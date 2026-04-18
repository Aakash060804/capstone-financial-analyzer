"use client";
interface Props { value: number | null; suffix?: string }

export default function GrowthBadge({ value, suffix = "%" }: Props) {
  if (value === null || isNaN(value)) return null;
  const pos = value >= 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-semibold px-1.5 py-0.5 rounded ${
      pos ? "bg-emerald-900/40 text-emerald-400" : "bg-red-900/40 text-red-400"
    }`}>
      {pos ? "▲" : "▼"} {Math.abs(value).toFixed(1)}{suffix}
    </span>
  );
}
