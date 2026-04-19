"use client";

const STEPS = [
  "Scraping Screener.in",
  "Financial statements",
  "Ratios & DuPont",
  "DCF & Monte Carlo",
  "AI commentary",
  "Finalising",
];

function getStep(message: string): number {
  if (message.includes("Ratio") || message.includes("DuPont")) return 2;
  if (message.includes("income") || message.includes("balance")) return 1;
  if (message.includes("DCF") || message.includes("Monte")) return 3;
  if (message.includes("AI") || message.includes("commentary")) return 4;
  if (message.includes("Finalising") || message.includes("almost")) return 5;
  if (message.includes("Scraping")) return 0;
  return 0;
}

export default function PipelineLoader({ company, message }: { company: string; message: string }) {
  const activeStep = getStep(message);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div className="w-full max-w-md">
        {/* Spinner */}
        <div className="flex justify-center mb-6">
          <div className="w-14 h-14 rounded-full border-4 border-accent/20 border-t-accent animate-spin" />
        </div>

        <p className="text-center text-lg font-bold text-txt mb-1">Analysing {company}</p>
        <p className="text-center text-sm text-txt2 mb-8">{message}</p>

        {/* Step tracker */}
        <div className="space-y-2">
          {STEPS.map((step, i) => {
            const done = i < activeStep;
            const active = i === activeStep;
            return (
              <div key={step} className={`flex items-center gap-3 rounded-lg px-4 py-2.5 transition-all ${active ? "bg-accent/10 border border-accent/30" : "border border-transparent"}`}>
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${done ? "bg-fin-green text-bg" : active ? "bg-accent text-white" : "bg-surface2 text-muted"}`}>
                  {done ? "✓" : i + 1}
                </div>
                <span className={`text-sm ${done ? "text-fin-green" : active ? "text-txt font-semibold" : "text-muted"}`}>{step}</span>
                {active && <div className="ml-auto flex gap-1">{[0,1,2].map(d => <div key={d} className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: `${d * 0.15}s` }} />)}</div>}
              </div>
            );
          })}
        </div>

        <p className="text-center text-xs text-muted mt-6">This takes 2–4 minutes · Do not close this tab</p>
      </div>
    </div>
  );
}
