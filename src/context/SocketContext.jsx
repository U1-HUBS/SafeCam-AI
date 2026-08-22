import React, { createContext, useContext, useState, useEffect } from "react";
import socketService from "../services/socketService";
import firestoreService from "../services/firestoreService";
import { useAuth } from "./AuthContext";

const SocketContext = createContext(null);

export const SocketProvider = ({ children }) => {
  const { user } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [detectionMap, setDetectionMap] = useState({});
  const [cameraMetricsMap, setCameraMetricsMap] = useState({});

  useEffect(() => {
    socketService.connect();
    setIsConnected(true);

    // Subscribe to live Firestore alerts collection
    const unsubscribeFirestoreAlerts = firestoreService.subscribeToAlerts((liveAlerts) => {
      setActiveAlerts(liveAlerts);
    });

    // Socket Event Subscriptions
    const handleDetectionUpdate = (data) => {
      if (data && data.cameraId) {
        setDetectionMap((prev) => ({
          ...prev,
          [data.cameraId]: data.detections || []
        }));
        if (data.metrics) {
          setCameraMetricsMap((prev) => ({
            ...prev,
            [data.cameraId]: data.metrics
          }));
        }
      }
    };

    const handleNewAlert = (alertData) => {
      if (alertData) {
        setActiveAlerts((prev) => [alertData, ...prev]);
      }
    };

    socketService.on("detection_update", handleDetectionUpdate);
    socketService.on("alert_created", handleNewAlert);

    return () => {
      unsubscribeFirestoreAlerts();
      socketService.off("detection_update", handleDetectionUpdate);
      socketService.off("alert_created", handleNewAlert);
    };
  }, []);

  const resolveAlert = (alertId) => {
    firestoreService.resolveAlert(alertId, user?.displayName || "User");
    setActiveAlerts((prev) =>
      prev.map((alert) =>
        alert.id === alertId ? { ...alert, status: "resolved", resolvedAt: new Date().toISOString() } : alert
      )
    );
  };

  const deleteAlert = (alertId) => {
    firestoreService.deleteAlertDoc(alertId);
    setActiveAlerts((prev) => prev.filter((alert) => alert.id !== alertId));
  };

  return (
    <SocketContext.Provider
      value={{
        isConnected,
        activeAlerts,
        detectionMap,
        cameraMetricsMap,
        resolveAlert,
        deleteAlert
      }}
    >
      {children}
    </SocketContext.Provider>
  );
};

export const useSocket = () => {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error("useSocket must be used within a SocketProvider");
  }
  return context;
};
