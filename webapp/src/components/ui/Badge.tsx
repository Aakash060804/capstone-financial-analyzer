"use client";
interface BadgeProps {
  label: string;
  variant?: "blue" | "green" | "amber" | "red" | "muted";
}

const styles: Record<string, string> = {
  blue:  "bg-blue-900/40 text-blue-300 border border-blue-800",
  green: "bg-emerald-900/40 text-emerald-300 border border-emerald-800",
  amber: "bg-amber-900/40 text-amber-300 border border-amber-800",
  red:   "bg-red-900/40 text-red-300 border border-red-800",
  muted: "bg-gray-800 text-gray-400 border border-gray-700",
};

export default function Badge({ label, variant = "muted" }: BadgeProps) {
  return (
    <span className={`inline-block text-xs font-semibold px-2.5 py-0.5 rounded-full ${styles[variant]}`}>
      {label}
    </span>
  );
}
