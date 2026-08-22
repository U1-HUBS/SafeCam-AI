// SAFECAM AI — Socket.IO Realtime Telemetry Client
import { io } from "socket.io-client";
import { generateLiveDetections, generateLiveMetrics } from "./simulationEngine";

class SocketService {
  constructor() {
    this.socket = null;
    this.callbacks = new Map();
    this.isConnected = false;
    this.simulationTimer = null;
  }

  // Connect to Socket.IO backend or initiate simulation fallback
  connect(url = import.meta.env.VITE_SOCKET_URL || "http://localhost:5000") {
    if (import.meta.env.VITE_SOCKET_URL) {
      try {
        this.socket = io(url, {
          transports: ["websocket", "polling"],
          autoConnect: true,
          reconnection: true
        });

        this.socket.on("connect", () => {
          console.log("[Socket.IO] Connected to backend:", this.socket.id);
          this.isConnected = true;
          this.trigger("system_status", { online: true, status: "SYSTEM ONLINE" });
        });

        this.socket.on("disconnect", () => {
          console.log("[Socket.IO] Disconnected from backend");
          this.isConnected = false;
          this.trigger("system_status", { online: false, status: "DISCONNECTED" });
        });

        // Backend event bindings
        this.socket.on("alert_created", (data) => this.trigger("alert_created", data));
        this.socket.on("detection_update", (data) => this.trigger("detection_update", data));
        this.socket.on("camera_status", (data) => this.trigger("camera_status", data));
        this.socket.on("system_status", (data) => this.trigger("system_status", data));

        return;
      } catch (err) {
        console.warn("[Socket.IO] Backend connection error, falling back to local simulation:", err.message);
      }
    }

    // Connected state
    this.isConnected = true;
  }

  // Subscribe to real-time events
  on(event, callback) {
    if (!this.callbacks.has(event)) {
      this.callbacks.set(event, []);
    }
    this.callbacks.get(event).push(callback);
  }

  // Unsubscribe from real-time events
  off(event, callback) {
    if (!this.callbacks.has(event)) return;
    const list = this.callbacks.get(event).filter((cb) => cb !== callback);
    this.callbacks.set(event, list);
  }

  // Internal event emitter
  trigger(event, data) {
    if (this.callbacks.has(event)) {
      this.callbacks.get(event).forEach((cb) => cb(data));
    }
  }

  disconnect() {
    if (this.simulationTimer) clearInterval(this.simulationTimer);
    if (this.socket) this.socket.disconnect();
    this.isConnected = false;
  }
}

export const socketService = new SocketService();
export default socketService;
