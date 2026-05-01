"""
STT service — Groq Whisper Large V3.

Processes audio via Groq cloud API instead of a local model.
Same public interface as before; push/flush are now async coroutines.
"""
import io
import logging
import time
from dataclasses import dataclass

import numpy as np
import soundfile as sf
from groq import AsyncGroq

from app.config import get_settings

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16000
_CHUNK_DURATION = 3.0       # send to Whisper every 3s for responsive transcripts
_OVERLAP = 0.5              # 0.5s overlap to avoid cutting words at boundaries
_SILENCE_THRESHOLD = 3      # consecutive silence chunks before auto-advance

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=get_settings().groq_api_key)
        logger.info("Groq STT client initialised (whisper-large-v3)")
    return _client


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class TranscriptChunk:
    text: str
    is_final: bool
    no_speech_prob: float
    avg_logprob: float
    words: list[dict]
    silence_detected: bool
    processing_ms: int


# ── Audio helpers ──────────────────────────────────────────────────────────────

def pcm_bytes_to_array(raw_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
    return arr / 32768.0


def wav_bytes_to_array(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    buf = io.BytesIO(wav_bytes)
    audio, sr = sf.read(buf, dtype="float32", always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return audio, sr


def resample_to_16k(audio: np.ndarray, source_sr: int) -> np.ndarray:
    if source_sr == _SAMPLE_RATE:
        return audio
    import librosa
    return librosa.resample(audio, orig_sr=source_sr, target_sr=_SAMPLE_RATE)


def _array_to_wav_bytes(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, _SAMPLE_RATE, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


# ── Core transcription ─────────────────────────────────────────────────────────

# Short prompt — just enough to bias vocabulary toward Indian names/amounts.
# Long prompts get regurgitated as hallucinated transcript when audio is silent.
_WHISPER_PROMPT = "Indian English. Rupees, EMI, Aadhar, PAN, Mumbai, Delhi, Bangalore."

# Phrases Whisper hallucinates on silence — discard these as empty.
_HALLUCINATION_FRAGMENTS = [
    "applicant", "emi obligation", "video kyc", "loan application",
    "personal detail", "thank you for watching", "see the video",
    "employment", "thumbnail", "subscribe", "please like",
    "thank you.", "thanks for watching",
]


def _is_hallucination(text: str) -> bool:
    """Return True if the text looks like a Whisper hallucination rather than real speech."""
    if not text or len(text) < 4:
        return True
    low = text.lower()
    return any(frag in low for frag in _HALLUCINATION_FRAGMENTS)


async def transcribe_chunk(audio_array: np.ndarray, language: str = "en") -> TranscriptChunk:
    """Transcribe a 16kHz float32 mono array via Groq Whisper Large V3."""
    client = _get_client()
    wav_bytes = _array_to_wav_bytes(audio_array)
    t0 = time.perf_counter()

    result = await client.audio.transcriptions.create(
        file=("chunk.wav", wav_bytes),
        model="whisper-large-v3",
        language=language,
        prompt=_WHISPER_PROMPT,
        temperature=0,
        response_format="verbose_json",
    )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    text = (result.text or "").strip()

    # Discard hallucinated output — treat as silence
    if _is_hallucination(text):
        text = ""

    no_speech_prob = 0.0
    avg_logprob = 0.0

    segments = getattr(result, "segments", None) or []
    if segments:
        nsp_vals = [s.no_speech_prob for s in segments if hasattr(s, "no_speech_prob")]
        lp_vals  = [s.avg_logprob   for s in segments if hasattr(s, "avg_logprob")]
        if nsp_vals:
            no_speech_prob = max(nsp_vals)
        if lp_vals:
            avg_logprob = sum(lp_vals) / len(lp_vals)

    silence_detected = not text

    logger.debug("STT chunk: %dms | silence=%s | nsp=%.2f | text=%r", elapsed_ms, silence_detected, no_speech_prob, text[:80])

    return TranscriptChunk(
        text=text,
        is_final=False,
        no_speech_prob=round(no_speech_prob, 4),
        avg_logprob=round(avg_logprob, 4),
        words=[],
        silence_detected=silence_detected,
        processing_ms=elapsed_ms,
    )


# ── Streaming buffer manager ───────────────────────────────────────────────────

class AudioStreamBuffer:
    """
    Accumulates PCM chunks and emits transcriptions on a rolling 5s window.
    push() and flush() are async — they call the Groq API.
    """

    def __init__(self, sample_rate: int = _SAMPLE_RATE, language: str = "en"):
        self._sr = sample_rate
        self._language = language
        self._buffer: np.ndarray = np.array([], dtype=np.float32)
        self._chunk_samples = int(_CHUNK_DURATION * sample_rate)
        self._overlap_samples = int(_OVERLAP * sample_rate)
        self._silence_frames = 0
        self._silence_limit = _SILENCE_THRESHOLD  # consecutive silent chunks required

    async def push(self, raw_pcm: bytes) -> TranscriptChunk | None:
        new_audio = pcm_bytes_to_array(raw_pcm)
        self._buffer = np.concatenate([self._buffer, new_audio])

        if len(self._buffer) >= self._chunk_samples:
            window = self._buffer[:self._chunk_samples]
            self._buffer = self._buffer[self._chunk_samples - self._overlap_samples:]

            chunk = await transcribe_chunk(window, language=self._language)
            if chunk.silence_detected:
                self._silence_frames += 1
            else:
                self._silence_frames = 0

            chunk.is_final = False
            return chunk
        return None

    async def flush(self) -> TranscriptChunk | None:
        if len(self._buffer) < int(0.5 * self._sr):
            return None
        chunk = await transcribe_chunk(self._buffer, language=self._language)
        chunk.is_final = True
        self._buffer = np.array([], dtype=np.float32)
        return chunk

    @property
    def auto_advance_triggered(self) -> bool:
        return self._silence_frames >= self._silence_limit

    def reset(self):
        self._buffer = np.array([], dtype=np.float32)
        self._silence_frames = 0


# ── Full-clip transcription (consent) ─────────────────────────────────────────

async def transcribe_full_audio(audio_bytes: bytes, language: str = "en") -> TranscriptChunk:
    """Transcribe a complete audio clip (consent utterance)."""
    try:
        audio, sr = wav_bytes_to_array(audio_bytes)
        if sr != _SAMPLE_RATE:
            audio = resample_to_16k(audio, sr)
        wav_bytes = _array_to_wav_bytes(audio)
    except Exception:
        audio = pcm_bytes_to_array(audio_bytes)
        wav_bytes = _array_to_wav_bytes(audio)

    chunk = await transcribe_chunk(
        np.frombuffer(wav_bytes[44:], dtype=np.int16).astype(np.float32) / 32768.0,
        language=language,
    )
    chunk.is_final = True
    return chunk
