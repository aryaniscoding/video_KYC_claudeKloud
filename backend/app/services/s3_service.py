"""
S3 upload helpers for liveness frames and audio recordings.
All uploads are fire-and-forget (run_in_executor) so they never block
the WebSocket response path.
"""
import io
import logging
import wave
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)

_PCM_SAMPLE_RATE = 16000
_PCM_CHANNELS = 1
_PCM_SAMPLE_WIDTH = 2  # 16-bit


@lru_cache(maxsize=1)
def _s3_client():
    s = get_settings()
    return boto3.client(
        "s3",
        aws_access_key_id=s.aws_access_key_id,
        aws_secret_access_key=s.aws_secret_access_key,
        region_name=s.aws_region,
        endpoint_url=f"https://s3.{s.aws_region}.amazonaws.com",
        config=Config(signature_version="s3v4"),
    )


# ── WAV helpers ───────────────────────────────────────────────────────────────

def _pcm_to_wav(pcm_chunks: list[bytes]) -> bytes:
    """Concatenate raw PCM chunks and wrap in a WAV container."""
    raw = b"".join(pcm_chunks)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_PCM_CHANNELS)
        wf.setsampwidth(_PCM_SAMPLE_WIDTH)
        wf.setframerate(_PCM_SAMPLE_RATE)
        wf.writeframes(raw)
    return buf.getvalue()


# ── Upload functions (synchronous — called via run_in_executor) ───────────────

def _upload_bytes_sync(bucket: str, key: str, data: bytes, content_type: str) -> str:
    client = _s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


# ── Public async wrappers ─────────────────────────────────────────────────────

async def upload_frame(session_jti: str, jpeg_bytes: bytes, label: str = "liveness") -> str | None:
    """Upload a JPEG frame to S3. Returns the S3 key or None on failure."""
    import asyncio
    s = get_settings()
    bucket = s.s3_bucket_frames
    if not bucket:
        return None
    key = f"frames/{session_jti}/{label}.jpg"
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _upload_bytes_sync, bucket, key, jpeg_bytes, "image/jpeg")
        logger.info("Uploaded frame s3://%s/%s", bucket, key)
        return key
    except (BotoCoreError, ClientError) as e:
        logger.warning("S3 frame upload failed for session %s: %s", session_jti, e)
        return None


async def upload_audio_recording(
    session_jti: str,
    pcm_chunks: list[bytes],
    label: str = "qa",
) -> str | None:
    """Assemble PCM chunks into WAV and upload to S3. Returns the S3 key or None on failure."""
    import asyncio
    s = get_settings()
    bucket = s.s3_bucket_recordings
    if not bucket or not pcm_chunks:
        return None
    key = f"recordings/{session_jti}/{label}.wav"
    try:
        wav_bytes = _pcm_to_wav(pcm_chunks)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _upload_bytes_sync, bucket, key, wav_bytes, "audio/wav")
        logger.info("Uploaded recording s3://%s/%s (%d bytes WAV)", bucket, key, len(wav_bytes))
        return key
    except (BotoCoreError, ClientError) as e:
        logger.warning("S3 audio upload failed for session %s: %s", session_jti, e)
        return None


def generate_presigned_url(key: str, bucket: str | None = None, expires_seconds: int = 3600) -> str | None:
    """Generate a presigned GET URL for an S3 object. Returns None if bucket not configured or key empty."""
    s = get_settings()
    bucket = bucket or s.s3_bucket_frames
    if not bucket or not key:
        return None
    try:
        client = _s3_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
        return url
    except (BotoCoreError, ClientError) as e:
        logger.warning("Failed to generate presigned URL for %s/%s: %s", bucket, key, e)
        return None


async def upload_raw_audio(
    session_jti: str,
    audio_bytes: bytes,
    label: str = "consent",
) -> str | None:
    """Upload raw audio bytes (already WAV/PCM) to S3. Returns the S3 key or None on failure."""
    import asyncio
    s = get_settings()
    bucket = s.s3_bucket_recordings
    if not bucket or not audio_bytes:
        return None
    key = f"recordings/{session_jti}/{label}.wav"
    try:
        # Wrap in WAV if it looks like raw PCM (no RIFF header)
        if audio_bytes[:4] != b"RIFF":
            data = _pcm_to_wav([audio_bytes])
        else:
            data = audio_bytes
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _upload_bytes_sync, bucket, key, data, "audio/wav")
        logger.info("Uploaded consent audio s3://%s/%s", bucket, key)
        return key
    except (BotoCoreError, ClientError) as e:
        logger.warning("S3 consent upload failed for session %s: %s", session_jti, e)
        return None
