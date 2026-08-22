import React, { useState } from "react";
import { NavLink as RouterNavLink, useNavigate } from "react-router-dom";
import { 
  ShieldAlert, 
  LayoutDashboard, 
  Video, 
  Bell, 
  FileText, 
  LogOut,
  Activity,
  Sliders
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useSocket } from "../../context/SocketContext";
import LogoutModal from "./LogoutModal";

export const Sidebar = ({ isMobileOpen, setIsMobileOpen }) => {
  const { user, logout } = useAuth();
  const { activeAlerts } = useSocket();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const criticalAlertCount = activeAlerts.filter((a) => a && a.status === "active").length;

  const handleConfirmLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      setShowLogoutModal(false);
      navigate("/login");
    } catch (e) {
      console.error("Logout failed:", e);
    } finally {
      setIsLoggingOut(false);
    }
  };

  const navItems = [
    { name: "Overview Dashboard", path: "/", icon: LayoutDashboard },
    { name: "Live Fight Detection", path: "/monitoring", icon: Video },
    { 
      name: "Alerts", 
      path: "/alerts", 
      icon: Bell, 
      badge: criticalAlertCount > 0 ? criticalAlertCount : null 
    },
    { name: "Event Logs", path: "/logs", icon: FileText },
    { name: "Analytics", path: "/analytics", icon: Activity },
    { name: "AI Config", path: "/settings", icon: Sliders }
  ];

  const username = user?.displayName || "Operator";
  const userInitial = username.charAt(0).toUpperCase();

  return (
    <>
      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          onClick={() => setIsMobileOpen(false)}
          className="fixed inset-0 bg-[#0B1120]/80 backdrop-blur-sm z-30 lg:hidden"
        />
      )}

      {/* Sidebar Container: 240-256px wide on desktop */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 bg-[#0B101D] border-r border-white/10 flex flex-col justify-between transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand Header */}
        <div className="p-5 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30 shadow-md">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-extrabold tracking-tight text-[17px] text-[#F8FAFC] flex items-center gap-1.5 font-sans">
                SafeCam <span className="text-[#00D4FF]">AI</span>
              </h1>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <div className="px-3.5 py-5 flex-1 space-y-2 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <RouterNavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                onClick={() => setIsMobileOpen(false)}
                className={({ isActive }) =>
                  `group flex items-center justify-between px-3.5 py-3 rounded-xl font-bold text-[14px] transition-all duration-200 cursor-pointer ${
                    isActive
                      ? "bg-[#00D4FF]/15 border-l-4 border-[#00D4FF] text-[#F8FAFC] shadow-md"
                      : "text-[#94A3B8] hover:text-white hover:bg-white/10"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="flex items-center gap-3.5">
                      <Icon className={`w-5 h-5 shrink-0 transition-transform group-hover:scale-110 ${isActive ? "text-[#00D4FF]" : "text-[#94A3B8]"}`} />
                      <span>{item.name}</span>
                    </div>
                    {item.badge ? (
                      <span className="px-2.5 py-0.5 text-xs font-mono font-extrabold rounded-full bg-[#EF4444] text-white shadow-sm">
                        {item.badge}
                      </span>
                    ) : null}
                  </>
                )}
              </RouterNavLink>
            );
          })}
        </div>

        {/* User Account Info & Sign Out Footer */}
        <div className="p-4 border-t border-white/10 bg-[#070C16] space-y-3">
          <div className="p-3 rounded-xl bg-[#0F1626] border border-white/10 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#00D4FF]/20 text-[#00D4FF] flex items-center justify-center font-extrabold text-sm shrink-0 border border-[#00D4FF]/30">
              {userInitial}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-sm text-white truncate font-sans">{username}</span>
                <span className="px-1.5 py-0.2 rounded bg-[#00D4FF]/20 text-[#00D4FF] text-[10px] font-mono font-bold">USER</span>
              </div>
              <p className="text-xs text-[#94A3B8] font-mono truncate mt-0.5">Account & Security</p>
            </div>
          </div>

          <button
            onClick={() => setShowLogoutModal(true)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-xs font-extrabold text-red-400 hover:text-red-300 hover:bg-red-950/40 border border-red-500/20 transition-all cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>

        <LogoutModal
          isOpen={showLogoutModal}
          onClose={() => setShowLogoutModal(false)}
          onConfirm={handleConfirmLogout}
          isLoading={isLoggingOut}
        />
      </aside>
    </>
  );
};

export default Sidebar;
