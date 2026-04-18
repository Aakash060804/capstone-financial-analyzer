"use client";
import { DataTable } from "@/types/financial";

interface Props {
  table: DataTable;
  highlightRows?: string[];
  compact?: boolean;
  lastNYears?: number;
}

function fmt(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "number") {
    if (!isFinite(v)) return "—";
    if (Math.abs(v) >= 100000) return `${(v / 100000).toFixed(2)}L`;
    if (Math.abs(v) >= 1000)   return `${(v / 1000).toFixed(1)}K`;
    return v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  }
  return String(v);
}

export default function FinTable({ table, highlightRows = [], compact, lastNYears }: Props) {
  if (!table?.headers?.length) return <p className="text-sm" style={{ color: "var(--text-muted)" }}>No data.</p>;

  let yearCols = table.headers.filter((h) => h !== "metric");
  if (lastNYears) yearCols = yearCols.slice(-lastNYears);

  return (
    <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "var(--border)" }}>
      <table className="fin-table">
        <thead>
          <tr>
            <th>Metric</th>
            {yearCols.map((y) => <th key={y}>{y}</th>)}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, i) => {
            const metric = String(row.metric ?? "");
            const hl = highlightRows.includes(metric);
            return (
              <tr key={i} className={hl ? "highlight" : ""}>
                <td className={compact ? "py-1.5" : ""}>{metric}</td>
                {yearCols.map((y) => (
                  <td key={y} className={`num ${compact ? "py-1.5" : ""}`}>{fmt(row[y])}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
