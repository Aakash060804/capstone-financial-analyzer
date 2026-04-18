"use client";
import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";
import { getSeries } from "@/lib/dataUtils";
import { DataTable } from "@/types/financial";

interface Props { table: DataTable; metric: string; color?: string }

export default function SparkLine({ table, metric, color = "#3b7cf4" }: Props) {
  const series = getSeries(table, metric).filter((p) => p.value !== null);
  if (series.length < 2) return null;
  const data = series.map((p) => ({ v: p.value }));
  const last  = data[data.length - 1]?.v ?? 0;
  const first = data[0]?.v ?? 0;
  const up = (last ?? 0) >= (first ?? 0);

  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={data}>
        <Line type="monotone" dataKey="v" stroke={up ? "#00d68f" : "#ff3d57"} strokeWidth={1.5} dot={false} />
        <Tooltip
          contentStyle={{ background: "#0c1529", border: "1px solid #1a2d4f", borderRadius: 6, fontSize: 11 }}
          itemStyle={{ color: "#94a3b8" }}
          formatter={(v: number) => [v?.toLocaleString("en-IN", { maximumFractionDigits: 1 }), metric]}
          labelFormatter={() => ""}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
