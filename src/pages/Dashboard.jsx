import React from "react";
import { useNavigate } from "react-router-dom";
import { 
  Camera, 
  ShieldAlert, 
  Activity, 
  Users, 
  TrendingUp, 
  PieChart, 
  ChevronRight,
  AlertTriangle
} from "lucide-react";
import { useSocket } from "../context/SocketContext";
import { useAuth } from "../context/AuthContext";
import { useCamera } from "../hooks/useCamera";
import StatCard from "../components/ui/StatCard";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import IncidentChart from "../components/charts/IncidentChart";
import EventDistribution from "../components/charts/EventDistribution";

export const Dashboard = () => {
  const navigate = useNavigate();
  const { activeAlerts, detectionMap, resolveAlert } = useSocket();
  const { user } = useAuth();
  const { cameras, selectCamera } = useCamera();

  const activeUnresolvedAlerts = activeAlerts.filter((a) => a && a.status === "active");
  const onlineCameraCount = cameras.filter((c) => c.status === "online").length;

  // Compute total people currently detected across all cameras
  const totalPeopleMonitored = Object.values(detectionMap || {}).reduce(
    (acc, detections) => acc + (detections ? detections.length : 0),
    cameras.reduce((sum, cam) => sum + (cam.peopleCount || 0), 0)
  );

  return (
    <div className="space-y-6">
      {/* Dashboard Greeting Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[#F8FAFC] tracking-tight">
          Good evening, {user?.displayName?.split(" ")[0] || "Operator"}
        </h1>
        <p className="text-sm text-[#94A3B8] mt-1 font-sans">
          Monitor your safety environment and real-time AI security telemetry
        </p>
      </div>

      {/* Top Stat Cards Grid: Large Visually Dominant Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Cameras Online"
          value={`${onlineCameraCount} / ${cameras.length}`}
          subtitle={`${onlineCameraCount} active CCTV streams connected`}
          icon={Camera}
        />

        <StatCard
          title="Threat Alerts"
          value={activeUnresolvedAlerts.length.toString()}
          subtitle="Requires immediate security review"
          icon={AlertTriangle}
          isAlert={activeUnresolvedAlerts.length > 0}
        />

        <StatCard
          title="People Monitored"
          value={totalPeopleMonitored.toString()}
          subtitle="Real-time bounding box count"
          icon={Users}
        />

        <StatCard
          title="AI Inference"
          value="10 FPS"
          subtitle="Mean telemetry latency: 22ms"
          icon={Activity}
        />
      </div>

      {/* Middle Section Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Incident Trend Chart (7 cols) */}
        <div className="lg:col-span-7">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
              <div>
                <h3 className="text-base font-bold text-[#F8FAFC] flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-[#00D4FF]" />
                  24-Hour Threat & Incident Trend
                </h3>
                <p className="text-xs text-[#94A3B8] mt-0.5">Temporal telemetry detection history</p>
              </div>
            </div>
            <IncidentChart />
          </Card>
        </div>

        {/* Event Type Distribution (5 cols) */}
        <div className="lg:col-span-5">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
              <div>
                <h3 className="text-base font-bold text-[#F8FAFC] flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-[#00D4FF]" />
                  Event Type Breakdown
                </h3>
                <p className="text-xs text-[#94A3B8] mt-0.5">Classified detection categories</p>
              </div>
            </div>
            <EventDistribution />
          </Card>
        </div>
      </div>

      {/* Lower Section: Connected Cameras & Recent Alerts Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Live Cameras Summary Card */}
        <Card glow="cyan" className="p-5">
          <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
            <div>
              <h3 className="text-base font-bold text-[#F8FAFC] flex items-center gap-2">
                <Camera className="w-5 h-5 text-[#00D4FF]" />
                LIVE CAMERAS
              </h3>
              <p className="text-xs text-[#94A3B8] mt-0.5">Connected security monitoring channels</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-[#00D4FF] px-2.5 py-1 rounded-lg bg-[#00D4FF]/10 border border-[#00D4FF]/30">
                ● {onlineCameraCount} ONLINE
              </span>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate("/monitoring")}
                className="text-xs py-1.5 px-3 bg-[#00D4FF] text-[#0B1120] font-bold"
              >
                OPEN MONITORING <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="space-y-2.5">
            {cameras.map((cam) => {
              const isCamOnline = cam.status === "online";
              const isCamThreat = (detectionMap[cam.id] || []).some((d) => d.role === "attacker") || cam.hasActiveAlert;

              return (
                <div
                  key={cam.id}
                  onClick={() => navigate(`/monitoring/${cam.id}`)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between text-sm ${
                    isCamThreat
                      ? "bg-[#EF4444]/10 border-[#EF4444]/40 text-white shadow-md"
                      : "bg-white/5 border-white/10 text-slate-200 hover:border-[#00D4FF]/40 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`w-2.5 h-2.5 rounded-full ${isCamOnline ? (isCamThreat ? "bg-[#EF4444] animate-ping" : "bg-[#00D4FF]") : "bg-slate-500"}`} />
                    <div>
                      <div className="font-bold text-white font-mono">{cam.name}</div>
                      <div className="text-xs text-[#94A3B8]">{cam.location}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className={`font-bold ${isCamOnline ? (isCamThreat ? "text-[#EF4444]" : "text-[#00D4FF]") : "text-slate-500"}`}>
                      {isCamOnline ? (isCamThreat ? "THREAT" : "● LIVE") : "● OFFLINE"}
                    </span>
                    <ChevronRight className="w-4 h-4 text-[#00D4FF]" />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Critical Threat Stream Card */}
        <Card glow={activeUnresolvedAlerts.length > 0 ? "red" : "none"} className="p-5">
          <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
            <div>
              <h3 className="text-base font-bold text-[#F8FAFC] flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-[#EF4444]" />
                Recent Critical Threats
              </h3>
              <p className="text-xs text-[#94A3B8] mt-0.5">Real-time alert telemetry stream</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/alerts")}
              className="text-xs py-1.5 px-3 font-semibold text-slate-200 border-white/20 hover:bg-white/10"
            >
              View All Alerts
            </Button>
          </div>

          <div className="space-y-2.5">
            {activeAlerts.length === 0 ? (
              <div className="p-8 text-center text-sm font-sans text-[#94A3B8]">
                No active threat alerts detected.
              </div>
            ) : (
              activeAlerts.slice(0, 3).map((alert) => (
                <div
                  key={alert.id}
                  className="p-3 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-sm"
                >
                  <div className="flex items-center gap-3">
                    <span className={`w-2.5 h-2.5 rounded-full ${alert.status === "active" ? "bg-[#EF4444] animate-ping" : "bg-[#00D4FF]"}`} />
                    <div>
                      <span className="font-extrabold text-[#EF4444] uppercase tracking-wide">{(alert.type || "alert").replace("_", " ")}</span>
                      <p className="text-xs text-[#94A3B8] font-sans mt-0.5">{alert.cameraName || alert.location || "Surveillance Zone"} • {alert.action || "Detection"}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold font-mono text-[#00D4FF]">
                      {alert.confidence != null ? `${(alert.confidence * (alert.confidence <= 1 ? 100 : 1)).toFixed(0)}%` : "N/A"}
                    </span>
                    {alert.status === "active" ? (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => resolveAlert(alert.id)}
                        className="text-xs py-1 px-2.5 bg-red-600 hover:bg-red-500 font-bold"
                      >
                        Resolve
                      </Button>
                    ) : (
                      <Badge variant="cyan">Resolved</Badge>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
