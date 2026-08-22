import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { 
  Camera, 
  Plus, 
  Grid, 
  Layers, 
  Search, 
  Filter, 
  Eye, 
  ArrowLeft, 
  Maximize2, 
  RefreshCw, 
  Sliders, 
  ShieldAlert, 
  Info,
  RotateCcw,
  Volume2
} from "lucide-react";
import { useCameraContext, maskRtspUrl } from "../context/CameraContext";
import { useSocket } from "../context/SocketContext";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import CameraCard from "../components/monitoring/CameraCard";
import CameraStream from "../components/monitoring/CameraStream";
import DetectionOverlay from "../components/monitoring/DetectionOverlay";
import AddCameraModal from "../components/monitoring/AddCameraModal";
import CameraSettingsModal from "../components/monitoring/CameraSettingsModal";
import RemoveCameraModal from "../components/monitoring/RemoveCameraModal";
import BullyingAlarmBanner from "../components/alerts/BullyingAlarmBanner";
import audioAlertService from "../services/audioAlertService";

export const LiveMonitoring = () => {
  const { cameraId } = useParams();
  const navigate = useNavigate();

  const {
    cameras,
    selectedCamera,
    selectCamera,
    gridMode,
    setGridMode,
    searchQuery,
    setSearchQuery,
    statusFilter,
    setStatusFilter,
    reconnectCamera,
    resetToDefaultCameras
  } = useCameraContext();

  const { detectionMap, cameraMetricsMap } = useSocket();

  const [showAddModal, setShowAddModal] = useState(false);
  const [settingsCamera, setSettingsCamera] = useState(null);
  const [removeCameraObj, setRemoveCameraObj] = useState(null);
  const [showOverlay, setShowOverlay] = useState(true);
  const [detailStreamMode, setDetailStreamMode] = useState("webrtc");
  const [activeAlarmState, setActiveAlarmState] = useState(null);

  // Determine active view: Detail View (if cameraId URL parameter is present) or Grid View
  const isDetailView = Boolean(cameraId);
  const activeDetailCamera = cameras.find((c) => c.id === cameraId) || selectedCamera;

  // Automatically sync detail stream mode to real WebRTC stream when detail camera is opened
  useEffect(() => {
    if (activeDetailCamera) {
      const mode = activeDetailCamera.streamType === "simulation" ? "webrtc" : (activeDetailCamera.streamType || "webrtc");
      setDetailStreamMode(mode);
    }
  }, [activeDetailCamera?.id]);

  // Live Monitoring Session Lifecycle
  useEffect(() => {
    let isMounted = true;
    const sessionId = audioAlertService.startLiveSession();

    const fetchAlarms = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/alarms");
        if (res.ok) {
          const data = await res.json();
          if (isMounted && data && data.active_alarms && data.active_alarms.length > 0) {
            const currentAlarm = data.active_alarms[0];
            setActiveAlarmState(currentAlarm);

            // Play audio alert ONLY if it is a NEW live incident created during this live session and not acknowledged
            if (!currentAlarm.acknowledged) {
              audioAlertService.playBullyingAlarm(
                currentAlarm.incident_id,
                currentAlarm.started_at,
                sessionId
              );
            } else {
              audioAlertService.stopAlarmSound();
            }
          } else if (isMounted) {
            setActiveAlarmState(null);
            audioAlertService.stopAlarmSound();
          }
        }
      } catch (err) {
        // Quiet catch when backend offline
      }
    };

    fetchAlarms();
    const timer = setInterval(fetchAlarms, 500);

    return () => {
      isMounted = false;
      clearInterval(timer);
      audioAlertService.endLiveSession();
    };
  }, []);

  // Filter cameras for multi-camera grid
  const filteredCameras = cameras.filter((cam) => {
    const matchesSearch =
      cam.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cam.location.toLowerCase().includes(searchQuery.toLowerCase());

    const isThreat = (detectionMap[cam.id] || []).some((d) => d.role === "attacker") || cam.hasActiveAlert;

    if (statusFilter === "online") return matchesSearch && cam.status === "online";
    if (statusFilter === "offline") return matchesSearch && cam.status === "offline";
    if (statusFilter === "threat") return matchesSearch && isThreat;

    return matchesSearch;
  });

  const onlineCount = cameras.filter((c) => c.status === "online").length;

  // Calculate dynamic grid CSS classes
  const getGridClass = () => {
    if (gridMode === "1x1") return "grid-cols-1 w-full max-w-4xl mx-auto min-w-0 overflow-hidden";
    if (gridMode === "2x2") return "grid-cols-1 md:grid-cols-2 w-full min-w-0 overflow-hidden";
    if (gridMode === "3x2") return "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 w-full min-w-0 overflow-hidden";
    if (gridMode === "4x4") return "grid-cols-1 md:grid-cols-2 lg:grid-cols-4 w-full min-w-0 overflow-hidden";

    // Auto responsive grid based on camera count
    const count = filteredCameras.length;
    if (count <= 1) return "grid-cols-1 w-full max-w-5xl mx-auto min-w-0 overflow-hidden";
    if (count <= 4) return "grid-cols-1 md:grid-cols-2 w-full min-w-0 overflow-hidden";
    if (count <= 6) return "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 w-full min-w-0 overflow-hidden";
    return "grid-cols-1 md:grid-cols-2 lg:grid-cols-4 w-full min-w-0 overflow-hidden";
  };

  /* =========================================================================
     1. CAMERA DETAIL VIEW (/monitoring/:cameraId)
     ========================================================================= */
  if (isDetailView && activeDetailCamera) {
    const currentDetections = detectionMap[activeDetailCamera.id] || [];
    const currentMetrics = cameraMetricsMap[activeDetailCamera.id] || {
      fps: activeDetailCamera.fps,
      aiFps: activeDetailCamera.aiFps,
      latencyMs: activeDetailCamera.latencyMs
    };
    const isOnline = activeDetailCamera.status === "online";
    const attackerDet = currentDetections.find((d) => d.role === "attacker");
    const hasThreat = Boolean(attackerDet) || activeDetailCamera.hasActiveAlert;

    let detailThreatText = "⚠️ VERIFYING ACTIVITY";
    if (attackerDet) {
      const rawAct = attackerDet.action_label || attackerDet.action || "";
      if (rawAct.includes("MUTUAL")) {
        detailThreatText = "🚨 MUTUAL FIGHT DETECTED";
      } else {
        const cleanAct = rawAct.replace("BULLY — ", "").replace("ATTACKER — ", "").replace("_ATTACKER", "").replace("_", " ");
        detailThreatText = `🚨 VIOLENCE DETECTED (${cleanAct.toUpperCase()})`;
      }
    }

    return (
      <div className="space-y-4 sm:space-y-5">
        {/* Top Return / Back Navigation Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              icon={ArrowLeft}
              onClick={() => navigate("/monitoring")}
              className="text-xs text-[#00D4FF] border-[#00D4FF]/30 hover:bg-[#00D4FF]/10"
            >
              Back to Live Monitoring Grid
            </Button>
            <div>
              <h1 className="text-xl sm:text-2xl font-black text-[#F8FAFC] tracking-tight flex items-center gap-2">
                {activeDetailCamera.name}
              </h1>
              <p className="text-xs text-[#94A3B8] font-mono mt-0.5">
                {activeDetailCamera.location} • {maskRtspUrl(activeDetailCamera.rtspUrl)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant={isOnline ? (hasThreat ? "danger" : "success") : "neutral"}>
              {isOnline ? (hasThreat ? detailThreatText : "● STREAM ONLINE") : "● OFFLINE"}
            </Badge>

            <Button
              variant="ghost"
              size="sm"
              icon={Sliders}
              onClick={() => setSettingsCamera(activeDetailCamera)}
              className="text-xs text-[#94A3B8]"
            >
              Settings
            </Button>
          </div>
        </div>

        {/* 12-Column Detail View Layout (75% Video Workspace, 25% Telemetry Specs) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5">
          {/* Left Main Primary Player Viewport (9 Columns ~ 75% Width) */}
          <div className="lg:col-span-8 xl:col-span-9 space-y-3">
            <div className="relative aspect-video rounded-xl overflow-hidden glass-panel border border-white/10 shadow-2xl bg-slate-950 group">
              <CameraStream
                camera={activeDetailCamera}
                streamUrl={activeDetailCamera.rtspUrl || activeDetailCamera.streamUrl || ""}
                streamType={detailStreamMode}
                onReconnect={reconnectCamera}
              />

              {showOverlay && isOnline && detailStreamMode !== "webrtc" && (
                <DetectionOverlay detections={currentDetections} />
              )}

              {/* Player Telemetry Overlay Badge */}
              <div className="absolute top-3 left-3 right-3 flex items-center justify-between z-30 pointer-events-none">
                <div className="flex items-center gap-2">
                  <Badge variant={isOnline ? (hasThreat ? "danger" : "success") : "neutral"}>
                    {isOnline ? `● ${activeDetailCamera.name}` : "● OFFLINE"}
                  </Badge>
                  <span className="px-2 py-0.5 rounded bg-slate-950/80 backdrop-blur-md text-[10px] font-mono text-[#00D4FF] border border-[#00D4FF]/30">
                    {activeDetailCamera.location}
                  </span>
                </div>
              </div>
            </div>

            {/* Protocol Switcher Bar */}
            <div className="glass-panel p-3 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="text-[#94A3B8] text-[11px] uppercase font-bold">Stream Protocol:</span>
                <div className="flex items-center gap-1 bg-[#0B1120] p-1 rounded-lg border border-white/10">
                  {["simulation", "webrtc", "hls", "mjpeg"].map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setDetailStreamMode(mode)}
                      className={`px-2 py-0.5 rounded text-[11px] uppercase transition-colors ${
                        detailStreamMode === mode
                          ? "bg-[#00D4FF] text-[#0B1120] font-bold"
                          : "text-[#94A3B8] hover:text-white"
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowOverlay(!showOverlay)}
                  className={`px-2.5 py-1 rounded text-[11px] border font-semibold transition-colors ${
                    showOverlay
                      ? "bg-[#00D4FF]/10 text-[#00D4FF] border-[#00D4FF]/30 glow-cyan"
                      : "bg-white/5 border-white/10 text-[#94A3B8]"
                  }`}
                >
                  {showOverlay ? "AI Overlay ON" : "AI Overlay OFF"}
                </button>
              </div>
            </div>
          </div>

          {/* Right Telemetry Information Sidebar (3 Columns ~ 25% Width) */}
          <div className="lg:col-span-4 xl:col-span-3 space-y-3">
            <Card glow={hasThreat ? "red" : "cyan"}>
              <div className="border-b border-white/10 pb-2.5 mb-3 flex items-center justify-between">
                <h3 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-1.5">
                  <Info className="w-4 h-4 text-[#00D4FF]" />
                  Telemetry Specs
                </h3>
                <Badge variant={isOnline ? "cyan" : "neutral"}>
                  {isOnline ? "CONNECTED" : "DISCONNECTED"}
                </Badge>
              </div>

              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between items-center py-1 border-b border-white/5">
                  <span className="text-[#94A3B8]">Camera Name</span>
                  <span className="font-bold text-white">{activeDetailCamera.name}</span>
                </div>

                <div className="flex justify-between items-center py-1 border-b border-white/5">
                  <span className="text-[#94A3B8]">Resolution</span>
                  <span className="font-bold text-[#00D4FF]">{activeDetailCamera.resolution}</span>
                </div>

                <div className="flex justify-between items-center py-1 border-b border-white/5">
                  <span className="text-[#94A3B8]">Video FPS</span>
                  <span className="font-bold text-white">{currentMetrics.fps || activeDetailCamera.fps} FPS</span>
                </div>

                <div className="flex justify-between items-center py-1 border-b border-white/5">
                  <span className="text-[#94A3B8]">AI Inference</span>
                  <span className="font-bold text-[#00D4FF]">{currentMetrics.aiFps || activeDetailCamera.aiFps} FPS</span>
                </div>

                <div className="flex justify-between items-center py-1 border-b border-white/5">
                  <span className="text-[#94A3B8]">People Detected</span>
                  <span className="font-bold text-white">{currentDetections.length || activeDetailCamera.peopleCount}</span>
                </div>

                <div className="flex justify-between items-center py-1 border-b border-white/5">
                  <span className="text-[#94A3B8]">Threat Level</span>
                  <span className={`font-bold ${hasThreat ? "text-[#EF4444]" : "text-[#00D4FF]"}`}>
                    {hasThreat ? "⚠️ POSSIBLE PHYSICAL VIOLENCE DETECTED" : "● NORMAL"}
                  </span>
                </div>

                <div className="flex justify-between items-center py-1 border-b border-white/5">
                  <span className="text-[#94A3B8]">Telemetry Latency</span>
                  <span className="font-bold text-[#00D4FF]">{currentMetrics.latencyMs || activeDetailCamera.latencyMs} ms</span>
                </div>

                <div className="mt-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-300 font-sans leading-relaxed">
                  <span className="font-bold block mb-0.5">ℹ️ AI-Assisted Safety System</span>
                  Detections require human verification. This system assists operators and does not produce automatic punishments.
                </div>
              </div>
            </Card>

            {/* Quick Switch Channel Selector */}
            <Card>
              <h4 className="text-[11px] font-mono font-bold uppercase text-[#94A3B8] mb-2">Switch Channel</h4>
              <div className="space-y-1.5">
                {cameras.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => navigate(`/monitoring/${c.id}`)}
                    className={`p-2 rounded-lg border transition-colors cursor-pointer flex items-center justify-between text-xs ${
                      c.id === activeDetailCamera.id
                        ? "bg-[#00D4FF]/10 border-[#00D4FF]/40 text-[#00D4FF]"
                        : "bg-white/5 border-white/5 text-[#94A3B8] hover:text-white"
                    }`}
                  >
                    <span className="font-semibold font-mono">{c.name}</span>
                    <span className={`w-2 h-2 rounded-full ${c.status === "online" ? "bg-[#00D4FF]" : "bg-slate-500"}`} />
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>

        {/* Camera Settings & Remove Modals */}
        <CameraSettingsModal
          camera={settingsCamera}
          isOpen={Boolean(settingsCamera)}
          onClose={() => setSettingsCamera(null)}
          onOpenRemove={(cam) => setRemoveCameraObj(cam)}
        />

        <RemoveCameraModal
          camera={removeCameraObj}
          isOpen={Boolean(removeCameraObj)}
          onClose={() => setRemoveCameraObj(null)}
        />
      </div>
    );
  }

  /* =========================================================================
     2. MULTI-CAMERA CONTROL CENTER GRID VIEW (Default `/monitoring`)
     ========================================================================= */
  return (
    <div className="space-y-5">
      {/* Top Main Command Bar */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Live Monitoring
          </h1>
        </div>

        {/* Right Header Controls */}
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-[#121A2D] border border-white/10 text-white focus:border-[#00D4FF] focus:outline-none cursor-pointer"
          >
            <option value="all">All Cameras ({cameras.length})</option>
            <option value="online">Online Only ({onlineCount})</option>
            <option value="offline">Offline Only ({cameras.length - onlineCount})</option>
            <option value="threat">Active Threats Only</option>
          </select>

          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 rounded-xl bg-[#00D4FF] text-[#0B1120] hover:bg-[#00D4FF]/90 font-bold text-xs shadow-lg transition-all flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Connect Camera</span>
          </button>
        </div>
      </div>

      {/* Real Bullying Alarm Warning Banner */}
      <BullyingAlarmBanner
        activeAlarm={activeAlarmState}
        onAcknowledge={(camId) => {
          fetch("http://localhost:8000/api/alarms/acknowledge", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ camera_id: camId })
          }).catch(() => {});
        }}
      />

      {/* Dynamic Adaptive CCTV Camera Grid */}
      {filteredCameras.length === 0 ? (
        <div className="bg-[#0B1120]/90 border border-white/10 rounded-2xl p-12 sm:p-20 text-center flex flex-col items-center justify-center min-h-[450px] shadow-2xl space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30 flex items-center justify-center shadow-lg">
            <Camera className="w-8 h-8" />
          </div>
          <h3 className="text-2xl font-extrabold text-[#F8FAFC]">
            No cameras connected
          </h3>
          <p className="text-sm text-[#94A3B8] max-w-md mx-auto leading-relaxed font-sans">
            Connect a webcam or camera stream to begin real-time monitoring.
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-6 py-3 rounded-xl bg-[#00D4FF] text-[#0B1120] hover:bg-[#00D4FF]/90 font-extrabold text-sm shadow-xl transition-all flex items-center gap-2 cursor-pointer"
          >
            <Plus className="w-5 h-5" />
            <span>+ Add Your First Camera</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 w-full">
          {filteredCameras.map((camera) => (
            <CameraCard
              key={camera.id}
              camera={camera}
              showOverlay={showOverlay}
              onOpenSettings={(cam) => setSettingsCamera(cam)}
              onOpenRemove={(cam) => setRemoveCameraObj(cam)}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      <AddCameraModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
      />

      <CameraSettingsModal
        camera={settingsCamera}
        isOpen={Boolean(settingsCamera)}
        onClose={() => setSettingsCamera(null)}
        onOpenRemove={(cam) => setRemoveCameraObj(cam)}
      />

      <RemoveCameraModal
        camera={removeCameraObj}
        isOpen={Boolean(removeCameraObj)}
        onClose={() => setRemoveCameraObj(null)}
      />
    </div>
  );
};

export default LiveMonitoring;
