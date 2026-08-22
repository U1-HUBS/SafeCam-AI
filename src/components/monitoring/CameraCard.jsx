import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Camera, 
  Maximize2, 
  Minimize2, 
  MoreVertical, 
  ExternalLink, 
  RefreshCw, 
  Settings, 
  Trash2, 
  Volume2, 
  VolumeX,
  X
} from "lucide-react";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import CameraStream from "./CameraStream";
import DetectionOverlay from "./DetectionOverlay";
import { useCameraContext } from "../../context/CameraContext";
import { useSocket } from "../../context/SocketContext";

export const CameraCard = ({
  camera,
  showOverlay = true,
  onOpenSettings,
  onOpenRemove
}) => {
  const navigate = useNavigate();
  const { toggleMinimize, reconnectCamera } = useCameraContext();
  const { detectionMap } = useSocket();

  const cardRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isMuted, setIsMuted] = useState(true);

  const detections = detectionMap[camera.id] || [];
  const isOnline = camera.status === "online";
  const attackerDet = detections.find((d) => d.role === "attacker");
  const hasThreat = Boolean(attackerDet) || camera.hasActiveAlert;

  let threatLabel = "● SAFE";
  if (attackerDet) {
    const rawAct = attackerDet.action_label || attackerDet.action || "";
    if (rawAct.includes("MUTUAL")) {
      threatLabel = "🚨 MUTUAL FIGHT DETECTED";
    } else {
      const cleanAct = rawAct
        .replace("BULLY — ", "")
        .replace("ATTACKER — ", "")
        .replace("_ATTACKER", "")
        .replace("_", " ");
      threatLabel = `🚨 VIOLENCE DETECTED (${cleanAct.toUpperCase()})`;
    }
  } else if (hasThreat) {
    threatLabel = "⚠️ VERIFYING ACTIVITY";
  }

  // Handle Fullscreen & ESC key listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
      }
    };

    const handleFullscreenChange = () => {
      const isDocFullscreen = Boolean(document.fullscreenElement);
      setIsFullscreen(isDocFullscreen);
    };

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("fullscreenchange", handleFullscreenChange);

    if (isFullscreen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.body.style.overflow = "unset";
    };
  }, [isFullscreen]);

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      setIsFullscreen(true);
      if (cardRef.current && cardRef.current.requestFullscreen) {
        cardRef.current.requestFullscreen().catch(() => {});
      }
    } else {
      setIsFullscreen(false);
      if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    }
  };

  const closeFullscreen = () => {
    setIsFullscreen(false);
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }
  };

  // Minimized state single-line compact bar view
  if (camera.minimized) {
    return (
      <div className="glass-card rounded-xl p-3 border border-white/10 flex items-center justify-between font-mono text-xs transition-all min-w-0 w-full">
        <div className="flex items-center gap-3 min-w-0">
          <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${isOnline ? (hasThreat ? "bg-[#EF4444]" : "bg-[#00D4FF]") : "bg-slate-500"}`} />
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-bold text-white truncate">{camera.name}</span>
            <span className="text-[10px] text-[#94A3B8] truncate">• {camera.location}</span>
          </div>
          <Badge variant={isOnline ? (hasThreat ? "danger" : "cyan") : "neutral"}>
            {isOnline ? (hasThreat ? "🚨 THREAT" : "LIVE") : "OFFLINE"}
          </Badge>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            icon={Maximize2}
            onClick={() => toggleMinimize(camera.id)}
            className="text-[11px] py-1 px-2.5"
          >
            RESTORE STREAM
          </Button>
        </div>
      </div>
    );
  }

  // FULLSCREEN VIEWPORT OVERLAY (100vw × 100vh)
  if (isFullscreen) {
    return (
      <div
        ref={cardRef}
        className="fixed inset-0 z-[9999] w-screen h-screen bg-[#070C16] p-4 flex flex-col justify-between overflow-hidden box-border font-mono"
      >
        {/* Fullscreen Header Bar */}
        <div className="h-12 flex items-center justify-between border-b border-white/10 pb-2 shrink-0">
          <div className="flex items-center gap-3">
            <span className={`w-3 h-3 rounded-full ${isOnline ? (hasThreat ? "bg-[#EF4444] animate-ping" : "bg-[#00D4FF]") : "bg-slate-500"}`} />
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight flex items-center gap-2">
                {camera.name}
              </h2>
              <p className="text-xs text-[#94A3B8]">{camera.location}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant={isOnline ? (hasThreat ? "danger" : "cyan") : "neutral"}>
              {isOnline ? (hasThreat ? "🚨 THREAT DETECTED" : "● LIVE") : "● OFFLINE"}
            </Badge>

            <button
              onClick={closeFullscreen}
              className="p-2 rounded-xl bg-white/10 hover:bg-[#EF4444]/20 text-[#94A3B8] hover:text-[#EF4444] transition-colors border border-white/10"
              title="Close Fullscreen (ESC)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Fullscreen Centered 16:9 Video Container */}
        <div className="flex-1 w-full min-h-0 min-w-0 relative flex items-center justify-center overflow-hidden bg-black rounded-xl my-3">
          <CameraStream
            camera={camera}
            streamUrl={camera.rtspUrl || camera.streamUrl || ""}
            streamType={camera.streamType}
            onReconnect={reconnectCamera}
            className="w-full h-full object-contain"
          />

          {/* Render React DetectionOverlay ONLY for non-WebRTC stream modes */}
          {showOverlay && isOnline && camera.streamType !== "webrtc" && (
            <DetectionOverlay detections={detections} />
          )}
        </div>

        {/* Fullscreen Footer Controls & Telemetry Spec Bar */}
        <div className="h-12 flex items-center justify-between border-t border-white/10 pt-2 text-xs text-[#94A3B8] shrink-0">
          <div className="flex items-center gap-4">
            <span className="font-bold text-white">{camera.resolution || "1920 × 1080"}</span>
            <span>• 30 FPS</span>
            <span className="text-[#00D4FF] font-bold">AI 10 FPS</span>
            <span className="hidden sm:inline text-slate-500">• Protocol: {(camera.streamType || "simulation").toUpperCase()}</span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              icon={Minimize2}
              onClick={closeFullscreen}
              className="text-xs border-white/20 text-white hover:bg-white/10"
            >
              Exit Fullscreen (ESC)
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // NORMAL MONITORING GRID CAMERA CARD
  return (
    <div
      ref={cardRef}
      className={`w-full min-w-0 overflow-hidden glass-card rounded-xl border flex flex-col transition-all duration-200 ${
        hasThreat
          ? "border-[#EF4444]/40 bg-[#EF4444]/5 glow-red"
          : isOnline
          ? "border-white/10 hover:border-[#00D4FF]/40"
          : "border-slate-800 opacity-80"
      }`}
    >
      {/* Camera Header Bar */}
      <div className="p-3 border-b border-white/10 bg-slate-950/40 flex items-center justify-between min-w-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className={`w-2 h-2 rounded-full shrink-0 ${isOnline ? (hasThreat ? "bg-[#EF4444] animate-ping" : "bg-[#00D4FF]") : "bg-slate-500"}`} />
          <div className="min-w-0">
            <h3 className="text-xs sm:text-sm font-bold text-[#F8FAFC] tracking-tight truncate">
              {camera.name}
            </h3>
            <p className="text-[10px] font-mono text-[#94A3B8] truncate">{camera.location}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Badge variant={isOnline ? (hasThreat ? "danger" : "cyan") : "neutral"}>
            {isOnline ? (hasThreat ? threatLabel : "● LIVE") : "● OFFLINE"}
          </Badge>
          <span className="hidden sm:inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[#00D4FF]">
            {camera.streamType || "SIMULATION"}
          </span>

          {/* Quick Fullscreen Button */}
          <button
            onClick={toggleFullscreen}
            className="p-1 rounded text-[#00D4FF] hover:text-white hover:bg-[#00D4FF]/20 transition-colors border border-[#00D4FF]/30"
            title="Expand Fullscreen"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>

          {/* Settings Dropdown Toggle */}
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1 rounded text-[#94A3B8] hover:text-white hover:bg-white/10 transition-colors"
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {showMenu && (
              <div className="absolute right-0 mt-1 w-44 glass-panel rounded-xl border border-white/10 shadow-2xl z-50 py-1 font-mono text-xs">
                <button
                  onClick={() => {
                    setShowMenu(false);
                    toggleFullscreen();
                  }}
                  className="w-full px-3 py-1.5 text-left text-white hover:bg-white/10 flex items-center gap-2"
                >
                  <Maximize2 className="w-3.5 h-3.5 text-[#00D4FF]" />
                  <span>Full Screen</span>
                </button>
                <button
                  onClick={() => {
                    setShowMenu(false);
                    navigate(`/monitoring/${camera.id}`);
                  }}
                  className="w-full px-3 py-1.5 text-left text-white hover:bg-white/10 flex items-center gap-2"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-[#00D4FF]" />
                  <span>Open Detail</span>
                </button>
                <button
                  onClick={() => {
                    setShowMenu(false);
                    reconnectCamera(camera.id);
                  }}
                  className="w-full px-3 py-1.5 text-left text-white hover:bg-white/10 flex items-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-[#00D4FF]" />
                  <span>Test / Reconnect</span>
                </button>
                <button
                  onClick={() => {
                    setShowMenu(false);
                    if (onOpenSettings) onOpenSettings(camera);
                  }}
                  className="w-full px-3 py-1.5 text-left text-white hover:bg-white/10 flex items-center gap-2"
                >
                  <Settings className="w-3.5 h-3.5 text-[#00D4FF]" />
                  <span>Configure RTSP</span>
                </button>
                <div className="my-1 border-t border-white/10" />
                <button
                  onClick={() => {
                    setShowMenu(false);
                    if (onOpenRemove) onOpenRemove(camera);
                  }}
                  className="w-full px-3 py-1.5 text-left text-[#EF4444] hover:bg-[#EF4444]/10 flex items-center gap-2"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Remove Camera</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Primary Video Feed Player Viewport (16:9 Aspect Ratio) */}
      <div 
        onDoubleClick={toggleFullscreen}
        className="relative w-full aspect-video bg-slate-950 overflow-hidden group flex items-center justify-center cursor-pointer"
        title="Double-click for Fullscreen"
      >
        <CameraStream
          camera={camera}
          streamUrl={camera.rtspUrl || camera.streamUrl || ""}
          streamType={camera.streamType}
          onReconnect={reconnectCamera}
        />

        {/* Render React DetectionOverlay ONLY for non-WebRTC stream modes */}
        {showOverlay && isOnline && camera.streamType !== "webrtc" && (
          <DetectionOverlay detections={detections} />
        )}

        {/* Quick Viewport Action Overlay on Hover */}
        <div className="absolute top-2 right-2 flex items-center gap-1.5 z-30 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto">
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleFullscreen();
            }}
            className="p-1.5 rounded-lg bg-slate-950/80 backdrop-blur-md text-[#00D4FF] hover:text-white border border-[#00D4FF]/30 transition-colors shadow-lg flex items-center gap-1 text-[10px] font-mono"
            title="Expand Fullscreen"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">FULLSCREEN</span>
          </button>
        </div>

        {/* Mute Indicator overlay */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsMuted(!isMuted);
          }}
          className="absolute bottom-2 right-2 p-1.5 rounded-lg bg-slate-950/80 backdrop-blur-md text-[#94A3B8] hover:text-white z-30 transition-colors opacity-0 group-hover:opacity-100"
        >
          {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5 text-[#00D4FF]" />}
        </button>
      </div>

      {/* Card Footer Control & Spec Bar */}
      <div className="p-2.5 border-t border-white/10 bg-[#070C16] flex items-center justify-between text-[11px] font-mono min-w-0">
        <span className="text-[#00D4FF] font-semibold flex items-center gap-1.5">
          Status: MONITORING ACTIVE
        </span>
        <button
          onClick={() => navigate("/logs")}
          className="text-[#00D4FF] hover:underline font-semibold"
        >
          View Logs
        </button>
      </div>
    </div>
  );
};

export default CameraCard;
