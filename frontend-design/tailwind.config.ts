import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    screens: {
      sm: "640px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
      "2xl": "1536px",
    },
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1440px",
      },
    },
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        fg: "var(--fg)",
        "fg-2": "var(--fg-2)",
        muted: "var(--muted)",
        "muted-2": "var(--muted-2)",
        accent: {
          DEFAULT: "var(--accent)",
          fg: "var(--accent-fg)",
        },
        line: "var(--line)",
        "line-2": "var(--line-2)",
        signal: {
          DEFAULT: "var(--signal)",
          soft: "var(--signal-soft)",
        },
        success: {
          DEFAULT: "var(--success)",
          soft: "var(--success-soft)",
        },
        upc: {
          DEFAULT: "var(--upc)",
          soft: "var(--upc-soft)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        serif: ["var(--font-serif)", "ui-serif", "serif"],
      },
      fontSize: {
        "2xs": ["10px", { lineHeight: "1.4", letterSpacing: "0.4px" }],
        xs: ["11px", { lineHeight: "1.4" }],
        sm: ["12.5px", { lineHeight: "1.5" }],
        base: ["14px", { lineHeight: "1.5" }],
        md: ["15px", { lineHeight: "1.5" }],
        lg: ["18px", { lineHeight: "1.4", letterSpacing: "-0.2px" }],
        xl: ["22px", { lineHeight: "1.3", letterSpacing: "-0.3px" }],
        "2xl": ["28px", { lineHeight: "1.2", letterSpacing: "-0.4px" }],
        "3xl": ["36px", { lineHeight: "1.15", letterSpacing: "-0.5px" }],
        display: ["84px", { lineHeight: "0.95", letterSpacing: "-2px" }],
      },
      fontWeight: {
        normal: "400",
        medium: "500",
        semibold: "600",
        bold: "700",
      },
      spacing: {
        1: "4px",
        2: "8px",
        3: "12px",
        4: "16px",
        5: "20px",
        6: "24px",
        8: "32px",
        10: "40px",
        12: "48px",
      },
      borderRadius: {
        xs: "2px",
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "12px",
      },
      boxShadow: {
        overlay:
          "0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.08)",
        modal: "0 10px 40px rgba(0,0,0,0.12)",
        toast: "0 4px 16px rgba(0,0,0,0.10)",
      },
      zIndex: {
        base: "0",
        sticky: "10",
        dropdown: "30",
        overlay: "40",
        modal: "50",
        toast: "60",
      },
      transitionTimingFunction: {
        "out-quart": "cubic-bezier(0.25, 1, 0.5, 1)",
      },
      transitionDuration: {
        fast: "120ms",
        DEFAULT: "180ms",
        slow: "240ms",
      },
    },
  },
  plugins: [],
};

export default config;
