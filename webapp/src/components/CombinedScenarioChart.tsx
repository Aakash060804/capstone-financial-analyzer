"use client";
import { buildCombinedSeries } from "@/lib/dataUtils";
import { FinancialData } from "@/types/financial";
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine, Area,
} from "recharts";

interface Props {
  data: FinancialData;
  historicMetric: string;
  forecastMetric: string;
  title: string;
  unit?: string;
  yFmt?: (v: number) => string;
}

const CustomTooltip = ({ active, payload, label, unit }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border p-3 text-xs" style={{ background: "#0c1529", borderColor: "#1a2d4f", minWidth: 160 }}>
      <p className="font-semibold mb-2" style={{ color: "#e2e8f0" }}>{label}</p>
      {payload.map((p: any) => p.value != null && (
        <div key={p.name} className="flex justify-between gap-4 mb-0.5">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="font-semibold num" style={{ color: "#e2e8f0" }}>
            ₹{Number(p.value).toLocaleString("en-IN", { maximumFractionDigits: 0 })} {unit}
          </span>
        </div>
      ))}
    </div>
  );
};

export default function CombinedScenarioChart({ data, historicMetric, forecastMetric, title, unit = "Cr", yFmt }: Props) {
  const series = buildCombinedSeries(data, historicMetric, forecastMetric);
  const lastHistYear = data.statements.income_statement.headers
    .filter((h) => h !== "metric" && h !== "TTM")
    .sort()
    .slice(-1)[0];

  const defaultFmt = (v: number) =>
    v >= 100000 ? `₹${(v / 100000).toFixed(1)}L` : `₹${(v / 1000).toFixed(0)}K`;
  const tickFmt = yFmt ?? defaultFmt;

  return (
    <div>
      <p className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>{title}</p>
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="bullBearFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#3b7cf4" stopOpacity={0.12} />
              <stop offset="95%" stopColor="#3b7cf4" stopOpacity={0.01} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a2d4f" vertical={false} />
          <XAxis
            dataKey="year"
            tick={{ fill: "#4a6080", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#1a2d4f" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#4a6080", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={tickFmt}
            width={60}
          />
          <Tooltip content={<CustomTooltip unit={unit} />} />
          <Legend
            wrapperStyle={{ fontSize: 12, paddingTop: 16 }}
            formatter={(val) => <span style={{ color: "#94a3b8" }}>{val}</span>}
          />
          {lastHistYear && (
            <ReferenceLine x={lastHistYear} stroke="#1a2d4f" strokeDasharray="4 4" label={{ value: "Forecast →", position: "insideTopRight", fill: "#4a6080", fontSize: 10 }} />
          )}
          {/* Bear–Bull uncertainty band */}
          <Area dataKey="bull" fill="url(#bullBearFill)" stroke="none" legendType="none" connectNulls />
          {/* Historical — solid bright blue */}
          <Line dataKey="historical" name="Historical" stroke="#3b7cf4" strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: "#3b7cf4" }} connectNulls />
          {/* Base — dashed blue */}
          <Line dataKey="base" name="Base" stroke="#3b7cf4" strokeWidth={2} strokeDasharray="6 3" dot={false} activeDot={{ r: 4 }} connectNulls />
          {/* Bull — dashed green */}
          <Line dataKey="bull" name="Bull" stroke="#00d68f" strokeWidth={2} strokeDasharray="6 3" dot={false} activeDot={{ r: 4 }} connectNulls />
          {/* Bear — dashed red */}
          <Line dataKey="bear" name="Bear" stroke="#ff3d57" strokeWidth={2} strokeDasharray="6 3" dot={false} activeDot={{ r: 4 }} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
