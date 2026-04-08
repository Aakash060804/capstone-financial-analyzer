"use client";
import { MonteCarlo } from "@/types/financial";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface Props { data: MonteCarlo }

export default function MonteCarloChart({ data }: Props) {
  if (!data?.p50) return <p className="text-gray-500 text-sm">No Monte Carlo data.</p>;

  const chartData = [
    { label: "P10", value: data.p10, color: "#ef4444" },
    { label: "P25", value: data.p25, color: "#f59e0b" },
    { label: "P50 (Median)", value: data.p50, color: "#3b82f6" },
    { label: "P75", value: data.p75, color: "#10b981" },
    { label: "P90", value: data.p90, color: "#6ee7b7" },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {chartData.map((d) => (
          <div key={d.label} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500 mb-1">{d.label}</p>
            <p className="text-lg font-bold" style={{ color: d.color }}>
              ₹{d.value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </p>
          </div>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <XAxis dataKey="label" tick={{ fill: "#6b7280", fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false}
            tickFormatter={(v) => `₹${(v).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }}
            formatter={(v: number) => [`₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`, "Value"]}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {chartData.map((d, i) => <Cell key={i} fill={d.color} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-6 text-sm text-gray-400 flex-wrap">
        <span>Simulations: <strong className="text-white">{data.n_simulations?.toLocaleString()}</strong></span>
        <span>Mean: <strong className="text-white">₹{data.mean?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</strong></span>
        <span>Std Dev: <strong className="text-white">₹{data.std?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</strong></span>
        <span>Prob within ±20%: <strong className="text-emerald-400">{data.prob_within_20?.toFixed(1)}%</strong></span>
      </div>
    </div>
  );
}
