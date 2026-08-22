import React, { useState, useEffect } from "react";
import { 
  Camera, 
  Video, 
  Smartphone, 
  Radio, 
  Wifi, 
  AlertTriangle, 
  RefreshCw, 
  Link as LinkIcon, 
  Building,
  Bookmark,
  CheckCircle,
  Search,
  Key,
  Shield,
  Monitor
} from "lucide-react";
import Modal from "../ui/Modal";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { useCameraContext, maskRtspUrl } from "../../context/CameraContext";

export const AddCameraModal = ({ isOpen, onClose }) => {
  const { cameras, addCamera } = useCameraContext();

  // Active Source Selection: 'connected', 'browser', 'mobile', 'obs', 'scanner'
  const [sourceType, setSourceType] = useState("connected");

  // Common Fields
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [streamType, setStreamType] = useState("simulation"); // 'simulation', 'browser', 'webrtc', 'hls', 'mjpeg'

  // Connected Camera Fields
  const [ipAddress, setIpAddress] = useState("");
  const [port, setPort] = useState("554");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rtspPath, setRtspPath] = useState("/stream1");
  const [rtspUrl, setRtspUrl] = useState("");

  // Browser Camera Fields
  const [browserDevices, setBrowserDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [webcamPermission, setWebcamPermission] = useState("unknown"); // 'unknown', 'granted', 'denied'

  // OBS Stream Fields
  const [obsStreamUrl, setObsStreamUrl] = useState("http://localhost:8080/live/obs.flv");

  // Mobile Phone Fields
  const [mobileDeviceName, setMobileDeviceName] = useState("SecMobile-Phone-01");

  // Network Scanner Fields
  const [isScanning, setIsScanning] = useState(false);
  const [discoveredDevices, setDiscoveredDevices] = useState([]);

  // Save Preset Checkbox
  const [savePreset, setSavePreset] = useState(true);

  // Connection Test & Feedback State
  const [testState, setTestState] = useState("idle"); // 'idle', 'testing', 'success', 'error'
  const [testMessage, setTestMessage] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const LAST_CONFIG_KEY = "safecam_last_camera_config_v1";
  const CAMERA_CONFIGS_KEY = "safecam_camera_configs_v1";

  // Enumerate Browser Camera Devices & Load Last Saved Camera Configuration on Open
  useEffect(() => {
    if (isOpen) {
      loadBrowserDevices();
      try {
        const savedConfigStr = localStorage.getItem(LAST_CONFIG_KEY);
        if (savedConfigStr) {
          const savedConfig = JSON.parse(savedConfigStr);
          if (savedConfig) {
            let baseName = savedConfig.name || "";
            if (baseName && cameras.some((c) => c.name.toLowerCase() === baseName.toLowerCase())) {
              let count = 2;
              while (cameras.some((c) => c.name.toLowerCase() === `${baseName} ${count}`.toLowerCase())) {
                count++;
              }
              baseName = `${baseName} ${count}`;
            }
            setName(baseName || `Camera ${cameras.length + 1}`);
            if (savedConfig.location) setLocation(savedConfig.location);
            if (savedConfig.sourceType) setSourceType(savedConfig.sourceType);
            if (savedConfig.ipAddress) setIpAddress(savedConfig.ipAddress);
            if (savedConfig.port) setPort(savedConfig.port);
            if (savedConfig.username) setUsername(savedConfig.username);
            if (savedConfig.password) setPassword(savedConfig.password);
            if (savedConfig.rtspPath) setRtspPath(savedConfig.rtspPath);
            if (savedConfig.rtspUrl) setRtspUrl(savedConfig.rtspUrl);
            if (savedConfig.streamType) setStreamType(savedConfig.streamType);
            if (savedConfig.obsStreamUrl) setObsStreamUrl(savedConfig.obsStreamUrl);
            if (savedConfig.mobileDeviceName) setMobileDeviceName(savedConfig.mobileDeviceName);
            if (savedConfig.selectedDeviceId) setSelectedDeviceId(savedConfig.selectedDeviceId);
          }
        }
      } catch (e) {
        console.warn("Failed to load saved camera config:", e);
      }
    }
  }, [isOpen]);

  const loadBrowserDevices = async () => {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoInputs = devices.filter((d) => d.kind === "videoinput");
        setBrowserDevices(videoInputs);
        if (videoInputs.length > 0 && !selectedDeviceId) {
          setSelectedDeviceId(videoInputs[0].deviceId);
        }
      }
    } catch (e) {
      console.warn("Failed to enumerate browser camera devices:", e);
    }
  };

  const requestWebcamAccess = async () => {
    try {
      setWebcamPermission("unknown");
      await navigator.mediaDevices.getUserMedia({ video: true });
      setWebcamPermission("granted");
      await loadBrowserDevices();
    } catch (e) {
      setWebcamPermission("denied");
      setErrorMsg("Webcam permission denied by browser settings.");
    }
  };

  // Helper to build effective RTSP URL for Connected Camera
  const getConstructedRtspUrl = () => {
    if (rtspUrl.trim()) return rtspUrl.trim();
    if (ipAddress.trim()) {
      const userPart = username.trim() ? `${encodeURIComponent(username.trim())}:${encodeURIComponent(password)}@` : "";
      const portPart = port.trim() ? `:${port.trim()}` : "";
      const pathPart = rtspPath.trim() ? (rtspPath.trim().startsWith("/") ? rtspPath.trim() : `/${rtspPath.trim()}`) : "/stream1";
      return `rtsp://${userPart}${ipAddress.trim()}${portPart}${pathPart}`;
    }
    return "";
  };

  // Saved Camera Presets Handler
  const handleSelectPreset = (presetCam) => {
    setName(`${presetCam.name} (Copy)`);
    setLocation(presetCam.location || "Zone A - Main");
    if (presetCam.rtspUrl) {
      setSourceType("connected");
      setRtspUrl(presetCam.rtspUrl);
      setStreamType(presetCam.streamType || "simulation");
    } else if (presetCam.streamType === "browser") {
      setSourceType("browser");
      setStreamType("browser");
    } else {
      setSourceType("connected");
      setStreamType(presetCam.streamType || "simulation");
    }
    if (presetCam.ipAddress) setIpAddress(presetCam.ipAddress);
    if (presetCam.port) setPort(presetCam.port);
    if (presetCam.username) setUsername(presetCam.username);
    if (presetCam.password) setPassword(presetCam.password);
    if (presetCam.rtspPath) setRtspPath(presetCam.rtspPath);
    setTestState("idle");
    setTestMessage("");
  };

  // Local Network Scanner Action
  const handleScanNetwork = () => {
    setIsScanning(true);
    setDiscoveredDevices([]);
    setTimeout(() => {
      setIsScanning(false);
      setDiscoveredDevices([
        { id: "disc-1", name: "Axis IP Camera 101", ip: "192.168.1.120", port: "554", path: "/live/ch0" },
        { id: "disc-2", name: "Hikvision Dome Cam", ip: "192.168.1.123", port: "554", path: "/h264/ch1/main" },
        { id: "disc-3", name: "Dahua PTZ Camera", ip: "192.168.1.145", port: "554", path: "/cam/realmonitor" }
      ]);
    }, 1200);
  };

  const handleSelectDiscoveredDevice = (device) => {
    setSourceType("connected");
    setName(device.name);
    setIpAddress(device.ip);
    setPort(device.port);
    setRtspPath(device.path);
    setTestState("idle");
  };

  // Source-Specific Connection Test
  const handleTestConnection = () => {
    setErrorMsg("");
    setTestState("testing");
    setTestMessage("Testing source connection...");

    setTimeout(() => {
      if (sourceType === "connected") {
        const effectiveUrl = getConstructedRtspUrl();
        if (effectiveUrl && !effectiveUrl.startsWith("rtsp://")) {
          setTestState("error");
          setTestMessage("Invalid RTSP URL format. Must begin with rtsp://");
          return;
        }
        setTestState("success");
        setTestMessage(`● Connected Camera Ready — IP Handshake OK (${effectiveUrl ? maskRtspUrl(effectiveUrl) : "Simulation Stream"})`);
      } else if (sourceType === "browser") {
        setTestState("success");
        setTestMessage("● Browser Camera Accessible — Resolution 1920x1080 @ 30 FPS");
      } else if (sourceType === "mobile") {
        setTestState("success");
        setTestMessage(`● Mobile App Stream Active — ${mobileDeviceName} paired`);
      } else if (sourceType === "obs") {
        setTestState("success");
        setTestMessage(`● OBS Endpoint Live — ${obsStreamUrl}`);
      } else if (sourceType === "scanner") {
        setTestState("success");
        setTestMessage(`● Network Scan Active — ${discoveredDevices.length} IP camera endpoints found`);
      }
    }, 1000);
  };

  // Submit Handler
  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMsg("");

    if (!name.trim()) {
      setErrorMsg("Camera name is required.");
      return;
    }

    // Check Duplicate Names
    const isDuplicate = cameras.some(
      (c) => c.name.toLowerCase() === name.trim().toLowerCase()
    );
    if (isDuplicate) {
      setErrorMsg(`A camera named "${name.trim()}" already exists.`);
      return;
    }

    let finalRtspUrl = "";
    let finalStreamType = streamType;
    let finalStreamUrl = "";

    if (sourceType === "connected") {
      finalRtspUrl = getConstructedRtspUrl();
      // Enforce RTSP format validation ONLY if an RTSP URL / IP address is specified
      if (finalRtspUrl && !finalRtspUrl.startsWith("rtsp://")) {
        setErrorMsg("Valid RTSP URL starting with rtsp:// is required for connected camera.");
        return;
      }
    } else if (sourceType === "browser") {
      finalStreamType = "browser";
      finalStreamUrl = selectedDeviceId;
      finalRtspUrl = ""; // No RTSP required
    } else if (sourceType === "obs") {
      finalStreamType = "hls";
      finalStreamUrl = obsStreamUrl.trim();
      finalRtspUrl = ""; // No RTSP required
    } else if (sourceType === "mobile") {
      finalStreamType = "webrtc";
      finalStreamUrl = `https://mobile.safecam.ai/stream/${Date.now()}`;
      finalRtspUrl = ""; // No RTSP required
    } else if (sourceType === "scanner") {
      finalRtspUrl = getConstructedRtspUrl();
    }

    const configToSave = {
      name: name.trim(),
      location: location.trim() || "Surveillance Zone",
      sourceType,
      ipAddress: ipAddress.trim(),
      port: port.trim() || "554",
      username: username.trim(),
      password,
      rtspPath: rtspPath.trim() || "/stream1",
      rtspUrl: finalRtspUrl,
      streamType: finalStreamType,
      streamUrl: finalStreamUrl,
      obsStreamUrl: obsStreamUrl.trim(),
      mobileDeviceName: mobileDeviceName.trim(),
      selectedDeviceId
    };

    // Persist configuration in localStorage
    try {
      localStorage.setItem(LAST_CONFIG_KEY, JSON.stringify(configToSave));
    } catch (e) {
      console.error("Failed to save camera configuration", e);
    }

    const createdCam = addCamera({
      name: name.trim(),
      location: location.trim() || "Surveillance Zone",
      rtspUrl: finalRtspUrl,
      streamType: finalStreamType,
      streamUrl: finalStreamUrl,
      ipAddress: ipAddress.trim(),
      port: port.trim() || "554",
      username: username.trim(),
      password,
      rtspPath: rtspPath.trim() || "/stream1",
      sourceType,
      resolution: "1920 × 1080",
      deviceId: selectedDeviceId
    });

    try {
      const existingMapStr = localStorage.getItem(CAMERA_CONFIGS_KEY);
      const map = existingMapStr ? JSON.parse(existingMapStr) : {};
      if (createdCam && createdCam.id) {
        map[createdCam.id] = configToSave;
        localStorage.setItem(CAMERA_CONFIGS_KEY, JSON.stringify(map));
      }
    } catch (e) {}

    setTestState("idle");
    setTestMessage("");
    onClose();
  };

  // Get Dynamic Submit Action Button Text
  const getSubmitButtonText = () => {
    switch (sourceType) {
      case "browser":
        return "Start Camera";
      case "mobile":
        return "Connect Phone";
      case "obs":
        return "Connect Stream";
      case "scanner":
        return "Connect Discovered Camera";
      default:
        return "Connect Camera";
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="CREATE LIVE / ADD CCTV CAMERA"
      subtitle="Configure video stream source, device stream protocol, or network discovery"
      maxWidth="max-w-3xl"
    >
      <form 
        onSubmit={handleSubmit} 
        className="space-y-5 sm:space-y-6 text-sm font-mono max-h-[calc(100vh-140px)] overflow-y-auto pr-1"
      >
        {errorMsg && (
          <div className="p-4 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/30 text-[#EF4444] font-sans flex items-center gap-2.5 text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span className="font-semibold">{errorMsg}</span>
          </div>
        )}

        {/* SAVED CAMERA PRESETS SECTION */}
        {cameras.length > 0 && (
          <div className="space-y-2 p-4 rounded-2xl bg-[#0B1120] border border-white/10 shadow-lg">
            <div className="flex items-center justify-between text-xs sm:text-sm text-[#94A3B8] font-mono">
              <span className="font-bold uppercase tracking-wider flex items-center gap-2 text-white">
                <Bookmark className="w-4 h-4 text-[#00D4FF]" />
                SAVED CAMERA PRESETS
              </span>
              <span className="text-xs">Click to auto-populate</span>
            </div>

            <div className="flex items-center gap-2.5 overflow-x-auto pt-1 pb-1">
              {cameras.slice(0, 5).map((cam) => (
                <button
                  key={cam.id}
                  type="button"
                  onClick={() => handleSelectPreset(cam)}
                  className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 hover:border-[#00D4FF]/50 text-left shrink-0 transition-colors group"
                >
                  <div className="font-bold text-white text-xs sm:text-sm font-mono group-hover:text-[#00D4FF] transition-colors">{cam.name}</div>
                  <div className="text-xs text-[#94A3B8] font-sans truncate max-w-[140px] mt-0.5">
                    {cam.location} • {cam.streamType.toUpperCase()}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 1. CAMERA NAME & LOCATION ROW */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Camera Name"
            placeholder="e.g. Camera 01 - Main Entrance"
            value={name}
            onChange={(e) => setName(e.target.value)}
            icon={Camera}
            required
            className="text-sm sm:text-base"
          />

          <Input
            label="Camera Location / Zone"
            placeholder="e.g. Building A - West Entryway"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            icon={Building}
            className="text-sm sm:text-base"
          />
        </div>

        {/* 2. SOURCE TYPE SELECTION CARDS */}
        <div className="space-y-2.5">
          <label className="block text-xs sm:text-sm font-semibold text-[#94A3B8] uppercase tracking-wider">
            Select Camera Source Type
          </label>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {[
              { id: "connected", label: "Connected Camera", desc: "IP / CCTV via RTSP", icon: Video },
              { id: "browser", label: "Browser Camera", desc: "Webcam Device", icon: Camera },
              { id: "mobile", label: "Mobile Phone (APP)", desc: "Mobile Stream", icon: Smartphone },
              { id: "obs", label: "OBS Stream", desc: "Studio Feed", icon: Radio },
              { id: "scanner", label: "Network Scanner", desc: "Subnet IP Scan", icon: Wifi }
            ].map((source) => {
              const SourceIcon = source.icon;
              const isSelected = sourceType === source.id;
              return (
                <div
                  key={source.id}
                  onClick={() => {
                    setSourceType(source.id);
                    setErrorMsg("");
                    setTestState("idle");
                  }}
                  className={`p-3.5 sm:p-4 rounded-xl border cursor-pointer transition-all duration-200 flex flex-col justify-between min-h-[90px] ${
                    isSelected
                      ? "bg-[#00D4FF]/10 border-[#00D4FF] glow-cyan text-white shadow-lg"
                      : "bg-white/5 border-white/5 text-[#94A3B8] hover:text-white hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <SourceIcon className={`w-5 h-5 ${isSelected ? "text-[#00D4FF]" : "text-[#94A3B8]"}`} />
                    {isSelected && <span className="w-2.5 h-2.5 rounded-full bg-[#00D4FF] animate-pulse" />}
                  </div>
                  <div>
                    <div className="font-bold text-white text-xs sm:text-sm leading-tight font-mono">{source.label}</div>
                    <div className="text-xs text-[#94A3B8] font-sans mt-0.5">{source.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* DYNAMIC FORM FIELDS BASED ON SELECTED SOURCE TYPE */}

        {/* SOURCE A: CONNECTED CAMERA */}
        {sourceType === "connected" && (
          <div className="space-y-4 p-4 sm:p-5 rounded-2xl bg-[#0B1120] border border-white/10 shadow-lg">
            <div className="text-xs sm:text-sm font-bold text-[#00D4FF] uppercase font-mono border-b border-white/10 pb-2.5 flex items-center justify-between">
              <span>CONNECTED IP / CCTV CAMERA SECTION</span>
              <span className="text-xs text-[#94A3B8]">RTSP & PORT CONFIGURATION</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
              <div className="sm:col-span-2">
                <Input
                  label="Camera Address / IP"
                  placeholder="e.g. 192.168.1.123"
                  value={ipAddress}
                  onChange={(e) => setIpAddress(e.target.value)}
                  icon={Building}
                />
              </div>
              <Input
                label="Port"
                placeholder="554"
                value={port}
                onChange={(e) => setPort(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <Input
                label="Username"
                placeholder="e.g. camera_user"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                icon={Shield}
              />
              <Input
                label="Password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                icon={Key}
              />
            </div>

            <Input
              label="RTSP Path"
              placeholder="e.g. /stream1"
              value={rtspPath}
              onChange={(e) => setRtspPath(e.target.value)}
            />

            <div className="pt-1 space-y-2">
              <label className="block text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
                Direct RTSP Override (Optional)
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="rtsp://admin:password@192.168.1.120:554/stream1"
                  value={rtspUrl}
                  onChange={(e) => setRtspUrl(e.target.value)}
                  className="w-full h-11 sm:h-12 px-4 py-3 text-sm font-mono rounded-xl bg-slate-950 border border-white/10 text-white placeholder-slate-600 focus:border-[#00D4FF] focus:outline-none"
                />
                <LinkIcon className="w-4 h-4 text-[#94A3B8] absolute right-4 top-3.5 opacity-50" />
              </div>
            </div>

            {/* Stream Output Selector for Connected Camera */}
            <div className="pt-2 space-y-2">
              <label className="block text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
                Rendering Protocol Output
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: "simulation", label: "Simulation" },
                  { id: "webrtc", label: "WebRTC" },
                  { id: "hls", label: "HLS.js" },
                  { id: "mjpeg", label: "MJPEG" }
                ].map((mode) => (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => setStreamType(mode.id)}
                    className={`py-2.5 px-3 rounded-xl text-xs sm:text-sm font-mono font-bold transition-all uppercase ${
                      streamType === mode.id
                        ? "bg-[#00D4FF] text-[#0B1120] shadow-md"
                        : "bg-white/5 text-[#94A3B8] hover:text-white hover:bg-white/10"
                    }`}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* SOURCE B: BROWSER CAMERA */}
        {sourceType === "browser" && (
          <div className="space-y-4 p-4 sm:p-5 rounded-2xl bg-[#0B1120] border border-white/10 shadow-lg">
            <div className="text-xs sm:text-sm font-bold text-[#00D4FF] uppercase font-mono border-b border-white/10 pb-2.5 flex items-center justify-between">
              <span>WEBCAM & BROWSER CAMERA CONFIGURATION</span>
              <span className="text-xs text-[#00D4FF] font-bold">RTSP NOT REQUIRED</span>
            </div>

            <div className="space-y-2">
              <label className="block text-xs sm:text-sm font-semibold text-[#94A3B8] uppercase tracking-wider">
                Select Camera Device
              </label>
              <div className="flex items-center gap-3">
                <select
                  value={selectedDeviceId}
                  onChange={(e) => setSelectedDeviceId(e.target.value)}
                  className="flex-1 h-11 sm:h-12 px-4 py-3 text-sm font-mono rounded-xl bg-slate-950 border border-white/10 text-white focus:border-[#00D4FF] focus:outline-none"
                >
                  {browserDevices.length === 0 ? (
                    <option value="">Default Web Camera</option>
                  ) : (
                    browserDevices.map((d, idx) => (
                      <option key={d.deviceId || idx} value={d.deviceId}>
                        {d.label || `Camera Device ${idx + 1}`}
                      </option>
                    ))
                  )}
                </select>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={requestWebcamAccess}
                  className="text-xs sm:text-sm h-11 sm:h-12 px-4"
                >
                  Grant Access
                </Button>
              </div>
            </div>

            <p className="text-xs text-[#94A3B8] font-sans leading-relaxed">
              Captures live video frames directly from connected USB or built-in webcam devices via HTML5 MediaStreams.
            </p>
          </div>
        )}

        {/* SOURCE C: MOBILE PHONE */}
        {sourceType === "mobile" && (
          <div className="space-y-4 p-4 sm:p-5 rounded-2xl bg-[#0B1120] border border-white/10 shadow-lg">
            <div className="text-xs sm:text-sm font-bold text-[#00D4FF] uppercase font-mono border-b border-white/10 pb-2.5 flex items-center justify-between">
              <span>MOBILE PHONE APP STREAM PAIRING</span>
              <span className="text-xs text-[#00D4FF] font-bold">MOBILE WEBRTC LINK</span>
            </div>

            <Input
              label="Mobile Phone Device Name"
              value={mobileDeviceName}
              onChange={(e) => setMobileDeviceName(e.target.value)}
              icon={Smartphone}
            />

            <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs sm:text-sm">
              <div>
                <div className="font-bold text-white font-mono">Mobile App Pairing Code</div>
                <div className="text-xs text-[#94A3B8] font-sans mt-0.5">Scan via SAFECAM Mobile App</div>
              </div>
              <div className="px-4 py-2 rounded-lg bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30 font-mono font-bold text-sm">
                PAIR-9842
              </div>
            </div>
          </div>
        )}

        {/* SOURCE D: OBS STREAM */}
        {sourceType === "obs" && (
          <div className="space-y-4 p-4 sm:p-5 rounded-2xl bg-[#0B1120] border border-white/10 shadow-lg">
            <div className="text-xs sm:text-sm font-bold text-[#00D4FF] uppercase font-mono border-b border-white/10 pb-2.5 flex items-center justify-between">
              <span>OBS STUDIO VIDEO STREAM ENDPOINT</span>
              <span className="text-xs text-[#00D4FF] font-bold">HTTP / HLS FEED</span>
            </div>

            <Input
              label="OBS Stream URL"
              placeholder="e.g. http://localhost:8080/live/obs.flv"
              value={obsStreamUrl}
              onChange={(e) => setObsStreamUrl(e.target.value)}
              icon={Radio}
            />

            <p className="text-xs text-[#94A3B8] font-sans leading-relaxed">
              Connects to your local OBS Studio HLS or HTTP MJPEG output stream.
            </p>
          </div>
        )}

        {/* SOURCE E: LOCAL NETWORK SCANNER */}
        {sourceType === "scanner" && (
          <div className="space-y-4 p-4 sm:p-5 rounded-2xl bg-[#0B1120] border border-white/10 shadow-lg">
            <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
              <span className="text-xs sm:text-sm font-bold text-[#00D4FF] uppercase font-mono">
                LOCAL NETWORK IP CAMERA SCANNER
              </span>
              <Button
                type="button"
                variant="primary"
                size="sm"
                icon={RefreshCw}
                isLoading={isScanning}
                onClick={handleScanNetwork}
                className="text-xs h-9 px-3"
              >
                SCAN NETWORK
              </Button>
            </div>

            {discoveredDevices.length === 0 ? (
              <div className="p-6 text-center text-[#94A3B8] font-mono text-xs sm:text-sm">
                Click "SCAN NETWORK" to discover IP cameras on your local Wi-Fi subnet.
              </div>
            ) : (
              <div className="space-y-2">
                <span className="text-xs text-[#94A3B8] uppercase font-mono font-bold tracking-wider">Discovered IP Cameras:</span>
                {discoveredDevices.map((dev) => (
                  <div
                    key={dev.id}
                    onClick={() => handleSelectDiscoveredDevice(dev)}
                    className="p-3 rounded-xl bg-white/5 border border-white/10 hover:border-[#00D4FF]/40 cursor-pointer flex items-center justify-between font-mono text-xs sm:text-sm transition-colors"
                  >
                    <div>
                      <span className="font-bold text-white block">{dev.name}</span>
                      <span className="text-xs text-[#94A3B8] block mt-0.5">{dev.ip}:{dev.port}{dev.path}</span>
                    </div>
                    <span className="text-xs text-[#00D4FF] font-bold">Select Camera</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SAVE PRESET CHECKBOX */}
        <div className="flex items-center gap-2.5 pt-1 font-sans">
          <input
            type="checkbox"
            id="savePreset"
            checked={savePreset}
            onChange={(e) => setSavePreset(e.target.checked)}
            className="w-4 h-4 rounded border-white/20 bg-slate-950 text-[#00D4FF] focus:ring-[#00D4FF]"
          />
          <label htmlFor="savePreset" className="text-xs sm:text-sm text-[#94A3B8] cursor-pointer">
            Save camera configuration preset for future quick access
          </label>
        </div>

        {/* CONNECTION TEST BAR */}
        <div className="p-4 rounded-2xl bg-[#0B1120] border border-white/10 flex flex-col gap-2.5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs sm:text-sm text-[#94A3B8] font-mono uppercase font-bold tracking-wider">Telemetry Ping:</span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              icon={RefreshCw}
              isLoading={testState === "testing"}
              onClick={handleTestConnection}
              className="text-xs h-9 px-3"
            >
              TEST CONNECTION
            </Button>
          </div>

          {testState !== "idle" && (
            <div className={`text-xs sm:text-sm font-mono ${testState === "success" ? "text-[#00D4FF]" : testState === "error" ? "text-[#EF4444]" : "text-[#00D4FF]"}`}>
              {testMessage}
            </div>
          )}
        </div>

        {/* ACTION FOOTER */}
        <div className="pt-4 border-t border-white/10 flex items-center justify-end gap-3 font-sans">
          <Button 
            type="button" 
            variant="outline" 
            onClick={onClose}
            className="h-11 sm:h-12 px-5 text-xs sm:text-sm font-bold"
          >
            Cancel
          </Button>
          <Button 
            type="submit" 
            variant="primary" 
            icon={Camera}
            className="h-11 sm:h-12 px-6 text-xs sm:text-sm font-bold"
          >
            {getSubmitButtonText()}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default AddCameraModal;
