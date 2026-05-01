/**
 * PCM audio capture utility for consent and Q&A WebSocket flows.
 * Captures 16-bit, 16 kHz, mono, little-endian PCM — the format the backend expects.
 *
 * Usage:
 *   const capture = new AudioCapture();
 *   capture.onChunk = (pcmBuffer) => ws.send(pcmBuffer);
 *   await capture.start(mediaStream);
 *   capture.pause();   // mic off during display phase
 *   capture.resume();  // mic on during answer phase
 *   await capture.stop();
 */

const TARGET_SAMPLE_RATE = 16000;
const SILENCE_RMS_THRESHOLD = 0.012; // below this → considered silent
const SILENCE_TIMEOUT_MS = 5000;     // 5 s of continuous silence → onSilenceTimeout

export class AudioCapture {
  constructor() {
    this._context = null;
    this._source = null;
    this._processor = null;
    this._started = false;
    this._silenceTimer = null;
    this._speakingNow = false;

    /** @type {((pcmBuffer: ArrayBuffer) => void) | null} */
    this.onChunk = null;
    /** Called when 5 s of continuous silence is detected while recording. */
    this.onSilenceTimeout = null;
  }

  async start(mediaStream) {
    this._context = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
    this._source = this._context.createMediaStreamSource(mediaStream);

    // ScriptProcessorNode is deprecated but universally supported;
    // AudioWorklet requires HTTPS and a separate file — not worth the complexity for MVP.
    this._processor = this._context.createScriptProcessor(4096, 1, 1);
    this._processor.onaudioprocess = (e) => {
      if (!this._started) return;
      const float32 = e.inputBuffer.getChannelData(0);

      // RMS energy for silence detection
      let sum = 0;
      for (let i = 0; i < float32.length; i++) sum += float32[i] * float32[i];
      const rms = Math.sqrt(sum / float32.length);

      if (rms > SILENCE_RMS_THRESHOLD) {
        // Speech — cancel any running silence timer
        if (this._silenceTimer) {
          clearTimeout(this._silenceTimer);
          this._silenceTimer = null;
        }
        this._speakingNow = true;
      } else if (this._speakingNow && !this._silenceTimer) {
        // Just went silent after speech — start countdown
        this._silenceTimer = setTimeout(() => {
          this._silenceTimer = null;
          this.onSilenceTimeout?.();
        }, SILENCE_TIMEOUT_MS);
      }

      // Send PCM to backend
      const int16 = new Int16Array(float32.length);
      for (let i = 0; i < float32.length; i++) {
        int16[i] = Math.max(-32768, Math.min(32767, Math.round(float32[i] * 32768)));
      }
      this.onChunk?.(int16.buffer);
    };

    this._source.connect(this._processor);
    this._processor.connect(this._context.destination);
    this._started = true;
  }

  pause() {
    this._started = false;
    this._clearSilenceTimer();
    this._speakingNow = false;
  }

  resume() {
    this._speakingNow = false;
    this._started = true;
  }

  _clearSilenceTimer() {
    if (this._silenceTimer) {
      clearTimeout(this._silenceTimer);
      this._silenceTimer = null;
    }
  }

  async stop() {
    this._started = false;
    this._clearSilenceTimer();
    this._speakingNow = false;
    this._processor?.disconnect();
    this._source?.disconnect();
    if (this._context?.state !== "closed") {
      await this._context?.close().catch(() => {});
    }
    this._context = null;
    this._source = null;
    this._processor = null;
  }

  /**
   * Record a single blob of audio for a fixed duration (used by consent step).
   * Returns an ArrayBuffer of raw 16-bit PCM.
   */
  captureBlob(mediaStream, durationMs = 5000) {
    return new Promise((resolve) => {
      const chunks = [];
      this.onChunk = (buf) => chunks.push(new Int16Array(buf));
      this.start(mediaStream).then(() => {
        setTimeout(() => {
          this.stop();
          const totalLen = chunks.reduce((s, c) => s + c.length, 0);
          const merged = new Int16Array(totalLen);
          let offset = 0;
          for (const c of chunks) {
            merged.set(c, offset);
            offset += c.length;
          }
          resolve(merged.buffer);
        }, durationMs);
      });
    });
  }
}
