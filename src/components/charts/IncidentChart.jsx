import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from "recharts";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass-panel p-3 rounded-lg border border-white/10 text-xs font-mono shadow-xl">
        <p className="text-[#00D4FF] font-bold mb-1">{label}</p>
        <p className="text-[#EF4444]">Incidents: <span className="font-bold text-white">{payload[0].value}</span></p>
        {payload[1] && (
          <p className="text-[#00D4FF]">Warnings: <span className="font-bold text-white">{payload[1].value}</span></p>
        )}
      </div>
    );
  }
  return null;
};

export const IncidentChart = ({ data = [] }) => {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-56 sm:h-60 flex flex-col items-center justify-center border border-dashed border-white/10 rounded-xl text-center p-4 text-[#94A3B8]">
        <p className="text-xs font-mono">NO INCIDENT TREND DATA RECORDED</p>
        <p className="text-[10px] text-[#64748B] mt-1">Real-time incident trends appear when AI telemetry is generated.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-56 sm:h-60">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorIncidents" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorWarnings" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00D4FF" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#00D4FF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="time" stroke="#94A3B8" fontSize={11} tickLine={false} />
          <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="incidents"
            stroke="#EF4444"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorIncidents)"
          />
          <Area
            type="monotone"
            dataKey="warnings"
            stroke="#00D4FF"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorWarnings)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default IncidentChart;
