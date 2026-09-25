import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#14181B",
          900: "#1A1F23",
          800: "#23292E",
          700: "#2E353B",
          500: "#5A636B",
          400: "#7C848C",
          300: "#A8AFB5",
          200: "#CDD2D6",
          100: "#E4E7EA",
          50: "#F1F3F5",
        },
        paper: "#FAFAF8",
        ocean: {
          DEFAULT: "#0E6BA8",
          600: "#0B5A8E",
          500: "#1677B8",
          400: "#2E8FC9",
          100: "#D9EBF7",
          50: "#EFF7FC",
        },
        earth: {
          DEFAULT: "#2F7D5B",
          600: "#25684A",
          400: "#4A9C78",
          100: "#D9EFE4",
        },
        amber: "#E8A33D",
        coral: "#D95D45",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(20,24,27,0.04), 0 8px 24px -12px rgba(20,24,27,0.12)",
        card: "0 1px 3px rgba(20,24,27,0.05), 0 12px 32px -16px rgba(20,24,27,0.14)",
        lift: "0 2px 6px rgba(20,24,27,0.06), 0 24px 48px -20px rgba(20,24,27,0.22)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s ease-out both",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
