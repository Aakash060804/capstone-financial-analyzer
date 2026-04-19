"use client";
import { useState, useEffect, useRef } from "react";
import { FinancialData } from "@/types/financial";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

export type DataStatus = "loading" | "running" | "done" | "error" | "not_found";

export interface CompanyDataState {
  data: FinancialData | null;
  status: DataStatus;
  message: string;
}

async function fetchData(slug: string): Promise<FinancialData | null> {
  // Try API
  if (API) {
    try {
      const r = await fetch(`${API}/data/${slug}`);
      if (r.ok) { const d = await r.json(); if (!d.error) return d; }
    } catch {}
  }
  // Fall back to bundled static files
  try {
    const r = await fetch(`/data/${slug}_financial_data.json`);
    if (r.ok) return r.json();
  } catch {}
  return null;
}

export function useCompanyData(company: string): CompanyDataState {
  const [state, setState] = useState<CompanyDataState>({ data: null, status: "loading", message: "Loading…" });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!company) return;
    const slug = company.toUpperCase();
    let cancelled = false;

    async function init() {
      setState({ data: null, status: "loading", message: "Loading…" });

      // 1. Try to load cached data
      const cached = await fetchData(slug);
      if (cancelled) return;
      if (cached) { setState({ data: cached, status: "done", message: "" }); return; }

      // 2. No data — trigger pipeline if API is available
      if (!API) { setState({ data: null, status: "not_found", message: "No data found. Run the pipeline first." }); return; }

      setState({ data: null, status: "running", message: "Starting analysis pipeline…" });

      try {
        await fetch(`${API}/analyze/${slug}`, { method: "POST" });
      } catch {
        setState({ data: null, status: "error", message: "Could not reach the analysis API." });
        return;
      }

      // 3. Poll every 6 seconds
      let elapsed = 0;
      const messages = [
        "Scraping financial data from Screener.in…",
        "Building income statement, balance sheet & cash flows…",
        "Calculating ratios, DuPont & common-size statements…",
        "Running DCF valuation & Monte Carlo simulation…",
        "Generating AI investment commentary…",
        "Finalising analysis — almost done…",
      ];

      pollRef.current = setInterval(async () => {
        if (cancelled) { clearInterval(pollRef.current!); return; }
        elapsed += 6;
        const msgIdx = Math.min(Math.floor(elapsed / 25), messages.length - 1);
        setState((s) => ({ ...s, message: messages[msgIdx] }));

        try {
          const st = await fetch(`${API}/status/${slug}`).then((r) => r.json());
          if (st.status === "done") {
            clearInterval(pollRef.current!);
            const fresh = await fetchData(slug);
            if (!cancelled) setState({ data: fresh, status: fresh ? "done" : "error", message: "" });
          } else if (st.status === "error") {
            clearInterval(pollRef.current!);
            if (!cancelled) setState({ data: null, status: "error", message: st.error ?? "Pipeline failed." });
          }
        } catch {}
      }, 6000);
    }

    init();
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [company]);

  return state;
}
