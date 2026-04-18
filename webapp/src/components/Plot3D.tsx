"use client";
import { useEffect, useRef } from "react";

interface SurfaceProps {
  xVals: string[];
  yVals: string[];
  zMatrix: (number | null)[][];
  title: string;
  xTitle?: string;
  yTitle?: string;
  zTitle?: string;
  highlightZ?: number;
}

export function SurfacePlot3D({ xVals, yVals, zMatrix, title, xTitle, yTitle, zTitle, highlightZ }: SurfaceProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    let cancelled = false;

    import("plotly.js-dist-min").then((Plotly: any) => {
      if (cancelled || !ref.current) return;

      const zClean = zMatrix.map((row) => row.map((v) => (v === null || isNaN(v as number) ? null : v)));

      const trace = {
        type: "surface",
        x: xVals,
        y: yVals,
        z: zClean,
        colorscale: [
          [0,    "#ff3d57"],
          [0.35, "#ffb020"],
          [0.65, "#3b7cf4"],
          [1,    "#00d68f"],
        ],
        contours: {
          z: { show: true, usecolormap: true, highlightcolor: "#ffffff", project: { z: true } },
        },
        opacity: 0.92,
        showscale: true,
        colorbar: {
          tickfont: { color: "#94a3b8", size: 11 },
          title: { text: zTitle ?? "₹", font: { color: "#94a3b8", size: 11 } },
          bgcolor: "rgba(0,0,0,0)",
          bordercolor: "#1a2d4f",
        },
      };

      const layout = {
        title: { text: title, font: { color: "#e2e8f0", size: 14 }, x: 0.05 },
        paper_bgcolor: "#0c1529",
        plot_bgcolor: "#0c1529",
        scene: {
          bgcolor: "#0c1529",
          xaxis: { title: xTitle ?? "X", color: "#4a6080", gridcolor: "#1a2d4f", zerolinecolor: "#1a2d4f" },
          yaxis: { title: yTitle ?? "Y", color: "#4a6080", gridcolor: "#1a2d4f", zerolinecolor: "#1a2d4f" },
          zaxis: { title: zTitle ?? "Z", color: "#4a6080", gridcolor: "#1a2d4f", zerolinecolor: "#1a2d4f" },
          camera: { eye: { x: 1.6, y: 1.6, z: 0.9 } },
        },
        margin: { l: 0, r: 0, t: 40, b: 0 },
        font: { family: "Inter, Segoe UI, system-ui", color: "#94a3b8" },
      };

      Plotly.newPlot(ref.current, [trace], layout, { responsive: true, displayModeBar: false });
    });

    return () => { cancelled = true; };
  }, [xVals, yVals, zMatrix, title, xTitle, yTitle, zTitle]);

  return <div ref={ref} style={{ width: "100%", height: 420 }} />;
}

// ─── Monte Carlo 3D Distribution ─────────────────────────────────────────────

interface MCProps {
  p10: number; p25: number; p50: number; p75: number; p90: number;
  mean: number; std: number;
}

export function MonteCarlo3D({ p10, p25, p50, p75, p90, mean, std }: MCProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    let cancelled = false;

    import("plotly.js-dist-min").then((Plotly: any) => {
      if (cancelled || !ref.current) return;

      // Generate smooth bell-curve distribution from mean + std
      const nPoints = 80;
      const xMin = Math.max(0, mean - 3.5 * std);
      const xMax = mean + 3.5 * std;
      const step = (xMax - xMin) / nPoints;

      const xs: number[] = [];
      const ys: number[] = [];
      const zs: number[] = [];

      // WACC axis (simulate range)
      const waccRange = [6, 8, 10, 12, 14, 16];

      for (const wacc of waccRange) {
        // Higher WACC shifts distribution left
        const waccShift = (10 - wacc) * std * 0.15;
        const waccMean = mean + waccShift;
        const waccStd = std * (1 + (wacc - 10) * 0.03);

        for (let i = 0; i <= nPoints; i++) {
          const x = xMin + i * step;
          const z = (1 / (waccStd * Math.sqrt(2 * Math.PI))) *
            Math.exp(-0.5 * Math.pow((x - waccMean) / waccStd, 2));
          xs.push(x);
          ys.push(wacc);
          zs.push(z * 100);
        }
      }

      const trace = {
        type: "scatter3d",
        mode: "lines",
        x: xs,
        y: ys,
        z: zs,
        line: {
          color: zs,
          colorscale: [
            [0, "#ff3d57"],
            [0.5, "#3b7cf4"],
            [1, "#00d68f"],
          ],
          width: 3,
        },
        opacity: 0.9,
      };

      // Percentile markers
      const markers = {
        type: "scatter3d",
        mode: "markers+text",
        x: [p10, p25, p50, p75, p90],
        y: [10, 10, 10, 10, 10],
        z: [0.001, 0.001, 0.001, 0.001, 0.001],
        text: ["P10", "P25", "P50", "P75", "P90"],
        textposition: "top center",
        marker: { size: 5, color: ["#ff3d57", "#ffb020", "#3b7cf4", "#00d68f", "#6ee7b7"] },
        textfont: { color: "#94a3b8", size: 10 },
      };

      const layout = {
        title: { text: "Monte Carlo Distribution (10,000 Simulations)", font: { color: "#e2e8f0", size: 13 }, x: 0.05 },
        paper_bgcolor: "#0c1529",
        scene: {
          bgcolor: "#0c1529",
          xaxis: { title: "Intrinsic Value (₹)", color: "#4a6080", gridcolor: "#1a2d4f" },
          yaxis: { title: "WACC (%)", color: "#4a6080", gridcolor: "#1a2d4f" },
          zaxis: { title: "Probability Density", color: "#4a6080", gridcolor: "#1a2d4f" },
          camera: { eye: { x: 1.8, y: -1.4, z: 1.0 } },
        },
        margin: { l: 0, r: 0, t: 40, b: 0 },
        showlegend: false,
        font: { family: "Inter, Segoe UI, system-ui", color: "#94a3b8" },
      };

      Plotly.newPlot(ref.current, [trace, markers], layout, { responsive: true, displayModeBar: false });
    });

    return () => { cancelled = true; };
  }, [p10, p25, p50, p75, p90, mean, std]);

  return <div ref={ref} style={{ width: "100%", height: 440 }} />;
}
