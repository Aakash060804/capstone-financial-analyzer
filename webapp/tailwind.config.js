/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg:      "#0b0f1a",
        surface: "#111827",
        card:    "#161d2e",
        border:  "#1f2937",
        accent:  "#3b82f6",
        green:   "#10b981",
        amber:   "#f59e0b",
        red:     "#ef4444",
        muted:   "#94a3b8",
      },
    },
  },
  plugins: [],
};
