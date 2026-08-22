import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from "recharts";

export const DetectionChart = ({ data = [] }) => {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-56 sm:h-60 flex flex-col items-center justify-center border border-dashed border-white/10 rounded-xl text-center p-4 text-[#94A3B8]">
        <p className="text-xs font-mono">NO CAMERA DETECTION ACTIVITY RECORDED</p>
        <p className="text-[10px] text-[#64748B] mt-1">Detection activity bars update as cameras record telemetry.</p>
      </div>
    );
  }

  const keys = Object.keys(data[0] || {}).filter((k) => k !== "hour" && k !== "time");
  const colors = ["#00D4FF", "#EF4444", "#0284C7", "#A855F7", "#F59E0B"];

  return (
    <div className="w-full h-56 sm:h-60">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="hour" stroke="#94A3B8" fontSize={11} tickLine={false} />
          <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#111827",
              borderColor: "rgba(255, 255, 255, 0.1)",
              borderRadius: "8px",
              color: "#F8FAFC",
              fontSize: "12px",
              fontFamily: "monospace"
            }}
          />
          <Legend wrapperStyle={{ fontSize: "11px", color: "#94A3B8", paddingTop: "8px" }} />
          {keys.map((key, idx) => (
            <Bar
              key={key}
              dataKey={key}
              name={key.toUpperCase()}
              fill={colors[idx % colors.length]}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DetectionChart;
