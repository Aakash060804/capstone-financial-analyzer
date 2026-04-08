"use client";
import { SensitivityTable } from "@/types/financial";

interface Props { data: SensitivityTable; intrinsic?: number | null }

function cellColor(val: number | null, intrinsic: number): string {
  if (val === null) return "bg-gray-800 text-gray-600";
  const ratio = val / intrinsic;
  if (ratio >= 1.2)  return "bg-emerald-900/70 text-emerald-300";
  if (ratio >= 1.0)  return "bg-emerald-900/40 text-emerald-400";
  if (ratio >= 0.85) return "bg-amber-900/40 text-amber-400";
  return "bg-red-900/40 text-red-400";
}

export default function SensitivityHeatmap({ data, intrinsic }: Props) {
  if (!data?.table?.rows?.length) return <p className="text-gray-500 text-sm">No sensitivity data.</p>;

  const base = intrinsic ?? 0;
  const yearCols = data.table.headers.filter((h) => h !== "metric");

  return (
    <div>
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <h3 className="text-base font-semibold text-white">DCF Sensitivity — Intrinsic Value per Share (₹)</h3>
        <span className="text-xs text-gray-500">{data.row_label} (rows) vs {data.col_label} (columns)</span>
      </div>
      <div className="flex gap-4 mb-3 text-xs flex-wrap">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-emerald-900/70 inline-block" /> &gt;20% upside</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-emerald-900/40 inline-block" /> 0–20% upside</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-900/40 inline-block" /> 0–15% downside</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-900/40 inline-block" /> &gt;15% downside</span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-800">
        <table className="text-sm w-full">
          <thead>
            <tr className="bg-gray-900 text-gray-400 text-xs uppercase tracking-wider">
              <th className="px-4 py-2 text-left">WACC \ TGR</th>
              {yearCols.map((c) => <th key={c} className="px-4 py-2 text-right">{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.table.rows.map((row, i) => (
              <tr key={i} className="border-t border-gray-800">
                <td className="px-4 py-2 text-gray-400 font-medium bg-gray-900">{String(row.metric)}</td>
                {yearCols.map((c) => {
                  const val = typeof row[c] === "number" ? (row[c] as number) : null;
                  return (
                    <td key={c} className={`px-4 py-2 text-right font-semibold tabular-nums ${cellColor(val, base)}`}>
                      {val !== null ? `₹${val.toLocaleString("en-IN", { maximumFractionDigits: 0 })}` : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
