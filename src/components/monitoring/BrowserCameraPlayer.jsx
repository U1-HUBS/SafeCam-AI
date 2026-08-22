import React, { useEffect, useRef, useState } from "react";
import { Camera, AlertCircle } from "lucide-react";

export const BrowserCameraPlayer = ({ deviceId, className = "" }) => {
  const videoRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let stream = null;
    async function startWebcam() {
      try {
        setError(null);
        const constraints = {
          video: deviceId ? { deviceId: { exact: deviceId } } : true,
          audio: false
        };
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error("Browser camera error:", err);
        setError(err.message || "Failed to access browser camera device");
      }
    }

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      startWebcam();
    } else {
      setError("Browser mediaDevice API not supported in this environment.");
    }

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [deviceId]);

  if (error) {
    return (
      <div className={`w-full h-full flex flex-col items-center justify-center bg-[#070C16] text-[#EF4444] p-4 text-center font-mono ${className}`}>
        <AlertCircle className="w-8 h-8 mb-2 opacity-80" />
        <p className="text-xs font-bold uppercase mb-1">Webcam Permission / Device Failure</p>
        <p className="text-[10px] text-[#94A3B8] max-w-xs leading-relaxed">{error}</p>
      </div>
    );
  }

  return (
    <video
      ref={videoRef}
      autoPlay
      playsInline
      muted
      className={`w-full h-full object-contain block ${className}`}
    />
  );
};

export default BrowserCameraPlayer;
