import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, Bell, Shield, User, ExternalLink, CheckCircle } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useSocket } from "../../context/SocketContext";
import audioAlertService from "../../services/audioAlertService";

export const Topbar = ({ onOpenMobile }) => {
  const location = useLocation();
  const { user } = useAuth();
  const { activeAlerts, resolveAlert } = useSocket();
  const [showNotifications, setShowNotifications] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(false);

  const activeUnresolvedAlerts = activeAlerts.filter((a) => a.status === "active");

  const getPageTitle = (path) => {
    switch (path) {
      case "/":
        return "Dashboard Overview";
      case "/monitoring":
        return "Live Surveillance Monitoring";
      case "/alerts":
        return "Critical Alert Center";
      case "/logs":
        return "System Audit Logs & Events";
      case "/profile":
        return "User Profile & Security";
      default:
        return "SAFECAM AI";
    }
  };

  return (
    <header className="sticky top-0 z-30 h-14 sm:h-16 glass-panel border-b border-white/10 px-4 sm:px-5 flex items-center justify-between">
      {/* Left Title & Mobile Menu Switch */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        <button
          onClick={onOpenMobile}
          className="p-1.5 rounded-lg text-[#94A3B8] hover:text-white hover:bg-white/10 lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <h2 className="text-sm sm:text-base font-bold text-[#F8FAFC] tracking-tight">
            {getPageTitle(location.pathname)}
          </h2>
        </div>
      </div>

      {/* Right Controls: System Status, Notifications, User */}
      <div className="flex items-center gap-3 sm:gap-5">
        {/* System Online Status Indicator */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-[#00D4FF]/10 border border-[#00D4FF]/30 text-xs font-mono text-[#00D4FF]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00D4FF] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00D4FF]"></span>
          </span>
          <span>SYSTEM ONLINE</span>
        </div>

        {/* Notifications Dropdown Container */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 rounded-lg text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/5 transition-colors focus:outline-none"
          >
            <Bell className="w-5 h-5" />
            {activeUnresolvedAlerts.length > 0 && (
              <span className="absolute top-1 right-1 w-2.5 h-2.5 rounded-full bg-[#EF4444] ring-2 ring-[#0B1120] animate-pulse" />
            )}
          </button>

          {/* Notifications Popover */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 glass-panel border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden">
              <div className="p-3.5 border-b border-white/10 bg-white/5 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-[#F8FAFC]">
                  Active Alerts ({activeUnresolvedAlerts.length})
                </span>
                <Link
                  to="/alerts"
                  onClick={() => setShowNotifications(false)}
                  className="text-xs text-[#00D4FF] hover:underline flex items-center gap-1"
                >
                  View All <ExternalLink className="w-3 h-3" />
                </Link>
              </div>

              <div className="max-h-72 overflow-y-auto divide-y divide-white/5">
                {activeUnresolvedAlerts.length === 0 ? (
                  <div className="p-6 text-center text-xs text-[#94A3B8]">
                    <CheckCircle className="w-6 h-6 text-[#00D4FF] mx-auto mb-2 opacity-80" />
                    No active threat alerts detected.
                  </div>
                ) : (
                  activeUnresolvedAlerts.map((alert) => (
                    <div key={alert.id} className="p-3.5 hover:bg-white/5 transition-colors">
                      <div className="flex items-start justify-between">
                        <span className="text-xs font-bold text-[#EF4444] uppercase font-mono">
                          {alert.type.replace("_", " ")}
                        </span>
                        <span className="text-[10px] text-[#94A3B8]">{alert.timeAgo}</span>
                      </div>
                      <p className="text-xs text-[#F8FAFC] mt-1">
                        {alert.cameraName} — Action: <span className="font-semibold text-white">{alert.action}</span>
                      </p>
                      <div className="mt-2 flex items-center justify-between text-[10px] font-mono">
                        <span className="text-[#94A3B8]">Confidence: {(alert.confidence * 100).toFixed(0)}%</span>
                        <button
                          onClick={() => resolveAlert(alert.id)}
                          className="text-[#00D4FF] hover:underline font-semibold"
                        >
                          Resolve
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Profile Quick Access */}
        <Link
          to="/profile"
          className="flex items-center gap-2.5 p-1 rounded-xl hover:bg-white/5 transition-colors group"
        >
          <img
            src={user?.photoURL || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=150&auto=format&fit=crop"}
            alt="User avatar"
            className="w-8 h-8 rounded-lg object-cover ring-1 ring-[#00D4FF]/40 group-hover:ring-[#00D4FF]"
          />
          <div className="hidden md:block text-left">
            <div className="text-xs font-semibold text-[#F8FAFC] leading-none">
              {user?.displayName || "User"}
            </div>
            <div className="text-[10px] font-mono text-[#00D4FF] mt-1 leading-none">
              {user?.email || "USER"}
            </div>
          </div>
        </Link>
      </div>
    </header>
  );
};

export default Topbar;
