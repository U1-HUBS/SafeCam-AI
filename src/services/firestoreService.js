// SAFECAM AI — Firestore Database Service (Web SDK v12 + Real-Time Sync)
import { 
  collection, 
  getDocs, 
  doc, 
  setDoc,
  updateDoc, 
  deleteDoc,
  addDoc, 
  query, 
  orderBy,
  onSnapshot 
} from "firebase/firestore";
import { db } from "./firebase";

export const firestoreService = {
  // ---------------------------------------------------------------------------
  // 1. CAMERAS COLLECTION
  // ---------------------------------------------------------------------------
  
  // Real-time camera listener
  subscribeToCameras(callback) {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const camerasRef = collection(db, "cameras");
        return onSnapshot(
          camerasRef,
          (snapshot) => {
            const cameras = [];
            snapshot.forEach((docSnap) => {
              cameras.push({ id: docSnap.id, ...docSnap.data() });
            });
            callback(cameras);
          },
          (error) => {
            console.warn("Firestore cameras snapshot listener error:", error.message);
            callback([]);
          }
        );
      }
    } catch (err) {
      console.warn("Firestore subscribeToCameras failed:", err.message);
    }
    callback([]);
    return () => {};
  },

  async getCameras() {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const querySnapshot = await getDocs(collection(db, "cameras"));
        const cameras = [];
        querySnapshot.forEach((docSnap) => cameras.push({ id: docSnap.id, ...docSnap.data() }));
        return cameras;
      }
    } catch (err) {
      console.warn("Firestore getCameras failed:", err.message);
    }
    return [];
  },

  async saveCameraDoc(cameraObj) {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const docRef = doc(db, "cameras", cameraObj.id);
        await setDoc(docRef, cameraObj, { merge: true });
        return cameraObj;
      }
    } catch (err) {
      console.warn("Firestore saveCameraDoc failed:", err.message);
    }
    return cameraObj;
  },

  async updateCameraDoc(id, fields) {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const docRef = doc(db, "cameras", id);
        await updateDoc(docRef, fields);
      }
    } catch (err) {
      console.warn("Firestore updateCameraDoc failed:", err.message);
    }
  },

  async deleteCameraDoc(id) {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const docRef = doc(db, "cameras", id);
        await deleteDoc(docRef);
      }
    } catch (err) {
      console.warn("Firestore deleteCameraDoc failed:", err.message);
    }
  },

  // ---------------------------------------------------------------------------
  // 2. ALERTS COLLECTION
  // ---------------------------------------------------------------------------

  // Real-time alerts listener
  subscribeToAlerts(callback) {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const alertsRef = collection(db, "alerts");
        return onSnapshot(
          alertsRef,
          (snapshot) => {
            const alerts = [];
            snapshot.forEach((docSnap) => {
              alerts.push({ id: docSnap.id, ...docSnap.data() });
            });
            callback(alerts);
          },
          (error) => {
            console.warn("Firestore alerts snapshot listener error:", error.message);
            callback([]);
          }
        );
      }
    } catch (err) {
      console.warn("Firestore subscribeToAlerts failed:", err.message);
    }
    callback([]);
    return () => {};
  },

  async getAlerts() {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const querySnapshot = await getDocs(collection(db, "alerts"));
        const alerts = [];
        querySnapshot.forEach((docSnap) => alerts.push({ id: docSnap.id, ...docSnap.data() }));
        return alerts;
      }
    } catch (err) {
      console.warn("Firestore getAlerts failed:", err.message);
    }
    return [];
  },

  async createRealAlert(alertData) {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const alertRef = doc(db, "alerts", alertData.id);
        await setDoc(alertRef, alertData, { merge: true });
        
        // Also log to events_logs collection
        const logRef = doc(db, "events_logs", `log_${alertData.id}`);
        await setDoc(logRef, {
          id: `log_${alertData.id}`,
          time: new Date(alertData.timestamp).toLocaleTimeString(),
          date: new Date(alertData.timestamp).toISOString().split("T")[0],
          datetime: alertData.timestamp,
          camera: alertData.cameraName || alertData.cameraId,
          location: alertData.location || "Surveillance Zone",
          event: "Bullying Detected",
          action: alertData.action || "Physical Aggression",
          confidence: `${Math.round((alertData.confidence || 0.9) * 100)}%`,
          severity: alertData.severity || "Critical",
          status: "Active Alert",
          details: `Confirmed bullying event on ${alertData.cameraName || alertData.cameraId}`
        }, { merge: true });

        return alertData;
      }
    } catch (err) {
      console.warn("Firestore createRealAlert failed:", err.message);
    }
    return alertData;
  },

  async resolveAlert(alertId, resolverName = "User") {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const alertRef = doc(db, "alerts", alertId);
        await updateDoc(alertRef, {
          status: "resolved",
          resolvedAt: new Date().toISOString(),
          resolvedBy: resolverName
        });
      }
    } catch (err) {
      console.warn("Firestore resolveAlert failed:", err.message);
    }
    return { alertId, status: "resolved", resolvedBy: resolverName };
  },

  async deleteAlertDoc(alertId) {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const alertRef = doc(db, "alerts", alertId);
        await deleteDoc(alertRef);
      }
    } catch (err) {
      console.warn("Firestore deleteAlertDoc failed:", err.message);
    }
  },

  // ---------------------------------------------------------------------------
  // 3. EVENTS & AUDIT LOGS COLLECTION
  // ---------------------------------------------------------------------------

  subscribeToLogs(callback) {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const logsRef = collection(db, "events_logs");
        return onSnapshot(
          logsRef,
          (snapshot) => {
            const logs = [];
            snapshot.forEach((docSnap) => {
              logs.push({ id: docSnap.id, ...docSnap.data() });
            });
            callback(logs);
          },
          (error) => {
            console.warn("Firestore logs snapshot listener error:", error.message);
            callback([]);
          }
        );
      }
    } catch (err) {
      console.warn("Firestore subscribeToLogs failed:", err.message);
    }
    callback([]);
    return () => {};
  },

  async getEventsLogs() {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const querySnapshot = await getDocs(collection(db, "events_logs"));
        const logs = [];
        querySnapshot.forEach((docSnap) => logs.push({ id: docSnap.id, ...docSnap.data() }));
        return logs;
      }
    } catch (err) {
      console.warn("Firestore getEventsLogs failed:", err.message);
    }
    return [];
  },

  async deleteLogDoc(logId) {
    try {
      if (import.meta.env.VITE_USE_FIREBASE === "true") {
        const logRef = doc(db, "events_logs", logId);
        await deleteDoc(logRef);
      }
    } catch (err) {
      console.warn("Firestore deleteLogDoc failed:", err.message);
    }
  }
};

export default firestoreService;
