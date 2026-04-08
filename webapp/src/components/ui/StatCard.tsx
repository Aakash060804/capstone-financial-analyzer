"use client";
interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  color?: "blue" | "green" | "amber" | "red";
}

const colors: Record<string, string> = {
  blue:  "text-blue-400",
  green: "text-emerald-400",
  amber: "text-amber-400",
  red:   "text-red-400",
};

export default function StatCard({ label, value, sub, color = "blue" }: StatCardProps) {
  return (
    <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colors[color]}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}
