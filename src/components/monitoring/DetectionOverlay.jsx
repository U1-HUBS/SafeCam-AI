import React from "react";

/**
 * DetectionOverlay Component
 * Renders real-time AI bounding boxes received from backend / Socket.IO data.
 * STRICT ROLE COLORING:
 * - CONFIRMED ATTACKER -> RED (#EF4444)
 * - VICTIM / NORMAL / BYSTANDER -> GREEN (#10B981)
 */
export const DetectionOverlay = ({ detections = [], containerWidth = 800, containerHeight = 450 }) => {
  if (!detections || detections.length === 0) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-20 overflow-hidden">
      {detections.map((det, index) => {
        const { box, role, action, action_label, confidence, personId, track_id } = det;
        if (!box) return null;

        const pId = personId || track_id || index;
        const isAttacker = role === "attacker";
        const isVictim = role === "victim";

        // Bounding Box Colors: RED ONLY for Confirmed Attacker, GREEN for Victim / Normal / Bystander
        const borderColor = isAttacker
          ? "border-[#EF4444] text-[#EF4444]"
          : "border-[#10B981] text-[#10B981]";

        const bgBadgeColor = isAttacker
          ? "bg-[#EF4444] text-white font-bold"
          : isVictim
          ? "bg-[#10B981] text-slate-950 font-bold"
          : "bg-[#10B981]/90 text-slate-950 font-bold";

        const glowEffect = isAttacker
          ? "glow-red"
          : "glow-green";

        let labelText = `ID: ${pId}`;
        if (action === "MUTUAL_FIGHT" || action_label === "MUTUAL FIGHT") {
          labelText = "⚠️ MUTUAL FIGHT";
        } else if (isAttacker) {
          const actName = (action_label || action || "BULLY")
            .replace("BULLY — ", "")
            .replace("ATTACKER — ", "")
            .replace("_ATTACKER", "")
            .replace("_", " ");
          labelText = `🔴 BULLY — ${actName.toUpperCase()}`;
        } else if (isVictim) {
          labelText = "🟢 VICTIM";
        } else if (action_label === "UNKNOWN") {
          labelText = `ID: ${pId} • UNKNOWN`;
        }

        return (
          <div
            key={`box-${pId}`}
            className={`absolute border-2 ${borderColor} ${glowEffect} transition-all duration-150 ease-out`}
            style={{
              left: `${(box.x / 800) * 100}%`,
              top: `${(box.y / 450) * 100}%`,
              width: `${(box.width / 800) * 100}%`,
              height: `${(box.height / 450) * 100}%`
            }}
          >
            {/* Corner Accents */}
            <span className="absolute -top-1 -left-1 w-2 h-2 border-t-2 border-l-2 border-white" />
            <span className="absolute -top-1 -right-1 w-2 h-2 border-t-2 border-r-2 border-white" />
            <span className="absolute -bottom-1 -left-1 w-2 h-2 border-b-2 border-l-2 border-white" />
            <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b-2 border-r-2 border-white" />

            {/* Target Reticle Crosshair */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 opacity-30 flex items-center justify-center">
              <div className="w-full h-0.5 bg-current" />
              <div className="h-full w-0.5 bg-current absolute" />
            </div>

            {/* Bounding Box Label Badge */}
            <div
              className={`absolute -top-7 left-0 px-2 py-0.5 rounded text-[11px] font-mono tracking-wider uppercase flex items-center gap-1.5 whitespace-nowrap shadow-lg ${bgBadgeColor}`}
            >
              <span>{labelText}</span>
              {confidence && <span>({(confidence * 100).toFixed(0)}%)</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default DetectionOverlay;
