/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          0: "var(--color-surface-0)",
          1: "var(--color-surface-1)",
          2: "var(--color-surface-2)",
          3: "var(--color-surface-3)",
          border: "var(--color-surface-border)",
        },
        ink: {
          primary: "var(--color-ink-primary)",
          secondary: "var(--color-ink-secondary)",
          muted: "var(--color-ink-muted)",
        },
        signal: {
          pass: "var(--color-signal-pass)",
          passDim: "var(--color-signal-passDim)",
          warn: "var(--color-signal-warn)",
          warnDim: "var(--color-signal-warnDim)",
          fail: "var(--color-signal-fail)",
          failDim: "var(--color-signal-failDim)",
          info: "var(--color-signal-info)",
          infoDim: "var(--color-signal-infoDim)",
        },
        accent: {
          DEFAULT: "var(--color-accent)",
          teal: "var(--color-accent-teal)",
          amber: "var(--color-accent-amber)",
        },
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.5)",
      },
      animation: {
        "pulse-slow": "pulse 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};
