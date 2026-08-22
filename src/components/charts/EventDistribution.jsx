import React from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend
} from "recharts";

export const EventDistribution = ({ data = [] }) => {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-56 sm:h-60 flex flex-col items-center justify-center border border-dashed border-white/10 rounded-xl text-center p-4 text-[#94A3B8]">
        <p className="text-xs font-mono">NO EVENT DISTRIBUTION RECORDED</p>
        <p className="text-[10px] text-[#64748B] mt-1">Distribution chart updates automatically as real events occur.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-56 sm:h-60 flex items-center justify-center">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            innerRadius={48}
            outerRadius={72}
            paddingAngle={4}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(17, 24, 39, 0.9)",
              borderColor: "rgba(255, 255, 255, 0.1)",
              borderRadius: "8px",
              color: "#F8FAFC",
              fontSize: "12px"
            }}
            formatter={(value) => [`${value}%`, "Share"]}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            wrapperStyle={{ fontSize: "11px", color: "#94A3B8" }}
            formatter={(value) => <span className="text-[#F8FAFC]">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default EventDistribution;
