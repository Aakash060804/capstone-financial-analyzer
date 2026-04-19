"use client";
import { useParams } from "next/navigation";
import Topbar from "@/components/Topbar";
import CompanySubNav from "@/components/CompanySubNav";
import GrowthBadge from "@/components/GrowthBadge";
import { buildSnapshotKPIs } from "@/lib/dataUtils";
import { useCompanyData } from "@/lib/useCompanyData";

export default function CompanyLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const company = (params?.company as string)?.toUpperCase() ?? "";
  const { data } = useCompanyData(company);

  const kpis = data ? buildSnapshotKPIs(data) : [];
  const revenue = kpis.find((k) => k.label === "Revenue");
  const intrinsic = data?.forecasts?.dcf?.valuation?.intrinsic_value_per_share;
  const sector = data?.audit?.industry_classification?.sector;
  const rating = data?.ai_commentary?.thesis?.overall_rating;

  const ratingBg = rating === "Strong" ? "bg-fin-green/10 text-fin-green border-fin-green/30"
    : rating === "Adequate" ? "bg-fin-amber/10 text-fin-amber border-fin-amber/30"
    : "bg-fin-red/10 text-fin-red border-fin-red/30";

  return (
    <div className="min-h-screen bg-bg">
      <Topbar />
      <CompanySubNav company={company} />

      <div className="border-b border-border bg-surface">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex flex-wrap items-center gap-4 justify-between">
          <div className="flex items-center gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-black text-txt">{company}</h1>
                {sector && (
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                    {sector}
                  </span>
                )}
                {rating && (
                  <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${ratingBg}`}>
                    {rating}
                  </span>
                )}
              </div>
              {data?.meta?.company_name && data.meta.company_name !== company && (
                <p className="text-sm text-txt2 mt-0.5">{data.meta.company_name}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-6 flex-wrap">
            {revenue && (
              <div className="text-right">
                <p className="text-xs text-muted uppercase tracking-wider">Revenue (Latest)</p>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-txt num">
                    ₹{((revenue.value ?? 0) / 1000).toFixed(1)}K Cr
                  </span>
                  <GrowthBadge value={revenue.yoy} />
                </div>
              </div>
            )}
            {intrinsic && (
              <div className="text-right">
                <p className="text-xs text-muted uppercase tracking-wider">DCF Intrinsic Value</p>
                <p className="text-lg font-bold text-accent num">
                  ₹{intrinsic.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                </p>
              </div>
            )}
            {data?.meta && (
              <div className="text-right">
                <p className="text-xs text-muted uppercase tracking-wider">Currency</p>
                <p className="text-sm font-semibold text-txt2">{data.meta.currency}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-6 py-8">
        {children}
      </div>
    </div>
  );
}
