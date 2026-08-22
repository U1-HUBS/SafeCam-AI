import React from "react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import AlertBadge from "./AlertBadge";
import { Camera, Clock, CheckCircle, ShieldAlert, Crosshair } from "lucide-react";

export const AlertModal = ({ alert, isOpen, onClose, onResolve }) => {
  if (!alert) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`INCIDENT REPORT: ${alert.id || 'N/A'}`}
      subtitle={`Timestamp: ${alert.timestamp || 'Real-time'} • Camera: ${alert.cameraName || alert.cameraId || 'Surveillance Zone'}`}
      maxWidth="max-w-3xl"
    >
      <div className="space-y-6">
        {/* Header Alert Status Banner */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-white/5 border border-white/10">
          <div className="flex items-center gap-3">
            <AlertBadge severity={alert.status === "resolved" ? "resolved" : alert.severity} />
            <div>
              <div className="text-sm font-extrabold text-[#F8FAFC] uppercase font-mono">{(alert.type || "alert").replace("_", " ")}</div>
              <div className="text-xs text-[#94A3B8]">Action Trigger: <span className="text-[#EF4444] font-semibold">{alert.action || "Detection"}</span></div>
            </div>
          </div>
          <div className="text-right font-mono">
            <div className="text-xs text-[#94A3B8]">Confidence</div>
            <div className="text-lg font-bold text-[#00D4FF]">
              {alert.confidence != null ? `${(alert.confidence * (alert.confidence <= 1 ? 100 : 1)).toFixed(0)}%` : "N/A"}
            </div>
          </div>
        </div>

        {/* Snapshot & Bounding Box Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="relative rounded-xl overflow-hidden border border-white/10 aspect-video bg-slate-950 flex items-center justify-center">
            {alert.snapshotUrl ? (
              <img
                src={alert.snapshotUrl}
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

            {alert.attacker && (
              <div className="p-2.5 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 space-y-1">
                <div className="flex items-center justify-between text-[#EF4444] font-mono font-bold">
                  <span>🚨 SUBJECT A (ATTACKER)</span>
                  <span>ID: {alert.attacker.id}</span>
                </div>
                <div className="text-[#F8FAFC]">Motion: {alert.attacker.action}</div>
                <div className="text-[10px] text-[#94A3B8]">Bounding Box: X:{alert.attacker.box?.x} Y:{alert.attacker.box?.y} W:{alert.attacker.box?.width} H:{alert.attacker.box?.height}</div>
              </div>
            )}

            {alert.victim && (
              <div className="p-2.5 rounded-lg bg-[#00D4FF]/10 border border-[#00D4FF]/30 space-y-1">
                <div className="flex items-center justify-between text-[#00D4FF] font-mono font-bold">
                  <span>🛡️ SUBJECT B (VICTIM)</span>
                  <span>ID: {alert.victim.id}</span>
                </div>
                <div className="text-[#F8FAFC]">Stance: {alert.victim.action}</div>
                <div className="text-[10px] text-[#94A3B8]">Bounding Box: X:{alert.victim.box?.x} Y:{alert.victim.box?.y} W:{alert.victim.box?.width} H:{alert.victim.box?.height}</div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Controls */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
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
