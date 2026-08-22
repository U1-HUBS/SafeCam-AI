import React, { useState, useEffect } from "react";
import { FileText, Download, RefreshCw, Eye } from "lucide-react";
import { firestoreService } from "../services/firestoreService";
import EventsTable from "../components/logs/EventsTable";
import Modal from "../components/ui/Modal";
import Button from "../components/ui/Button";

export const EventsLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLogModal, setSelectedLogModal] = useState(null);

  useEffect(() => {
    const unsubscribe = firestoreService.subscribeToLogs((liveLogs) => {
      setLogs(liveLogs);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleDeleteLog = (logId) => {
    firestoreService.deleteLogDoc(logId);
    setLogs((prev) => prev.filter((log) => log.id !== logId));
  };

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-[#F8FAFC] tracking-tight flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#00D4FF]" />
            EVENTS & AUDIT LOGS
          </h1>
          <p className="text-xs text-[#94A3B8] mt-0.5">
            Historical database of all physical telemetry events and automated system logs
          </p>
        </div>
      </div>

      {/* Main Audit Table */}
      <EventsTable
        logs={logs}
        onViewDetails={(log) => setSelectedLogModal(log)}
        onDeleteLog={handleDeleteLog}
      />

      {/* Log Detail Modal */}
      {selectedLogModal && (
        <Modal
          isOpen={Boolean(selectedLogModal)}
          onClose={() => setSelectedLogModal(null)}
          title={`AUDIT LOG: ${selectedLogModal.id}`}
          subtitle={`${selectedLogModal.date} at ${selectedLogModal.time}`}
        >
          <div className="space-y-4 text-xs font-mono">
            <div className="p-3.5 rounded-xl bg-white/5 border border-white/10 space-y-2">
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">Camera Source:</span>
                <span className="text-[#00D4FF] font-bold">{selectedLogModal.camera}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">Zone Location:</span>
                <span className="text-white">{selectedLogModal.location}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">Classified Event:</span>
                <span className="text-[#EF4444] font-bold">{selectedLogModal.event}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">Detected Action:</span>
                <span className="text-white">{selectedLogModal.action}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">AI Confidence Score:</span>
                <span className="text-[#00D4FF] font-bold">{selectedLogModal.confidence}</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#0B1120] border border-white/10">
              <h4 className="text-xs font-bold text-[#F8FAFC] uppercase mb-1">Telemetry Notes:</h4>
              <p className="text-[#94A3B8] font-sans leading-relaxed">{selectedLogModal.details}</p>
            </div>

            <div className="pt-2 flex justify-end">
              <Button variant="outline" onClick={() => setSelectedLogModal(null)}>
                Close Record
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default EventsLogs;
