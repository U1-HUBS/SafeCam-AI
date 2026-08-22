import React from "react";

export const Badge = ({
  children,
  variant = "cyan", // 'cyan', 'danger', 'neutral', 'success', 'info'
  pulse = false,
  className = ""
}) => {
  const baseStyles = "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold tracking-wide uppercase transition-colors";

  const variantStyles = {
    cyan: "bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30",
    success: "bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30",
    info: "bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30",
    danger: "bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/30",
    neutral: "bg-white/5 text-[#94A3B8] border border-white/10"
  };

  const dotColor = {
    cyan: "bg-[#00D4FF]",
    success: "bg-[#00D4FF]",
    info: "bg-[#00D4FF]",
    danger: "bg-[#EF4444]",
    neutral: "bg-slate-400"
  };

  const currentVariant = variantStyles[variant] || variantStyles.cyan;
  const currentDot = dotColor[variant] || dotColor.cyan;

  return (
    <span className={`${baseStyles} ${currentVariant} ${className}`}>
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${currentDot} opacity-75`} />
          <span className={`relative inline-flex rounded-full h-2 w-2 ${currentDot}`} />
        </span>
      )}
      {children}
    </span>
  );
};

export default Badge;
