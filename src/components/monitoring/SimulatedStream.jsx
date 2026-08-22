import React, { useEffect, useRef } from "react";

export const SimulatedStream = ({ cameraName = "Camera 01", location = "Zone A", className = "" }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    // Simulated streams always render normal activity (no live threat state)
    const isThreat = false;

    let animId;
    const render = () => {
      ctx.fillStyle = "#0B1120";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Grid Lines
      ctx.strokeStyle = "rgba(0, 212, 255, 0.08)";
      ctx.lineWidth = 1;

      for (let x = 0; x < canvas.width; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += 40) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }

      // Perspective Grid Viewport Lines
      ctx.strokeStyle = "rgba(0, 212, 255, 0.12)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(100, 100);
      ctx.lineTo(0, 0);
      ctx.moveTo(700, 100);
      ctx.lineTo(800, 0);
      ctx.moveTo(100, 400);
      ctx.lineTo(0, 450);
      ctx.moveTo(700, 400);
      ctx.lineTo(800, 450);
      ctx.stroke();

      // Background Frame
      ctx.fillStyle = "rgba(15, 23, 42, 0.4)";
      ctx.fillRect(100, 100, 600, 300);

      // Top Left Camera Info Telemetry
      ctx.fillStyle = "#00D4FF";
      ctx.font = "bold 12px monospace";
      ctx.fillText(`CAM: ${cameraName.toUpperCase()}`, 20, 30);
      ctx.fillStyle = "#94A3B8";
      ctx.font = "11px monospace";
      ctx.fillText(`LOC: ${location.toUpperCase()}`, 20, 45);

      // Top Right Live Timestamp
      const now = new Date();
      const timeStr = now.toTimeString().split(" ")[0] + "." + Math.floor(now.getMilliseconds() / 100);
      ctx.fillStyle = "#00D4FF";
      ctx.font = "bold 13px monospace";
      ctx.fillText(`● REC [${timeStr}]`, canvas.width - 170, 30);

      // Center Watermark
      ctx.fillStyle = "rgba(255, 255, 255, 0.05)";
      ctx.font = "bold 22px 'Inter', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("SAFECAM AI SURVEILLANCE FEED", canvas.width / 2, canvas.height / 2);
      ctx.textAlign = "left";

      animId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animId);
  }, [cameraName, location]);

  return (
    <div className={`relative w-full h-full ${className}`}>
      <canvas
        ref={canvasRef}
        width={800}
        height={450}
        className="w-full h-full object-cover block"
      />
      <div className="video-scanline absolute inset-0 pointer-events-none" />
    </div>
  );
};

export default SimulatedStream;
