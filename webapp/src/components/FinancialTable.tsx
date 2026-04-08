"use client";
import { DataTable } from "@/types/financial";

interface Props {
  table: DataTable;
  title?: string;
  highlightRows?: string[];
  compact?: boolean;
}

function fmt(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "number") {
    if (Math.abs(v) >= 1000) return v.toLocaleString("en-IN", { maximumFractionDigits: 1 });
    return v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  }
  return String(v);
}

export default function FinancialTable({ table, title, highlightRows = [], compact }: Props) {
  if (!table?.headers?.length) return <p className="text-gray-500 text-sm">No data available.</p>;

  const yearCols = table.headers.filter((h) => h !== "metric");

  return (
    <div className="w-full">
      {title && <h3 className="text-base font-semibold text-white mb-3">{title}</h3>}
      <div className="overflow-x-auto rounded-lg border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900 text-gray-400 uppercase text-xs tracking-wider">
              <th className="text-left px-4 py-3 sticky left-0 bg-gray-900 min-w-[200px]">Metric</th>
              {yearCols.map((y) => (
                <th key={y} className="text-right px-4 py-3 whitespace-nowrap min-w-[90px]">{y}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, i) => {
              const metric = String(row.metric ?? "");
              const isHighlight = highlightRows.includes(metric);
              return (
                <tr
                  key={i}
                  className={`border-t border-gray-800 transition-colors hover:bg-gray-800/50
                    ${isHighlight ? "bg-blue-900/20 font-semibold" : i % 2 === 0 ? "bg-[#161d2e]" : "bg-[#111827]"}
                  `}
                >
                  <td className={`px-4 ${compact ? "py-1.5" : "py-2.5"} text-gray-300 sticky left-0 ${i % 2 === 0 ? "bg-[#161d2e]" : "bg-[#111827]"} ${isHighlight ? "bg-blue-900/20 text-white" : ""}`}>
                    {metric}
                  </td>
                  {yearCols.map((y) => (
                    <td key={y} className={`px-4 ${compact ? "py-1.5" : "py-2.5"} text-right text-gray-300 tabular-nums`}>
                      {fmt(row[y])}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
