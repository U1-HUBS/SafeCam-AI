import React from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Clock, Camera, Eye, Check, Trash2 } from "lucide-react";
import AlertBadge from "./AlertBadge";
import Button from "../ui/Button";

export const AlertCard = ({ alert, onView, onResolve, onDelete }) => {
  if (!alert) return null;

  const isResolved = alert.status === "resolved";
  const confidencePercent = alert.confidence != null
    ? `${(alert.confidence * (alert.confidence <= 1 ? 100 : 1)).toFixed(0)}%`
    : "N/A";

  return (
    <motion.div
      whileHover={{ y: -2 }}
      className={`rounded-2xl p-5 border transition-all duration-300 shadow-xl ${
        isResolved
          ? "bg-[#0B1120]/80 border-white/10 opacity-75"
          : alert.severity === "critical"
          ? "bg-[#EF4444]/10 border-[#EF4444]/40 shadow-red-950/20"
          : "bg-amber-500/10 border-amber-500/30"
      }`}
    >
      {/* Top Status & Title Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
        <div className="flex items-center gap-3">
          <AlertBadge severity={isResolved ? "resolved" : alert.severity || "critical"} />
          <h3 className="text-base font-extrabold text-[#F8FAFC] tracking-tight uppercase">
            {(alert.type || "BULLYING CONFIRMED").replace("_", " ")}
          </h3>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[#94A3B8] font-medium">
          <Clock className="w-4 h-4 text-[#00D4FF]" />
          <span>{alert.timeAgo || "Just now"}</span>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
        {/* Snapshot Preview Container */}
        <div className="relative rounded-xl overflow-hidden border border-white/10 aspect-video bg-slate-950 group shadow-inner">
          {alert.snapshotUrl || alert.snapshotPath ? (
            <img
              src={alert.snapshotUrl || alert.snapshotPath}
              alt="Incident Snapshot"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-[#94A3B8] text-xs font-mono gap-1">
              <Camera className="w-6 h-6 text-slate-600" />
              <span>[ NO SNAPSHOT ]</span>
            </div>
          )}
          <div className="absolute top-2 left-2 px-2.5 py-1 rounded-lg bg-slate-950/90 backdrop-blur-md text-xs font-semibold text-white flex items-center gap-1.5 border border-white/10">
            <Camera className="w-3.5 h-3.5 text-[#00D4FF]" />
            <span>{alert.cameraId || alert.cameraName || "CAM-01"}</span>
          </div>
        </div>

        {/* Highly Legible Details */}
        <div className="sm:col-span-2 space-y-2 text-sm font-sans">
          <div className="flex items-center justify-between py-1 border-b border-white/5">
            <span className="text-[#94A3B8] font-medium">Camera:</span>
            <span className="font-bold text-[#F8FAFC]">{alert.cameraName || alert.location || "Surveillance Zone"}</span>
          </div>
          <div className="flex items-center justify-between py-1 border-b border-white/5">
            <span className="text-[#94A3B8] font-medium">Action Triggered:</span>
            <span className="font-bold text-[#EF4444] uppercase tracking-wide">{alert.action || "PUSH / ATTACK"}</span>
          </div>
          <div className="flex items-center justify-between py-1">
            <span className="text-[#94A3B8] font-medium">AI Confidence:</span>
            <span className="font-extrabold text-[#00D4FF] text-base">{confidencePercent}</span>
          </div>
          {isResolved && alert.resolvedBy && (
            <div className="flex items-center justify-between py-1 text-[#00D4FF]">
              <span>Resolved By:</span>
              <span className="font-semibold">{alert.resolvedBy}</span>
            </div>
          )}
        </div>
      </div>

      {/* Footer Actions: Delete, View Event, Resolve */}
      <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-end gap-2.5">
        {onDelete && (
          <Button
            variant="ghost"
            size="sm"
            icon={Trash2}
            onClick={() => onDelete(alert.id || alert.incident_id)}
            className="text-xs py-2 px-3 text-[#EF4444] hover:bg-[#EF4444]/15 hover:text-red-300 font-semibold"
          >
            Delete
          </Button>
        )}

        <Button
          variant="outline"
          size="sm"
          icon={Eye}
          onClick={() => onView && onView(alert)}
          className="text-xs py-2 px-3 font-semibold text-slate-200 border-white/20 hover:bg-white/10"
        >
          View Event
        </Button>

        {!isResolved && (
          <Button
            variant="primary"
            size="sm"
            icon={Check}
            onClick={() => onResolve && onResolve(alert.id || alert.incident_id)}
            className="text-xs py-2 px-3.5 bg-[#00D4FF] text-[#0B1120] font-bold hover:bg-[#00D4FF]/90"
          >
            Resolve
          </Button>
        )}
      </div>
    </motion.div>
  );
};

export default AlertCard;
