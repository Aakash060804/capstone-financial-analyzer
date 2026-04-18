/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg:        "#060d1f",
        surface:   "#0c1529",
        surface2:  "#111d35",
        border:    "#1a2d4f",
        border2:   "#1e3a5f",
        accent:    "#3b7cf4",
        fin: {
          green:  "#00d68f",
          red:    "#ff3d57",
          amber:  "#ffb020",
          blue:   "#3b7cf4",
        },
        txt:       "#e2e8f0",
        txt2:      "#94a3b8",
        muted:     "#4a6080",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
};
