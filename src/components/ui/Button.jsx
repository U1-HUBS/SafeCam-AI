import React from "react";
import { Loader2 } from "lucide-react";

export const Button = ({
  children,
  variant = "primary", // 'primary', 'secondary', 'danger', 'outline', 'ghost'
  size = "md", // 'sm', 'md', 'lg'
  isLoading = false,
  isDisabled = false,
  icon: Icon,
  className = "",
  type = "button",
  onClick,
  ...props
}) => {
  const baseStyles = "inline-flex items-center justify-center font-semibold transition-all duration-150 rounded-xl focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed";

  const sizeStyles = {
    sm: "px-3 py-1.5 text-xs gap-1.5",
    md: "px-4 py-2 text-xs sm:text-sm gap-2",
    lg: "px-5 py-2.5 text-sm sm:text-base gap-2.5"
  };

  const variantStyles = {
    primary: "bg-[#00D4FF] text-[#0B1120] hover:bg-[#33E0FF] font-bold shadow-sm active:scale-[0.98]",
    secondary: "bg-white/5 text-[#F8FAFC] border border-white/10 hover:bg-white/10 active:scale-[0.98]",
    danger: "bg-[#EF4444] text-white hover:bg-[#F87171] font-bold shadow-sm active:scale-[0.98]",
    outline: "border border-[#00D4FF]/40 text-[#00D4FF] hover:bg-[#00D4FF]/10 active:scale-[0.98]",
    ghost: "text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/5"
  };

  return (
    <button
      type={type}
      disabled={isDisabled || isLoading}
      onClick={onClick}
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : Icon ? (
        <Icon className="w-4 h-4 shrink-0" />
      ) : null}
      <span>{children}</span>
    </button>
  );
};

export default Button;
