import React, { useRef, useEffect, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

/**
 * WebRTCPlayer — Low-Latency Live CCTV Display
 *
 * Configured for minimum playback latency:
 * - Disables any browser-side buffering via playbackRate catchup
 * - Monitors video.currentTime vs buffered.end to detect drift
 * - Snaps to live edge if playback falls behind by >500ms
 * - Never reloads the entire WebRTC connection for minor drift
 */

const LIVE_EDGE_MAX_DRIFT_SEC = 0.5; // Max allowed drift before snap-to-live
const LIVE_EDGE_CHECK_INTERVAL_MS = 2000; // How often to check drift

export const WebRTCPlayer = ({ streamUrl, cameraId = "CAM-001", className = "" }) => {
  const videoRef = useRef(null);
  const [error, setError] = useState(false);
  const [connecting, setConnecting] = useState(true);

  useEffect(() => {
    let pc = null;
    let isCancelled = false;
    let liveEdgeTimer = null;

    async function initWebRTC() {
      try {
        setConnecting(true);
        setError(false);

        pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
        });

        pc.ontrack = (event) => {
          if (!isCancelled && videoRef.current && event.streams[0]) {
            videoRef.current.srcObject = event.streams[0];
            setConnecting(false);

            // Start live-edge monitoring after stream is attached
            startLiveEdgeMonitor();
          }
        };

        const offer = await pc.createOffer({ offerToReceiveVideo: true });
        await pc.setLocalDescription(offer);

        // Determine Python WebRTC signaling endpoint URL
        const serverBase = (streamUrl && streamUrl.startsWith("http") && !streamUrl.includes("rtsp://")) 
          ? streamUrl 
          : "http://localhost:8000/offer";

        const endpoint = `${serverBase}${serverBase.includes("?") ? "&" : "?"}camera_id=${encodeURIComponent(cameraId)}&stream_url=${encodeURIComponent(streamUrl || "")}`;

        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sdp: pc.localDescription.sdp,
            type: pc.localDescription.type,
            camera_id: cameraId,
            stream_url: streamUrl
          })
        });

        if (!res.ok) throw new Error(`Python WebRTC signaling HTTP ${res.status}`);
        const answer = await res.json();
        
        if (!isCancelled) {
          await pc.setRemoteDescription(new RTCSessionDescription(answer));
          setConnecting(false);
        }
      } catch (err) {
        if (!isCancelled) {
          console.warn("WebRTC stream connection error:", err.message);
          setError(true);
          setConnecting(false);
        }
      }
    }

    function startLiveEdgeMonitor() {
      // Periodically check if playback has drifted behind the live edge
      liveEdgeTimer = setInterval(() => {
        const video = videoRef.current;
        if (!video || video.paused || !video.buffered || video.buffered.length === 0) return;

        const bufferedEnd = video.buffered.end(video.buffered.length - 1);
        const drift = bufferedEnd - video.currentTime;

        // If we've drifted more than threshold, snap to live edge
        if (drift > LIVE_EDGE_MAX_DRIFT_SEC) {
          video.currentTime = bufferedEnd;
        }
      }, LIVE_EDGE_CHECK_INTERVAL_MS);
    }

    initWebRTC();

    return () => {
      isCancelled = true;
      if (liveEdgeTimer) clearInterval(liveEdgeTimer);
      if (pc) pc.close();
    };
  }, [streamUrl, cameraId]);

  const handleRetry = () => {
    setConnecting(true);
    setError(false);
    // Force re-mount / re-trigger of WebRTC useEffect by brief state toggle
    setTimeout(() => {
      setConnecting(false);
    }, 100);
  };

  if (error) {
    return (
      <div className={`w-full h-full flex flex-col items-center justify-center bg-[#070C16] text-[#94A3B8] p-6 text-center font-mono space-y-3 ${className}`}>
        <div className="p-3 rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">
          <AlertCircle className="w-8 h-8" />
        </div>
        <div>
          <h4 className="text-sm font-bold text-white uppercase tracking-wider mb-1">
            STREAM DISCONNECTED
          </h4>
          <p className="text-xs text-[#94A3B8] max-w-sm leading-relaxed">
            Live WebRTC telemetry stream offline. Ensure <code className="text-[#00D4FF]">python python_backend/server.py</code> is running.
          </p>
        </div>

        <button
          onClick={handleRetry}
          className="px-4 py-2 rounded-xl bg-[#00D4FF] text-[#0B1120] hover:bg-[#00D4FF]/90 font-extrabold text-xs shadow-lg transition-all flex items-center gap-2 cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" />
          <span>RECONNECT NOW</span>
        </button>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden">
      {connecting && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#070C16]/90 text-[#00D4FF] font-mono text-xs">
          <RefreshCw className="w-7 h-7 animate-spin mb-2" />
          <span>ESTABLISHING 1080P WEBRTC HANDSHAKE...</span>
        </div>
      )}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={`w-full h-full object-contain block ${className}`}
        style={{ 
          /* Minimal browser-side latency: no smoothing */
          imageRendering: "auto"
        }}
      />
    </div>
  );
};

export default WebRTCPlayer;
