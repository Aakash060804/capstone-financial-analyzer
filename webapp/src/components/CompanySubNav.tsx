"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { label: "Snapshot",  path: "" },
  { label: "Forecast",  path: "/forecast" },
  { label: "Valuation", path: "/valuation" },
  { label: "Analysis",  path: "/analysis" },
  { label: "Reports",   path: "/reports" },
];

export default function CompanySubNav({ company }: { company: string }) {
  const pathname = usePathname();

  return (
    <nav className="sticky top-12 z-40 border-b" style={{ background: "rgba(6,13,31,0.95)", borderColor: "var(--border)", backdropFilter: "blur(12px)" }}>
      <div className="max-w-[1400px] mx-auto px-6 flex items-center gap-1 overflow-x-auto">
        {LINKS.map((l) => {
          const href = `/${company}${l.path}`;
          const base = `/${company}${l.path}`;
          const isActive = pathname === base || pathname === `${base}/`;
          return (
            <Link
              key={l.label}
              href={href}
              className={`px-4 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors ${
                isActive
                  ? "border-[#3b7cf4] text-[#3b7cf4]"
                  : "border-transparent hover:text-white"
              }`}
              style={{ color: isActive ? "#3b7cf4" : "var(--text-muted)" }}
            >
              {l.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
