import React from "react";
import { AlertTriangle, VolumeX, ShieldAlert, CheckCircle2 } from "lucide-react";
import audioAlertService from "../../services/audioAlertService";

export const BullyingAlarmBanner = ({ activeAlarm, onAcknowledge }) => {
  if (!activeAlarm || !activeAlarm.alarm_active) return null;

  const {
    camera_id,
    action,
    confidence,
    attacker_id,
    victim_id,
    started_at,
    reason,
    acknowledged
  } = activeAlarm;

  const handleSilence = () => {
    audioAlertService.stopAlarmSound();
    if (onAcknowledge) onAcknowledge(camera_id);
  };

  let formattedTime = "Just now";
  if (started_at) {
    try {
      const dt = new Date(started_at);
      if (!isNaN(dt.getTime())) {
        formattedTime = dt.toLocaleTimeString();
      }
    } catch (e) {}
  }

  return (
    <div className="w-full bg-gradient-to-r from-red-950 via-red-900 to-red-950 border-2 border-red-500/80 rounded-2xl p-4 sm:p-5 shadow-2xl shadow-red-950/80 animate-pulse-subtle my-4 text-white font-sans">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Left Warning Info */}
        <div className="flex items-start sm:items-center gap-3.5">
          <div className="p-3 rounded-xl bg-red-600/30 border border-red-500/60 text-red-400 shrink-0 animate-bounce">
            <AlertTriangle className="w-7 h-7 text-red-400" />
          </div>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-full bg-red-600 text-white font-mono text-[11px] font-black uppercase tracking-wider shadow">
                🚨 CONFIRMED BULLYING DETECTED
              </span>
              <span className="text-xs font-mono font-bold text-red-200">
                CAM: <code className="text-white">{camera_id}</code>
              </span>
              <span className="text-xs font-mono text-red-300">
                {formattedTime}
              </span>
            </div>

            <h2 className="text-base sm:text-lg font-black text-white mt-1 tracking-tight">
              {action || "PHYSICAL VIOLENCE"} DETECTED ({Math.round((confidence || 0.88) * 100)}% CONFIDENCE)
            </h2>

            <div className="flex items-center gap-3 mt-1.5 text-xs font-mono text-red-200 flex-wrap">
              {attacker_id && (
                <span>
                  ATTACKER: <strong className="text-red-400 font-bold bg-red-950/80 px-1.5 py-0.5 rounded border border-red-500/40">ID {attacker_id}</strong>
                </span>
              )}
              {victim_id && (
                <span>
                  VICTIM: <strong className="text-emerald-400 font-bold bg-emerald-950/80 px-1.5 py-0.5 rounded border border-emerald-500/40">ID {victim_id}</strong>
                </span>
              )}
              {reason && (
                <span className="text-red-300/80 text-[11px]">
                  • {reason}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right Silence / Action Button */}
        <div className="flex items-center gap-2 shrink-0">
          {!acknowledged ? (
            <button
              onClick={handleSilence}
              className="px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs shadow-lg transition-all flex items-center gap-2 border border-red-400/50 hover:scale-105 active:scale-95"
            >
              <VolumeX className="w-4 h-4" />
              <span>Silence Alarm Audio</span>
            </button>
          ) : (
            <span className="px-3 py-1.5 rounded-lg bg-red-950/90 border border-red-500/30 text-xs font-mono text-red-300 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Audio Silenced</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default BullyingAlarmBanner;
