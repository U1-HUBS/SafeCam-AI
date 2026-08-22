import React from "react";
import { AlertTriangle, Trash2 } from "lucide-react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import { useCameraContext } from "../../context/CameraContext";

export const RemoveCameraModal = ({ camera, isOpen, onClose }) => {
  const { removeCamera } = useCameraContext();

  if (!camera) return null;

  const handleRemove = () => {
    removeCamera(camera.id);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`REMOVE ${camera.name.toUpperCase()}?`}
      subtitle="Confirm camera deletion from live monitoring dashboard"
    >
      <div className="space-y-4 text-xs font-mono">
        <div className="p-4 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/30 space-y-2">
          <div className="flex items-center gap-2 text-[#EF4444] font-bold text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span>Confirm Deletion</span>
          </div>
          <p className="text-slate-300 font-sans text-xs leading-relaxed">
            Are you sure you want to remove <strong className="text-white">{camera.name}</strong> ({camera.location}) from your monitoring workspace?
          </p>
        </div>

        <div className="pt-2 flex items-center justify-end gap-2.5 font-sans">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" icon={Trash2} onClick={handleRemove}>
            Remove Camera
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default RemoveCameraModal;
