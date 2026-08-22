import React, { useState } from "react";
import { 
  Sliders, 
  Cpu, 
  Eye, 
  Activity, 
  Check, 
  Save, 
  Zap
} from "lucide-react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";

export const AIConfig = () => {
  const [yoloConf, setYoloConf] = useState(0.45);
  const [mediaPipeConf, setMediaPipeConf] = useState(0.45);
  const [proximityPx, setProximityPx] = useState(140);
  const [wristThrust, setWristThrust] = useState(180);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#F8FAFC] tracking-tight flex items-center gap-3">
            <Sliders className="w-7 h-7 text-[#00D4FF]" />
            <span>AI Model & Telemetry Configuration</span>
          </h1>
          <p className="text-sm text-[#94A3B8] mt-1 font-sans">
            Adjust AI person detection sensitivity, pose tracking thresholds, and stream settings
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            size="sm"
            icon={savedSuccess ? Check : Save}
            onClick={handleSave}
            className="text-xs py-2 px-4 font-bold bg-[#00D4FF] text-[#0B1120]"
          >
            {savedSuccess ? "Saved Successfully!" : "Save Configuration"}
          </Button>
        </div>
      </div>

      {/* Main Settings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 1: Person Detection Confidence */}
        <Card className="p-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-3 mb-4">
            <h3 className="text-base font-bold text-[#F8FAFC] flex items-center gap-2">
              <Cpu className="w-5 h-5 text-[#00D4FF]" />
              <span>Person Detection Confidence</span>
            </h3>
            <Badge variant="cyan">yolo11n.pt</Badge>
          </div>

          <div className="space-y-4 font-sans text-sm">
            <div className="space-y-2">
              <p className="text-sm text-[#F8FAFC] font-medium leading-relaxed">
                Minimum confidence required before a person detection is accepted.
              </p>
              
              <div className="flex items-center justify-between text-base font-extrabold py-1">
                <span className="text-[#94A3B8] text-xs font-mono">CONFIDENCE THRESHOLD</span>
                <span className="text-[#00D4FF] text-xl font-mono">{(yoloConf * 100).toFixed(0)}%</span>
              </div>

              <input
                type="range"
                min="0.20"
                max="0.90"
                step="0.05"
                value={yoloConf}
                onChange={(e) => setYoloConf(parseFloat(e.target.value))}
                className="w-full accent-[#00D4FF] bg-white/10 h-2.5 rounded-lg cursor-pointer"
              />
            </div>

            <div className="space-y-1.5 py-3 border-t border-white/10 text-xs font-mono">
              <div className="flex justify-between text-[#F8FAFC]">
                <span>AI Input Dimension:</span>
                <span className="text-[#00D4FF] font-bold">640 × 360 px</span>
              </div>
              <p className="text-xs text-[#94A3B8] font-sans">
                Resizes high-resolution video frames for fast CPU inference.
              </p>
            </div>
          </div>
        </Card>

        {/* Card 2: Landmark Detection Confidence */}
        <Card className="p-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-3 mb-4">
            <h3 className="text-base font-bold text-[#F8FAFC] flex items-center gap-2">
              <Eye className="w-5 h-5 text-[#00D4FF]" />
              <span>Landmark Detection Confidence</span>
            </h3>
            <Badge variant="cyan">MediaPipe Pose</Badge>
          </div>

          <div className="space-y-4 font-sans text-sm">
            <div className="space-y-2">
              <p className="text-sm text-[#F8FAFC] font-medium leading-relaxed">
                Minimum accuracy required for human skeletal joint extraction.
              </p>

              <div className="flex items-center justify-between text-base font-extrabold py-1">
                <span className="text-[#94A3B8] text-xs font-mono">POSE THRESHOLD</span>
                <span className="text-[#00D4FF] text-xl font-mono">{(mediaPipeConf * 100).toFixed(0)}%</span>
              </div>

              <input
                type="range"
                min="0.20"
                max="0.90"
                step="0.05"
                value={mediaPipeConf}
                onChange={(e) => setMediaPipeConf(parseFloat(e.target.value))}
                className="w-full accent-[#00D4FF] bg-white/10 h-2.5 rounded-lg cursor-pointer"
              />
            </div>

            <div className="space-y-1.5 py-3 border-t border-white/10 text-xs font-mono">
              <span className="text-[#F8FAFC] font-bold">Extracted Joint Chains:</span>
              <p className="text-xs text-[#00D4FF] font-mono mt-1">
                ✓ Left/Right Arms (Wrist & Elbow Vectors)<br />
                ✓ Left/Right Legs (Knee & Ankle Vectors)
              </p>
            </div>
          </div>
        </Card>

        {/* Card 3: Proximity & Velocity Thresholds */}
        <Card className="p-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-3 mb-4">
            <h3 className="text-base font-bold text-[#F8FAFC] flex items-center gap-2">
              <Zap className="w-5 h-5 text-[#00D4FF]" />
              <span>Proximity & Wrist Velocity Rules</span>
            </h3>
            <Badge variant="warning">Rule Engine</Badge>
          </div>

          <div className="space-y-5 font-sans text-sm">
            <div className="space-y-2">
              <p className="text-sm text-[#F8FAFC] font-medium leading-relaxed">
                Distance between subjects before an interaction is flagged as close contact.
              </p>

              <div className="flex items-center justify-between py-1">
                <span className="text-[#94A3B8] text-xs font-mono">PROXIMITY DISTANCE</span>
                <span className="text-[#00D4FF] text-xl font-mono font-extrabold">{proximityPx} px</span>
              </div>

              <input
                type="range"
                min="80"
                max="250"
                step="10"
                value={proximityPx}
                onChange={(e) => setProximityPx(parseInt(e.target.value))}
                className="w-full accent-[#00D4FF] bg-white/10 h-2.5 rounded-lg cursor-pointer"
              />
            </div>

            <div className="space-y-2 pt-3 border-t border-white/10">
              <p className="text-sm text-[#F8FAFC] font-medium leading-relaxed">
                Minimum wrist strike velocity to trigger aggressive movement warning.
              </p>

              <div className="flex items-center justify-between py-1">
                <span className="text-[#94A3B8] text-xs font-mono">WRIST VELOCITY</span>
                <span className="text-[#00D4FF] text-xl font-mono font-extrabold">{wristThrust} px/s</span>
              </div>

              <input
                type="range"
                min="100"
                max="300"
                step="10"
                value={wristThrust}
                onChange={(e) => setWristThrust(parseInt(e.target.value))}
                className="w-full accent-[#00D4FF] bg-white/10 h-2.5 rounded-lg cursor-pointer"
              />
            </div>
          </div>
        </Card>

        {/* Card 4: WebRTC & Stream Telemetry */}
        <Card className="p-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-3 mb-4">
            <h3 className="text-base font-bold text-[#F8FAFC] flex items-center gap-2">
              <Activity className="w-5 h-5 text-[#00D4FF]" />
              <span>Stream Settings & AI Inference</span>
            </h3>
            <Badge variant="success">Controlled 1s Delay</Badge>
          </div>

          <div className="space-y-3 font-sans text-sm">
            <div className="flex justify-between py-2 border-b border-white/10 text-[#F8FAFC]">
              <span className="text-[#94A3B8]">WebRTC Stream Resolution:</span>
              <span className="text-[#00D4FF] font-bold font-mono">1920 × 1080 (1080p)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-white/10 text-[#F8FAFC]">
              <span className="text-[#94A3B8]">Video Playback Framerate:</span>
              <span className="text-[#00D4FF] font-bold font-mono">30 FPS</span>
            </div>
            <div className="flex justify-between py-2 border-b border-white/10 text-[#F8FAFC]">
              <span className="text-[#94A3B8]">Target Stream Delay:</span>
              <span className="text-[#00D4FF] font-bold font-mono">1000 ms (700–1200ms)</span>
            </div>
            <div className="flex justify-between py-2 text-[#F8FAFC]">
              <span className="text-[#94A3B8]">AI Worker Inference Target:</span>
              <span className="text-[#00D4FF] font-bold font-mono">~10 FPS (100ms)</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default AIConfig;
