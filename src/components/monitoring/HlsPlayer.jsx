import React, { useRef, useEffect, useState } from "react";
import Hls from "hls.js";
import { AlertCircle } from "lucide-react";

export const HlsPlayer = ({ streamUrl, className = "" }) => {
  const videoRef = useRef(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!streamUrl) return;

    let hls = null;
    const video = videoRef.current;

    if (Hls.isSupported()) {
      hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true
      });
      hls.loadSource(streamUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.ERROR, () => setError(true));
    } else if (video && video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = streamUrl;
    } else {
      setError(true);
    }

    return () => {
      if (hls) hls.destroy();
    };
  }, [streamUrl]);

  if (error || !streamUrl) {
    return (
      <div className={`flex flex-col items-center justify-center bg-[#0B1120] text-[#94A3B8] p-6 ${className}`}>
        <AlertCircle className="w-8 h-8 text-amber-400 mb-2" />
        <p className="text-xs font-mono">HLS Stream endpoint unavailable.</p>
      </div>
    );
  }

  return (
    <video
      ref={videoRef}
      autoPlay
      playsInline
      muted
      className={`w-full h-full object-cover ${className}`}
    />
  );
};

export default HlsPlayer;
