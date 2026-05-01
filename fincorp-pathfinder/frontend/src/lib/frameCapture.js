/**
 * Capture JPEG frames from a <video> element for the liveness WebSocket.
 * The backend expects raw JPEG binary sent as WebSocket binary frames.
 *
 * Usage:
 *   const stopper = startFrameCapture(videoEl, ws, 15);
 *   // stopper() to cancel early
 */

/**
 * Capture a single JPEG blob from a video element.
 * @param {HTMLVideoElement} video
 * @param {number} quality — JPEG quality 0–1
 * @returns {Promise<Blob>}
 */
export function captureJpegFrame(video, quality = 0.85) {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), "image/jpeg", quality);
  });
}

/**
 * Start capturing frames at ~15fps and sending them over a WebSocket.
 * Returns a cancel function.
 *
 * @param {HTMLVideoElement} video
 * @param {WebSocket} ws — must be in OPEN state
 * @param {number} fps
 * @returns {() => void} cancel
 */
export function startFrameCapture(video, ws, fps = 15) {
  let running = true;
  const interval = 1000 / fps;

  const loop = async () => {
    if (!running) return;
    if (ws.readyState === 1 && video.readyState >= 2) {
      const blob = await captureJpegFrame(video);
      if (running && ws.readyState === 1) {
        ws.send(blob);
      }
    }
    if (running) setTimeout(loop, interval);
  };

  loop();
  return () => { running = false; };
}
