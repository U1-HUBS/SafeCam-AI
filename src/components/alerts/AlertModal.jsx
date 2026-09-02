import React from "react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import AlertBadge from "./AlertBadge";
import { Camera, Clock, CheckCircle, ShieldAlert, Crosshair, Film, User } from "lucide-react";

export const AlertModal = ({ alert, isOpen, onClose, onResolve }) => {
  if (!alert) return null;

  const clipUrl     = alert.clipPath || alert.clip_path || null;
  const snapshotUrl = alert.snapshotUrl || alert.snapshotPath || alert.snapshot_path || null;
  const attackType  = (alert.type || "")
    .replace("BULLYING_CONFIRMED", "")
    .trim() || (alert.action || "").replace("BULLY — ", "") || "UNKNOWN";

  const confPct = alert.confidence != null
    ? `${(alert.confidence * (alert.confidence <= 1 ? 100 : 1)).toFixed(0)}%`
    : "N/A";

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`INCIDENT REPORT: ${alert.id || "N/A"}`}
      subtitle={`${alert.timeAgo || "Real-time"} • Camera: ${alert.cameraName || alert.cameraId || "Surveillance Zone"}`}
      maxWidth="max-w-3xl"
    >
      <div className="space-y-5">
        {/* Header Alert Status Banner */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-white/5 border border-white/10">
          <div className="flex items-center gap-3">
            <AlertBadge severity={alert.status === "resolved" ? "resolved" : alert.severity} />
            <div>
              <div className="text-sm font-extrabold text-[#F8FAFC] uppercase font-mono">
                {"\u{1F6A8}"} BULLYING DETECTED
              </div>
              <div className="text-xs text-[#94A3B8] mt-0.5">
                Type: <span className="text-[#EF4444] font-bold">{attackType}</span>
                {alert.attackerId && (
                  <span className="ml-3">Attacker: <span className="text-[#EF4444] font-semibold">ID {alert.attackerId}</span></span>
                )}
                {alert.victimId && (
                  <span className="ml-3">Victim: <span className="text-[#10B981] font-semibold">ID {alert.victimId}</span></span>
                )}
              </div>
            </div>
          </div>
          <div className="text-right font-mono">
            <div className="text-xs text-[#94A3B8]">Confidence</div>
            <div className="text-lg font-bold text-[#00D4FF]">{confPct}</div>
          </div>
        </div>

        {/* Incident Video Clip Player — shown when clip exists */}
        {clipUrl ? (
          <div className="rounded-xl overflow-hidden border border-[#EF4444]/40 bg-slate-950">
            <div className="flex items-center gap-2 px-3 py-2 border-b border-white/10 bg-[#EF4444]/10">
              <Film className="w-4 h-4 text-[#EF4444]" />
              <span className="text-xs font-mono font-bold text-[#EF4444] uppercase tracking-wider">
                Incident Recording
              </span>
            </div>
            <video
              controls
              className="w-full max-h-72 bg-black"
              src={`http://localhost:8000${clipUrl}`}
              preload="metadata"
            >
              Your browser does not support video playback.
            </video>
          </div>
        ) : (
          /* Snapshot + AI Details — shown when no clip yet */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="relative rounded-xl overflow-hidden border border-white/10 aspect-video bg-slate-950 flex items-center justify-center">
              {snapshotUrl ? (
                <img
                  src={snapshotUrl.startsWith("/") ? `http://localhost:8000${snapshotUrl}` : snapshotUrl}
                  alt="Incident Snapshot"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-[#94A3B8] text-xs font-mono">[ NO SNAPSHOT AVAILABLE ]</div>
              )}
              <div className="absolute top-2 left-2 px-2 py-1 rounded bg-slate-950/80 backdrop-blur-md text-[10px] font-mono text-white flex items-center gap-1.5">
                <Camera className="w-3.5 h-3.5 text-[#00D4FF]" />
                <span>{alert.location || alert.cameraName || "Main Area"}</span>
              </div>
            </div>

            {/* AI Detection Breakdown */}
            <div className="space-y-3 p-4 rounded-xl bg-[#0B1120] border border-white/5 text-xs">
              <h4 className="font-bold text-[#F8FAFC] flex items-center gap-1.5 uppercase font-mono text-xs">
                <Crosshair className="w-4 h-4 text-[#00D4FF]" />
                AI Subject Breakdown
              </h4>

              {alert.attackerId && (
                <div className="p-2.5 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 space-y-1">
                  <div className="flex items-center justify-between text-[#EF4444] font-mono font-bold">
                    <span>ATTACKER</span>
                    <span>Track ID: {alert.attackerId}</span>
                  </div>
                  <div className="text-[#F8FAFC]">Action: {attackType}</div>
                </div>
              )}

              {alert.victimId && (
                <div className="p-2.5 rounded-lg bg-[#10B981]/10 border border-[#10B981]/30 space-y-1">
                  <div className="flex items-center justify-between text-[#10B981] font-mono font-bold">
                    <span>VICTIM</span>
                    <span>Track ID: {alert.victimId}</span>
                  </div>
                  <div className="text-[#F8FAFC]">Contact estimation confirmed</div>
                </div>
              )}

              <div className="text-[10px] text-[#94A3B8] leading-relaxed">
                Contact estimation is based on bounding-box analysis only.
                Requires human operator verification.
              </div>
            </div>
          </div>
        )}

        {/* Metadata Table */}
        <div className="p-3 rounded-xl bg-[#0B1120] border border-white/5 grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3 text-xs font-mono">
          {[
            ["Type",       attackType,                           "#EF4444"],
            ["Confidence", confPct,                              "#00D4FF"],
            ["Camera",     alert.cameraName || alert.cameraId || "—", null],
            ["Date",       alert.date || "—",                    null],
            ["Time",       alert.time || alert.timeAgo || "—",   null],
            ["Status",     alert.status === "resolved" ? "RESOLVED" : "CONFIRMED", null],
          ].map(([label, value, color]) => (
            <div key={label}>
              <div className="text-[#94A3B8] text-[10px] uppercase mb-0.5">{label}</div>
              <div
                className="font-bold"
                style={{ color: color || "#F8FAFC" }}
              >
                {value}
              </div>
            </div>
          ))}
        </div>

        {/* Modal Controls */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/10 flex-wrap">
          {clipUrl && (
            <a
              href={`http://localhost:8000${clipUrl}`}
              download
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border border-[#EF4444]/40 bg-[#EF4444]/10 text-[#EF4444] hover:bg-[#EF4444]/20 transition-colors"
            >
              <Film className="w-3.5 h-3.5" />
              Download Clip
            </a>
          )}
          <Button variant="outline" onClick={onClose}>
            Close Window
          </Button>
          {alert.status !== "resolved" && (
            <Button
              variant="primary"
              icon={CheckCircle}
              onClick={() => {
                onResolve && onResolve(alert.id);
                onClose();
              }}
            >
              Resolve Incident
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default AlertModal;
