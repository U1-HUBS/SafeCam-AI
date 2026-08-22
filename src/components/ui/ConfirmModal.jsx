import React from "react";
import { AlertTriangle, Trash2 } from "lucide-react";
import Modal from "./Modal";
import Button from "./Button";

export const ConfirmModal = ({
  isOpen,
  title = "Delete this alert?",
  message = "Are you sure you want to permanently delete this alert?",
  confirmLabel = "Delete Alert",
  cancelLabel = "Cancel",
  onConfirm,
  onClose,
  isProcessing = false
}) => {
  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} maxWidth="max-w-md">
      <div className="space-y-4 text-sm">
        <div className="flex items-start gap-3 p-3.5 rounded-xl bg-red-950/40 border border-red-500/30 text-red-200">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-slate-300 leading-relaxed font-sans">{message}</p>
        </div>

        <div className="pt-2 flex items-center justify-end gap-2.5 font-sans">
          <Button variant="outline" size="md" onClick={onClose} disabled={isProcessing}>
            {cancelLabel}
          </Button>
          <Button
            variant="danger"
            size="md"
            icon={Trash2}
            onClick={onConfirm}
            disabled={isProcessing}
            className="bg-red-600 hover:bg-red-500 text-white font-bold"
          >
            {isProcessing ? "Deleting..." : confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default ConfirmModal;
