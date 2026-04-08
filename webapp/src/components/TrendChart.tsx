"use client";
import { DataTable } from "@/types/financial";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

interface Props {
  table: DataTable;
  metrics: string[];           // row "metric" values to plot
  title?: string;
  colors?: string[];
  yFormat?: (v: number) => string;
}

const DEFAULT_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#a855f7"];

export default function TrendChart({ table, metrics, title, colors = DEFAULT_COLORS, yFormat }: Props) {
  if (!table?.rows?.length) return null;

  // Transform: rows (metric × year) → chart data (year × metric)
  const yearCols = table.headers.filter((h) => h !== "metric");
  const metricRows: Record<string, Record<string, number | null>> = {};
  table.rows.forEach((row) => {
    const m = String(row.metric ?? "");
    if (metrics.includes(m)) {
      metricRows[m] = {};
      yearCols.forEach((y) => {
        const v = row[y];
        metricRows[m][y] = typeof v === "number" ? v : null;
      });
    }
  });

  const chartData = yearCols.map((y) => {
    const point: Record<string, string | number | null> = { year: y };
    metrics.forEach((m) => {
      point[m] = metricRows[m]?.[y] ?? null;
    });
    return point;
  });

  const tickFmt = yFormat ?? ((v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}K` : String(v));

  return (
    <div className="w-full">
      {title && <h3 className="text-base font-semibold text-white mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="year"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#1f2937" }}
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={tickFmt}
          />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }}
            labelStyle={{ color: "#e5e7eb", fontWeight: 600 }}
            itemStyle={{ color: "#94a3b8" }}
            formatter={(v: number) => [v?.toLocaleString("en-IN", { maximumFractionDigits: 2 }), ""]}
          />
          <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12, paddingTop: 12 }} />
          {metrics.map((m, i) => (
            <Line
              key={m}
              type="monotone"
              dataKey={m}
              stroke={colors[i % colors.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
