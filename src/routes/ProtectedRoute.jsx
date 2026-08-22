import React from "react";
import { Navigate } from "react-router-dom";
import { ShieldAlert, RefreshCw } from "lucide-react";
import { useAuth } from "../context/AuthContext";

// Loading Screen per Specification #13
export const AuthLoadingScreen = () => {
  return (
    <div className="min-h-screen bg-[#0B1120] flex flex-col items-center justify-center p-4 text-[#F8FAFC]">
      <div className="text-center space-y-4 max-w-sm">
        <div className="inline-flex p-4 rounded-2xl bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30 glow-cyan animate-pulse">
          <ShieldAlert className="w-10 h-10" />
        </div>
        <div>
          <h1 className="text-xl font-extrabold tracking-tight text-[#F8FAFC]">
            SAFECAM <span className="text-[#00D4FF]">AI</span>
          </h1>
          <p className="text-xs font-mono text-[#94A3B8] mt-1">
            Checking authentication...
          </p>
        </div>
        <div className="pt-2">
          <RefreshCw className="w-5 h-5 text-[#00D4FF] animate-spin mx-auto opacity-80" />
        </div>
      </div>
    </div>
  );
};

// Protected Dashboard Guard
export const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <AuthLoadingScreen />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Public Route Guard (Redirects authenticated users away from /login & /register)
export const PublicOnlyRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <AuthLoadingScreen />;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return children;
};

export default ProtectedRoute;
