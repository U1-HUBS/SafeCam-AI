import React from "react";
import Card from "./Card";

export const StatCard = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  isAlert = false
}) => {
  const borderStyle = isAlert
    ? "border-[#EF4444]/50 bg-[#EF4444]/10 shadow-red-950/20"
    : "border-white/10 bg-[#0B1120]/90";
  const iconStyle = isAlert
    ? "bg-[#EF4444]/20 text-[#EF4444] border-[#EF4444]/40"
    : "bg-[#00D4FF]/10 text-[#00D4FF] border-[#00D4FF]/30";
  const statusDot = isAlert ? "bg-[#EF4444] animate-pulse" : "bg-[#00D4FF]";

  return (
    <Card className={`relative overflow-hidden p-5 transition-all duration-300 ${borderStyle}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${statusDot}`} />
            <p className="text-sm font-bold tracking-wide text-[#94A3B8] font-sans">
              {title}
            </p>
          </div>
          <h3 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#F8FAFC] font-sans mt-1">
            {value}
          </h3>
        </div>

        {Icon && (
          <div className={`p-3 rounded-xl border ${iconStyle} shrink-0`}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-3 pt-2.5 border-t border-white/10 flex items-center justify-between text-xs font-sans text-[#94A3B8]">
          {subtitle && <span>{subtitle}</span>}
          {trend && <span className="font-bold text-[#00D4FF]">{trend}</span>}
        </div>
      )}
    </Card>
  );
};

export default StatCard;
