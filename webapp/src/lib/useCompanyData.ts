"use client";
import { useState, useEffect, useRef } from "react";
import { FinancialData } from "@/types/financial";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

export type DataStatus = "loading" | "running" | "done" | "error" | "not_found";

export interface CompanyDataState {
  data: FinancialData | null;
  status: DataStatus;
  message: string;
  step: number;
}

async function fetchData(slug: string): Promise<FinancialData | null> {
  if (API) {
    try {
      const r = await fetch(`${API}/data/${slug}`);
      if (r.ok) { const d = await r.json(); if (!d.error) return d; }
    } catch {}
  }
  try {
    const r = await fetch(`/data/${slug}_financial_data.json`);
    if (r.ok) return r.json();
  } catch {}
  return null;
}

export function useCompanyData(company: string): CompanyDataState {
  const [state, setState] = useState<CompanyDataState>({ data: null, status: "loading", message: "Loading…", step: 0 });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!company) return;
    const slug = company.toUpperCase();
    let cancelled = false;

    async function init() {
      setState({ data: null, status: "loading", message: "Checking for cached data…", step: 0 });

      // 1. Try to load cached data first
      const cached = await fetchData(slug);
      if (cancelled) return;
      if (cached) { setState({ data: cached, status: "done", message: "", step: 6 }); return; }

      // 2. No data — trigger pipeline
      if (!API) {
        setState({ data: null, status: "not_found", message: "No data found. Run the pipeline first.", step: 0 });
        return;
      }

      setState({ data: null, status: "running", message: "Starting analysis pipeline…", step: 0 });

      try {
        await fetch(`${API}/analyze/${slug}`, { method: "POST" });
      } catch {
        setState({ data: null, status: "error", message: "Could not reach the analysis server.", step: 0 });
        return;
      }

      // 3. Poll every 4 seconds for fast feedback
      pollRef.current = setInterval(async () => {
        if (cancelled) { clearInterval(pollRef.current!); return; }
        try {
          const st = await fetch(`${API}/status/${slug}`).then((r) => r.json());

          if (st.status === "done") {
            clearInterval(pollRef.current!);
            const fresh = await fetchData(slug);
            if (!cancelled) setState({ data: fresh, status: fresh ? "done" : "error", message: "", step: 6 });

          } else if (st.status === "error") {
            clearInterval(pollRef.current!);
            if (!cancelled) setState({ data: null, status: "error", message: st.message ?? "Pipeline failed.", step: 0 });

          } else if (st.status === "running") {
            if (!cancelled) setState((prev) => ({
              ...prev,
              status: "running",
              message: st.message ?? prev.message,
              step: st.step ?? prev.step,
            }));
          }
        } catch {}
      }, 4000);
    }

    init();
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [company]);

  return state;
}
