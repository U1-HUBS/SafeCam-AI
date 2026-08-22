import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { SocketProvider } from "./context/SocketContext";
import { CameraProvider } from "./context/CameraContext";
import { ProtectedRoute, PublicOnlyRoute } from "./routes/ProtectedRoute";
import DashboardLayout from "./components/layout/DashboardLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import Dashboard from "./pages/Dashboard";
import LiveMonitoring from "./pages/LiveMonitoring";
import Alerts from "./pages/Alerts";
import EventsLogs from "./pages/EventsLogs";
import Profile from "./pages/Profile";
import Analytics from "./pages/Analytics";
import AIConfig from "./pages/AIConfig";

import ErrorBoundary from "./components/ui/ErrorBoundary";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SocketProvider>
          <CameraProvider>
            <Routes>
              {/* Public Authentication Routes (Guarded for Unauthenticated Users) */}
              <Route
                path="/login"
                element={
                  <PublicOnlyRoute>
                    <Login />
                  </PublicOnlyRoute>
                }
              />
              <Route
                path="/register"
                element={
                  <PublicOnlyRoute>
                    <Register />
                  </PublicOnlyRoute>
                }
              />
              <Route
                path="/forgot-password"
                element={
                  <PublicOnlyRoute>
                    <ForgotPassword />
                  </PublicOnlyRoute>
                }
              />

              {/* Protected Main Application Shell */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<ErrorBoundary title="DASHBOARD COMPONENT ERROR"><Dashboard /></ErrorBoundary>} />
                <Route path="dashboard" element={<Navigate to="/" replace />} />
                <Route path="monitoring" element={<ErrorBoundary title="LIVE MONITORING COMPONENT ERROR"><LiveMonitoring /></ErrorBoundary>} />
                <Route path="monitoring/:cameraId" element={<ErrorBoundary title="LIVE MONITORING COMPONENT ERROR"><LiveMonitoring /></ErrorBoundary>} />
                <Route path="live-monitoring" element={<Navigate to="/monitoring" replace />} />
                <Route path="live-monitoring/:cameraId" element={<LiveMonitoring />} />
                <Route path="alerts" element={<ErrorBoundary title="LIVE ALERT COMPONENT ERROR"><Alerts /></ErrorBoundary>} />
                <Route path="live-alert" element={<ErrorBoundary title="LIVE ALERT COMPONENT ERROR"><Alerts /></ErrorBoundary>} />
                <Route path="live-alerts" element={<Navigate to="/alerts" replace />} />
                <Route path="logs" element={<ErrorBoundary title="EVENT LOGS COMPONENT ERROR"><EventsLogs /></ErrorBoundary>} />
                <Route path="events" element={<Navigate to="/logs" replace />} />
                <Route path="analytics" element={<ErrorBoundary font-mono title="ANALYTICS COMPONENT ERROR"><Analytics /></ErrorBoundary>} />
                <Route path="ai-config" element={<ErrorBoundary title="AI CONFIG COMPONENT ERROR"><AIConfig /></ErrorBoundary>} />
                <Route path="settings" element={<AIConfig />} />
                <Route path="profile" element={<ErrorBoundary title="PROFILE COMPONENT ERROR"><Profile /></ErrorBoundary>} />
              </Route>

              {/* Catch-all redirect */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </CameraProvider>
        </SocketProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
