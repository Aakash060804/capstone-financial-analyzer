import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinAnalyzer — NSE/BSE Financial Analysis & DCF Valuation",
  description: "AI-powered financial analysis, 5-year forecasts, DCF valuation and scenario modelling for NSE/BSE listed companies.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#060d1f]">
        {children}
      </body>
    </html>
  );
}
