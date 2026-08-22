import React, { createContext, useContext, useState, useEffect } from "react";
import { firestoreService } from "../services/firestoreService";

const CameraContext = createContext();

const LOCAL_STORAGE_KEY = "safecam_user_cameras_v1";

// Helper to mask credentials in RTSP URLs for display
export const maskRtspUrl = (url) => {
  if (!url) return "";
  return url.replace(/rtsp:\/\/([^:]+):([^@]+)@/, "rtsp://$1:••••••••@");
};

export const CameraProvider = ({ children }) => {
  const [cameras, setCameras] = useState(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (e) {
      console.error("Failed to parse saved cameras", e);
    }
    return [];
  });

  const [selectedCameraId, setSelectedCameraId] = useState(cameras[0]?.id || null);
  const [gridMode, setGridMode] = useState("auto"); // 'auto', '1x1', '2x2', '3x2', '4x4'
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all"); // 'all', 'online', 'offline', 'threat'
  const [loading, setLoading] = useState(true);

  // Subscribe to live Firestore Database cameras stream
  useEffect(() => {
    const unsubscribe = firestoreService.subscribeToCameras((liveCameras) => {
      setCameras(liveCameras);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  // Sync to local storage for backup
  useEffect(() => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(cameras));
    } catch (e) {
      console.error("Failed to save cameras to localStorage", e);
    }
  }, [cameras]);

  const selectedCamera = cameras.find((cam) => cam.id === selectedCameraId) || cameras[0] || null;

  const selectCamera = (id) => {
    if (cameras.some((c) => c.id === id)) {
      setSelectedCameraId(id);
    }
  };

  const addCamera = (newCam) => {
    const id = `camera-${String(cameras.length + 1).padStart(2, "0")}_${Date.now().toString().slice(-4)}`;
    const cameraObj = {
      id,
      name: newCam.name || `Camera ${cameras.length + 1}`,
      location: newCam.location || "Zone A - Main",
      sourceType: newCam.sourceType || (newCam.rtspUrl ? "rtsp" : "simulation"),
      rtspUrl: newCam.rtspUrl ? newCam.rtspUrl.trim() : "",
      streamType: newCam.streamType || "simulation",
      streamUrl: newCam.streamUrl || "",
      ipAddress: newCam.ipAddress || "",
      port: newCam.port || "554",
      username: newCam.username || "",
      password: newCam.password || "",
      rtspPath: newCam.rtspPath || "/stream1",
      deviceId: newCam.deviceId || "",
      obsStreamUrl: newCam.obsStreamUrl || "",
      mobileDeviceName: newCam.mobileDeviceName || "",
      resolution: newCam.resolution || "1920 × 1080",
      fps: 30,
      aiFps: 10,
      latencyMs: 220,
      peopleCount: 2,
      status: "online",
      connected: true,
      minimized: false,
      fullscreen: false,
      hasActiveAlert: false,
      lastAlert: "Normal Activity"
    };

    // Save to Firestore & local state
    firestoreService.saveCameraDoc(cameraObj);
    setCameras((prev) => [...prev, cameraObj]);
    return cameraObj;
  };

  const updateCamera = (id, updatedFields) => {
    firestoreService.updateCameraDoc(id, updatedFields);
    setCameras((prev) =>
      prev.map((cam) => (cam.id === id ? { ...cam, ...updatedFields } : cam))
    );
  };

  const removeCamera = (id) => {
    firestoreService.deleteCameraDoc(id);
    setCameras((prev) => {
      const filtered = prev.filter((cam) => cam.id !== id);
      if (selectedCameraId === id && filtered.length > 0) {
        setSelectedCameraId(filtered[0].id);
      }
      return filtered;
    });
  };

  const toggleMinimize = (id) => {
    const target = cameras.find((c) => c.id === id);
    const newMinimized = !target?.minimized;
    firestoreService.updateCameraDoc(id, { minimized: newMinimized });
    setCameras((prev) =>
      prev.map((cam) => (cam.id === id ? { ...cam, minimized: newMinimized } : cam))
    );
  };

  const reconnectCamera = (id) => {
    firestoreService.updateCameraDoc(id, { status: "connecting", connected: false });
    setCameras((prev) =>
      prev.map((cam) =>
        cam.id === id
          ? { ...cam, status: "connecting", connected: false }
          : cam
      )
    );

    setTimeout(() => {
      firestoreService.updateCameraDoc(id, { status: "online", connected: true, fps: 30 });
      setCameras((prev) =>
        prev.map((cam) =>
          cam.id === id
            ? { ...cam, status: "online", connected: true, fps: 30 }
            : cam
        )
      );
    }, 1800);
  };

  const resetToDefaultCameras = () => {
    localStorage.removeItem(LOCAL_STORAGE_KEY);
    firestoreService.getCameras().then((cams) => setCameras(cams));
  };

  return (
    <CameraContext.Provider
      value={{
        cameras,
        selectedCamera,
        selectedCameraId,
        selectCamera,
        addCamera,
        updateCamera,
        removeCamera,
        toggleMinimize,
        reconnectCamera,
        resetToDefaultCameras,
        gridMode,
        setGridMode,
        searchQuery,
        setSearchQuery,
        statusFilter,
        setStatusFilter,
        loading
      }}
    >
      {children}
    </CameraContext.Provider>
  );
};

export const useCameraContext = () => {
  const context = useContext(CameraContext);
  if (!context) {
    throw new Error("useCameraContext must be used within a CameraProvider");
  }
  return context;
};

export default CameraContext;
