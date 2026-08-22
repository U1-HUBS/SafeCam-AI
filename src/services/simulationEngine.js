// SAFECAM AI — Telemetry & Bounding Box Engine

export function generateLiveDetections(cameraId, isAlertActive = false) {
  // Returns empty array unless real AI telemetry is received
  return [];
}

export function generateLiveMetrics(baseFps = 30, baseAiFps = 10, baseLatency = 240) {
  return {
    fps: baseFps,
    aiFps: baseAiFps,
    latencyMs: baseLatency
  };
}
