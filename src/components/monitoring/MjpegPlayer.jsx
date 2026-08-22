import React, { useState } from "react";
import { AlertCircle } from "lucide-react";

export const MjpegPlayer = ({ streamUrl, className = "" }) => {
  const [error, setError] = useState(false);

  if (error || !streamUrl) {
    return (
      <div className={`flex flex-col items-center justify-center bg-[#0B1120] text-[#94A3B8] p-6 ${className}`}>
        <AlertCircle className="w-8 h-8 text-amber-400 mb-2" />
        <p className="text-xs font-mono">MJPEG stream feed offline.</p>
      </div>
    );
  }

  return (
    <img
      src={streamUrl}
      alt="MJPEG CCTV Stream"
      onError={() => setError(true)}
      className={`w-full h-full object-cover ${className}`}
    />
  );
};

export default MjpegPlayer;
