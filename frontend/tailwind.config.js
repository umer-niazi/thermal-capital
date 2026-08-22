/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#f8fafc",
        surface: "#ffffff",
        "surface-subtle": "#f1f5f9",
        "surface-border": "#e2e8f0",
        "surface-border-strong": "#cbd5e1",
        brand: {
          50: "#f0fdf4",
          100: "#dcfce7",
          500: "#16a34a",
          600: "#15803d",
          700: "#166534",
        },
        primary: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
        },
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
}
