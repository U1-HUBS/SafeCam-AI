import React from "react";
import { ShieldAlert } from "lucide-react";

export const LoadingSpinner = () => (
  <div className="w-10 h-10 rounded-full border-2 border-t-[#00D4FF] border-r-[#00D4FF]/40 border-b-transparent border-l-transparent animate-spin" />
);

export const LoadingScreen = ({ message = "Loading SAFECAM AI Core..." }) => (
  <div className="min-h-screen bg-[#0B1120] flex flex-col items-center justify-center p-4 text-[#F8FAFC]">
    <div className="text-center space-y-4 max-w-sm">
      <div className="inline-flex p-4 rounded-2xl bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30 glow-cyan">
        <ShieldAlert className="w-10 h-10" />
      </div>
      <div>
        <h1 className="text-xl font-black tracking-tight text-[#F8FAFC]">
          SAFECAM <span className="text-[#00D4FF]">AI</span>
        </h1>
        <p className="text-xs font-mono text-[#94A3B8] mt-1">{message}</p>
      </div>
      <div className="pt-2 flex justify-center">
        <LoadingSpinner />
      </div>
    </div>
  </div>
);

export default LoadingScreen;
