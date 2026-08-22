import React, { useState, useEffect } from "react";
import { ShieldAlert, CheckCircle2 } from "lucide-react";
import { useSocket } from "../context/SocketContext";
import AlertCard from "../components/alerts/AlertCard";
import AlertModal from "../components/alerts/AlertModal";
import ConfirmModal from "../components/ui/ConfirmModal";
import Toast from "../components/ui/Toast";

export const Alerts = () => {
  const { activeAlerts, resolveAlert, deleteAlert: deleteSocketAlert } = useSocket();
  const [filterTab, setFilterTab] = useState("all");
  const [selectedAlertForModal, setSelectedAlertForModal] = useState(null);
  const [backendIncidents, setBackendIncidents] = useState([]);
  
  // Deletion Confirmation & Toast States
  const [alertToDelete, setAlertToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [toastMessage, setToastMessage] = useState("");

  // Helper to retrieve deleted IDs from localStorage
  const getDeletedAlertIds = () => {
    try {
      const stored = localStorage.getItem("safecam_deleted_alert_ids");
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      return [];
    }
  };

  const addDeletedAlertId = (alertId) => {
    try {
      const current = getDeletedAlertIds();
      if (!current.includes(alertId)) {
        const updated = [...current, alertId];
        localStorage.setItem("safecam_deleted_alert_ids", JSON.stringify(updated));
      }
    } catch (e) {}
  };

  // Fetch real single-source-of-truth backend incident records
  const fetchIncidents = () => {
    fetch("http://localhost:8000/api/alarms")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.incidents)) {
          setBackendIncidents(data.incidents);
        }
      })
      .catch((err) => {
        console.warn("[ALERTS PAGE] REST fetch warning:", err);
      });
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const deletedIds = getDeletedAlertIds();
  const safeActiveAlerts = (Array.isArray(activeAlerts) ? activeAlerts : []).filter(
    (a) => a && !deletedIds.includes(a.id)
  );
  const safeBackendIncidents = (Array.isArray(backendIncidents) ? backendIncidents : []).filter(
    (inc) => inc && !deletedIds.includes(inc.incident_id)
  );

  // Map real backend incidents to alert UI objects
  const realMappedAlerts = safeBackendIncidents
    .map((inc) => {
      if (!inc) return null;
      let formattedTime = "Just now";
      if (inc.started_at) {
        try {
          const dt = new Date(inc.started_at);
          if (!isNaN(dt.getTime())) {
            formattedTime = dt.toLocaleTimeString();
          }
        } catch (e) {}
      }

      return {
        id: inc.incident_id || "INC-000",
        cameraName: `Camera ${inc.camera_id || "01"}`,
        type: inc.event_type || "BULLYING_CONFIRMED",
        severity: "critical",
        status: "active",
        timeAgo: formattedTime,
        confidence: inc.confidence != null ? inc.confidence : 0.88,
        action: inc.action || "PHYSICAL VIOLENCE",
        attackerId: inc.attacker_id,
        victimId: inc.victim_id,
        clipPath: inc.clip_path,
        snapshotPath: inc.snapshot_path,
        reason: inc.reason || "Confirmed Violence"
      };
    })
    .filter(Boolean);

  const allAlertsList = realMappedAlerts.length > 0 ? realMappedAlerts : safeActiveAlerts;

  const filteredAlerts = allAlertsList.filter((alert) => {
    if (!alert) return false;
    if (filterTab === "critical") return alert.severity === "critical" && alert.status === "active";
    if (filterTab === "warning") return alert.severity === "warning" && alert.status === "active";
    if (filterTab === "resolved") return alert.status === "resolved";
    return true;
  });

  const criticalCount = allAlertsList.filter((a) => a && a.severity === "critical" && a.status === "active").length;
  const warningCount = allAlertsList.filter((a) => a && a.severity === "warning" && a.status === "active").length;
  const resolvedCount = allAlertsList.filter((a) => a && a.status === "resolved").length;

  // Handle Permanent Incident Deletion
  const handleDeleteClick = (alertId) => {
    setAlertToDelete(alertId);
  };

  const handleConfirmDelete = async () => {
    if (!alertToDelete) return;
    setIsDeleting(true);

    const idToRemove = alertToDelete;

    // 1. Add to localStorage persistence filter
    addDeletedAlertId(idToRemove);

    // 2. Call Python WebRTC REST delete endpoint
    try {
      await fetch("http://localhost:8000/api/alarms/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incident_id: idToRemove })
      });
    } catch (e) {
      console.warn("[ALERTS PAGE] REST delete error:", e);
    }

    // 3. Update Socket Context & Local state
    if (deleteSocketAlert) deleteSocketAlert(idToRemove);
    setBackendIncidents((prev) => prev.filter((inc) => inc.incident_id !== idToRemove));

    setIsDeleting(false);
    setAlertToDelete(null);
    setToastMessage("Alert deleted successfully.");
  };

  return (
    <div className="space-y-6">
      {/* Header & Title Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#F8FAFC] tracking-tight flex items-center gap-3">
            <ShieldAlert className="w-7 h-7 text-[#EF4444]" />
            CRITICAL ALERTS & INCIDENTS
          </h1>
          <p className="text-sm text-[#94A3B8] mt-1 font-sans">
            Real-time bullying alerts and physical safety incident management
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 p-1.5 bg-[#0B1120] rounded-xl border border-white/10 overflow-x-auto">
          {[
            { id: "all", label: `All (${allAlertsList.length})` },
            { id: "critical", label: `Critical (${criticalCount})` },
            { id: "warning", label: `Warning (${warningCount})` },
            { id: "resolved", label: `Resolved (${resolvedCount})` }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterTab(tab.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold font-mono transition-all whitespace-nowrap cursor-pointer ${
                filterTab === tab.id
                  ? "bg-[#00D4FF] text-[#0B1120] font-bold shadow-md"
                  : "text-[#94A3B8] hover:text-white hover:bg-white/5"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Alerts Grid Display */}
      {filteredAlerts.length === 0 ? (
        <div className="glass-panel p-10 rounded-2xl text-center space-y-3 border border-white/10">
          <CheckCircle2 className="w-12 h-12 text-[#00D4FF] mx-auto opacity-90" />
          <h3 className="text-base font-bold text-[#F8FAFC]">
            {allAlertsList.length === 0 ? "No active alerts." : "No matching alerts."}
          </h3>
          <p className="text-sm text-[#94A3B8] max-w-md mx-auto">
            {allAlertsList.length === 0
              ? "There are currently no security alerts detected by the AI telemetry system."
              : "No threat alerts match your current tab filter selection."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredAlerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onView={(a) => setSelectedAlertForModal(a)}
              onResolve={(id) => resolveAlert(id)}
              onDelete={(id) => handleDeleteClick(id)}
            />
          ))}
        </div>
      )}

      {/* Alert Detail View Modal */}
      <AlertModal
        alert={selectedAlertForModal}
        isOpen={Boolean(selectedAlertForModal)}
        onClose={() => setSelectedAlertForModal(null)}
        onResolve={(id) => resolveAlert(id)}
      />

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={Boolean(alertToDelete)}
        title="Delete this alert?"
        message="Are you sure you want to permanently delete this alert?"
        confirmLabel="Delete Alert"
        cancelLabel="Cancel"
        onConfirm={handleConfirmDelete}
        onClose={() => setAlertToDelete(null)}
        isProcessing={isDeleting}
      />

      {/* Action Toast Notification */}
      <Toast message={toastMessage} onClose={() => setToastMessage("")} />
    </div>
  );
};

export default Alerts;
