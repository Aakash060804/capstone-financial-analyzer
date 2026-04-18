"use client";
import GrowthBadge from "./GrowthBadge";
import { SnapshotKPI, fmtRaw } from "@/lib/dataUtils";

interface Props { kpi: SnapshotKPI; highlight?: boolean }

export default function KPICard({ kpi, highlight }: Props) {
  return (
    <div className={`card-sm flex flex-col gap-1.5 transition-all hover:border-[#2a4a7f] ${
      highlight ? "border-[#2a4a7f] glow-blue" : ""
    }`}>
      <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
        {kpi.label}
      </p>
      <p className="text-2xl font-bold num" style={{ color: "var(--text)" }}>
        {fmtRaw(kpi.value, kpi.format)}
      </p>
      <div className="flex items-center gap-2">
        <GrowthBadge value={kpi.yoy} />
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>YoY</span>
        <span className="text-xs ml-auto" style={{ color: "var(--text-muted)" }}>{kpi.year}</span>
      </div>
    </div>
  );
}
