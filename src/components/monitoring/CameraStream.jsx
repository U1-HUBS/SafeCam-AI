import React, { useState, useEffect } from "react";
import { Camera, AlertCircle, RefreshCw, Radio, WifiOff } from "lucide-react";
import WebRTCPlayer from "./WebRTCPlayer";
import HlsPlayer from "./HlsPlayer";
import MjpegPlayer from "./MjpegPlayer";
import SimulatedStream from "./SimulatedStream";
import BrowserCameraPlayer from "./BrowserCameraPlayer";
import Button from "../ui/Button";

export const CameraStream = ({
  camera,
  streamUrl,
  streamType,
  onReconnect,
  className = ""
}) => {
  const currentMode = streamType || camera?.streamType || "simulation";
  const url = streamUrl || camera?.streamUrl || "";
  const status = camera?.status || "online";

  const [retryAttempt, setRetryAttempt] = useState(1);
  const [isRetrying, setIsRetrying] = useState(false);

  const handleManualReconnect = () => {
    setIsRetrying(true);
    if (onReconnect) {
      onReconnect(camera?.id);
    }
    setTimeout(() => {
      setIsRetrying(false);
      setRetryAttempt((prev) => (prev >= 5 ? 1 : prev + 1));
    }, 1500);
  };

  if (status === "offline" || status === "error") {
    return (
      <div className={`w-full h-full flex flex-col items-center justify-center bg-[#070C16] text-[#94A3B8] p-6 text-center font-mono ${className}`}>
        <div className="p-3 rounded-2xl bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20 mb-3 animate-pulse">
          <WifiOff className="w-8 h-8" />
        </div>
        <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">
          CAMERA SIGNAL LOST
        </h4>
        <p className="text-[11px] text-[#94A3B8] max-w-xs mb-4">
          Stream endpoint unresponsive. Attempting exponential auto-reconnect backoff.
        </p>

        <Button
          variant="outline"
          size="sm"
          icon={RefreshCw}
          isLoading={isRetrying}
          onClick={handleManualReconnect}
          className="text-xs border-[#EF4444]/40 text-[#EF4444] hover:bg-[#EF4444]/10"
        >
          RECONNECT NOW
        </Button>
      </div>
    );
  }

  if (status === "connecting") {
    return (
      <div className={`w-full h-full flex flex-col items-center justify-center bg-[#070C16] text-[#00D4FF] p-6 text-center font-mono ${className}`}>
        <RefreshCw className="w-8 h-8 animate-spin text-[#00D4FF] mb-3" />
        <h4 className="text-xs font-bold uppercase tracking-wider mb-1">
          CONNECTING TELEMETRY STREAM...
        </h4>
        <p className="text-[11px] text-[#94A3B8]">
          Establishing handshake • Attempt {retryAttempt}/5
        </p>
      </div>
    );
  }

  switch (currentMode) {
    case "browser":
      return <BrowserCameraPlayer deviceId={camera?.deviceId || camera?.streamUrl} className={className} />;
    case "webrtc":
      return (
        <WebRTCPlayer 
          streamUrl={camera?.rtspUrl || camera?.streamUrl || url} 
          cameraId={camera?.id || "CAM-001"} 
          className={className} 
        />
      );
    case "hls":
      return <HlsPlayer streamUrl={url} className={className} />;
    case "mjpeg":
      return <MjpegPlayer streamUrl={url} className={className} />;
    default:
      return (
        <SimulatedStream
          cameraName={camera?.name || "Camera Feed"}
          location={camera?.location || "Main Zone"}
          className={className}
        />
      );
  }
};

export default CameraStream;
