import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export const DashboardLayout = () => {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#0B1120] text-[#F8FAFC] flex">
      {/* Persistent Left Sidebar */}
      <Sidebar isMobileOpen={isMobileOpen} setIsMobileOpen={setIsMobileOpen} />

      {/* Main Content Area Shifted for Sidebar */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-64 transition-all duration-300">
        <Topbar onOpenMobile={() => setIsMobileOpen(true)} />

        <main className="flex-1 p-3.5 sm:p-5 lg:p-6 w-full max-w-none space-y-4 sm:space-y-5">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
