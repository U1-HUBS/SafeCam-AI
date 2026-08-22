import React, { useEffect } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

export const Toast = ({ message, type = "success", onClose, duration = 4000 }) => {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => {
      if (onClose) onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!message) return null;

  const isSuccess = type === "success";
  const isError = type === "error";

  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-900/95 border border-white/10 shadow-2xl backdrop-blur-md text-white font-sans text-sm font-semibold animate-in slide-in-from-bottom-5 duration-300">
      {isSuccess && <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
      {isError && <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />}
      {!isSuccess && !isError && <Info className="w-5 h-5 text-[#00D4FF] shrink-0" />}

      <span>{message}</span>

      <button
        onClick={onClose}
        className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors ml-2"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export default Toast;
