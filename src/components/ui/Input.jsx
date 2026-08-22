import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

export const Input = ({
  label,
  type = "text",
  placeholder,
  value,
  onChange,
  error,
  icon: Icon,
  isPassword = false,
  required = false,
  className = "",
  helperText,
  ...props
}) => {
  const [showPassword, setShowPassword] = useState(false);

  const inputType = isPassword ? (showPassword ? "text" : "password") : type;

  return (
    <div className={`space-y-1.5 ${className}`}>
      {label && (
        <label className="block text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">
          {label} {required && <span className="text-[#EF4444]">*</span>}
        </label>
      )}
      <div className="relative rounded-lg shadow-sm">
        {Icon && (
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#94A3B8]">
            <Icon className="h-4 w-4" />
          </div>
        )}
        <input
          type={inputType}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={`block w-full rounded-lg bg-[#0B1120]/80 border ${
            error
              ? "border-[#EF4444] focus:ring-[#EF4444] focus:border-[#EF4444]"
              : "border-white/10 focus:border-[#00D4FF] focus:ring-1 focus:ring-[#00D4FF]"
          } ${Icon ? "pl-10" : "pl-3.5"} ${
            isPassword ? "pr-10" : "pr-3.5"
          } py-2.5 text-sm text-[#F8FAFC] placeholder-[#94A3B8]/60 transition-all duration-200 focus:outline-none`}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-[#94A3B8] hover:text-[#F8FAFC] transition-colors"
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        )}
      </div>
      {error && <p className="text-xs text-[#EF4444] mt-1 font-medium">{error}</p>}
      {helperText && !error && <p className="text-xs text-[#94A3B8] mt-1">{helperText}</p>}
    </div>
  );
};

export default Input;
