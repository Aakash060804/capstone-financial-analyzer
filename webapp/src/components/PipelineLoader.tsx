"use client";

const STEPS = [
  "Fetching data from Screener.in",
  "Building financial statements",
  "Ratios, DuPont & classification",
  "DCF valuation & Monte Carlo",
  "AI commentary (parallel)",
  "Exporting results",
];

export default function PipelineLoader({ company, message, step = 0 }: { company: string; message: string; step?: number }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div className="w-full max-w-md">
        {/* Spinner */}
        <div className="flex justify-center mb-6">
          <div className="w-14 h-14 rounded-full border-4 border-accent/20 border-t-accent animate-spin" />
        </div>

        <p className="text-center text-lg font-bold text-txt mb-1">Analysing {company}</p>
        <p className="text-center text-sm text-txt2 mb-8 min-h-[20px]">{message}</p>

        {/* Step tracker */}
        <div className="space-y-2">
          {STEPS.map((label, i) => {
            const done   = i < step;
            const active = i === step;
            return (
              <div key={label} className={`flex items-center gap-3 rounded-lg px-4 py-2.5 transition-all ${active ? "bg-accent/10 border border-accent/30" : "border border-transparent"}`}>
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${done ? "bg-fin-green text-bg" : active ? "bg-accent text-white" : "bg-surface2 text-muted"}`}>
                  {done ? "✓" : i + 1}
                </div>
                <span className={`text-sm ${done ? "text-fin-green" : active ? "text-txt font-semibold" : "text-muted"}`}>{label}</span>
                {active && (
                  <div className="ml-auto flex gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce [animation-delay:0ms]" />
                    <div className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce [animation-delay:150ms]" />
                    <div className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce [animation-delay:300ms]" />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <p className="text-center text-xs text-muted mt-6">Typically completes in 90–120 seconds · Do not close this tab</p>
      </div>
    </div>
  );
}
