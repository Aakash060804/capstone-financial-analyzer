"use client";
import { AICommentary } from "@/types/financial";
import Badge from "./ui/Badge";

const trendIcon = (t: string) =>
  t === "improving" ? "↑" : t === "deteriorating" ? "↓" : "→";
const trendColor = (t: string) =>
  t === "improving" ? "text-emerald-400" : t === "deteriorating" ? "text-red-400" : "text-amber-400";
const severityVariant = (s: string): "red" | "amber" | "blue" =>
  s === "high" ? "red" : s === "medium" ? "amber" : "blue";
const ratingColor = (r: string) =>
  r === "Strong" ? "text-emerald-400" : r === "Adequate" ? "text-amber-400" : "text-red-400";
const riskColor = (r: string) =>
  r === "Low" ? "text-emerald-400" : r === "Medium" ? "text-amber-400" : "text-red-400";

interface Props { data: AICommentary }

export default function AIInsights({ data }: Props) {
  if (!data) return <p className="text-gray-500 text-sm">No AI analysis available.</p>;

  return (
    <div className="space-y-8">

      {/* Investment Thesis */}
      {data.thesis && (
        <div className="bg-[#161d2e] border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h3 className="text-base font-semibold text-white">Investment Thesis</h3>
            <span className={`text-lg font-bold ${ratingColor(data.thesis.overall_rating)}`}>
              {data.thesis.overall_rating}
            </span>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed mb-4">{data.thesis.executive_summary}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-emerald-500 uppercase tracking-wider font-semibold mb-2">Key Strengths</p>
              <ul className="space-y-1">
                {data.thesis.key_strengths?.map((s, i) => (
                  <li key={i} className="text-sm text-gray-300 flex gap-2">
                    <span className="text-emerald-500 mt-0.5">✓</span>{s}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs text-red-500 uppercase tracking-wider font-semibold mb-2">Key Concerns</p>
              <ul className="space-y-1">
                {data.thesis.key_concerns?.map((c, i) => (
                  <li key={i} className="text-sm text-gray-300 flex gap-2">
                    <span className="text-red-500 mt-0.5">✗</span>{c}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Category Commentary */}
      {data.categories?.length > 0 && (
        <div>
          <h3 className="text-base font-semibold text-white mb-3">Category Analysis</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.categories.map((cat, i) => (
              <div key={i} className="bg-[#161d2e] border border-gray-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-white text-sm">{cat.category}</span>
                  <span className={`text-sm font-bold ${trendColor(cat.trend)}`}>
                    {trendIcon(cat.trend)} {cat.trend}
                  </span>
                </div>
                <p className="text-xs text-blue-400 font-medium mb-1">{cat.headline}</p>
                <p className="text-xs text-gray-400 leading-relaxed">{cat.commentary}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Red Flags */}
      {data.red_flags && (
        <div>
          <div className="flex items-center gap-3 mb-3 flex-wrap">
            <h3 className="text-base font-semibold text-white">Red Flags</h3>
            <Badge label={`Overall Risk: ${data.red_flags.overall_risk}`}
              variant={riskColor(data.red_flags.overall_risk).includes("emerald") ? "green" : riskColor(data.red_flags.overall_risk).includes("amber") ? "amber" : "red"} />
            <Badge label={`${data.red_flags.total_flags} flags`} variant="muted" />
          </div>
          {data.red_flags.risk_summary && (
            <p className="text-sm text-gray-400 mb-4">{data.red_flags.risk_summary}</p>
          )}
          {data.red_flags.flags?.length > 0 ? (
            <div className="space-y-2">
              {data.red_flags.flags.map((flag, i) => (
                <div key={i} className="bg-[#161d2e] border border-gray-800 rounded-lg p-3 flex gap-3">
                  <Badge label={flag.severity} variant={severityVariant(flag.severity)} />
                  <div className="flex-1">
                    <span className="text-sm font-medium text-white">{flag.metric}</span>
                    <span className="text-gray-500 text-sm mx-2">·</span>
                    <span className="text-sm text-amber-400 font-mono">{flag.value}</span>
                    <p className="text-xs text-gray-400 mt-0.5">{flag.explanation}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-emerald-400">No red flags detected.</p>
          )}
        </div>
      )}
    </div>
  );
}
