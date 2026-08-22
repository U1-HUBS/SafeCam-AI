import React from "react";

export const Card = ({
  children,
  className = "",
  glow = "none" // 'none', 'cyan', 'red'
}) => {
  const glowStyles = {
    none: "border-white/10",
    cyan: "glow-cyan border-[#00D4FF]/30",
    red: "glow-red border-[#EF4444]/30"
  };

  const selectedGlow = glowStyles[glow] || glowStyles.cyan;

  return (
    <div
      className={`glass-card rounded-xl p-3.5 sm:p-4 border transition-all duration-200 ${selectedGlow} ${className}`}
    >
      {children}
    </div>
  );
};

export default Card;
