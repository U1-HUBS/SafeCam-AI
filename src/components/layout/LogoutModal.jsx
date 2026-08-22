import React from "react";
import { LogOut, AlertTriangle } from "lucide-react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";

export const LogoutModal = ({ isOpen, onClose, onConfirm, isLoading }) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="LOGOUT CONFIRMATION"
      subtitle="Terminate security surveillance session"
    >
      <div className="space-y-4 font-mono text-xs">
        <div className="p-4 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/30 space-y-2">
          <div className="flex items-center gap-2 text-[#EF4444] font-bold text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span>Confirm Session Termination</span>
          </div>
          <p className="text-slate-300 font-sans text-xs leading-relaxed">
            Are you sure you want to logout of your SAFECAM AI account? You will be redirected to the sign-in screen.
          </p>
        </div>

        <div className="pt-2 flex items-center justify-end gap-2.5 font-sans">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            CANCEL
          </Button>
          <Button
            variant="danger"
            icon={LogOut}
            isLoading={isLoading}
            onClick={onConfirm}
          >
            LOGOUT
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default LogoutModal;
