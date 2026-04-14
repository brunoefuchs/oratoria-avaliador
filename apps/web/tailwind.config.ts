import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#a2c9ff",
        "primary-dim": "#8ebfff",
        "primary-container": "#004d89",
        "on-primary": "#00315b",
        "on-primary-container": "#8ebfff",
        secondary: "#45d8ed",
        "secondary-container": "#00bacd",
        "on-secondary": "#00363d",
        "on-secondary-container": "#00444d",
        tertiary: "#ffb954",
        "tertiary-container": "#6a4400",
        "on-tertiary": "#452b00",
        "on-tertiary-container": "#f6af46",
        error: "#ffb4ab",
        "error-container": "#93000a",
        "on-error": "#690005",
        background: "#0b1326",
        surface: "#0b1326",
        "surface-dim": "#0b1326",
        "surface-bright": "#31394d",
        "surface-container-lowest": "#060e20",
        "surface-container-low": "#131b2e",
        "surface-container": "#171f33",
        "surface-container-high": "#222a3d",
        "surface-container-highest": "#2d3449",
        "surface-variant": "#2d3449",
        "on-surface": "#dae2fd",
        "on-background": "#dae2fd",
        "on-surface-variant": "#c3c6d4",
        outline: "#8d909d",
        "outline-variant": "#434652",
        "inverse-surface": "#dae2fd",
        "inverse-primary": "#0060a8",
      },
      fontFamily: {
        headline: ["var(--font-manrope)", "sans-serif"],
        body: ["var(--font-jakarta)", "sans-serif"],
        label: ["var(--font-jakarta)", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "0.5rem",
        md: "0.75rem",
        lg: "1rem",
        xl: "1.5rem",
        "2xl": "2rem",
        "3xl": "2.5rem",
        full: "9999px",
      },
      backgroundImage: {
        "ai-pulse": "linear-gradient(135deg, #45d8ed 0%, #004d89 100%)",
        "ai-pulse-soft":
          "linear-gradient(135deg, rgba(69,216,237,0.2) 0%, rgba(0,77,137,0.2) 100%)",
      },
      boxShadow: {
        "cta-glow":
          "0 20px 40px rgba(69, 216, 237, 0.25), 0 0 0 1px rgba(69, 216, 237, 0.1)",
        "ambient":
          "0 40px 40px rgba(218, 226, 253, 0.08)",
        "focus-ring":
          "0 0 0 1px rgba(69, 216, 237, 0.4), 0 0 16px rgba(69, 216, 237, 0.25)",
      },
      keyframes: {
        "glow-pulse": {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "glow-pulse": "glow-pulse 2.4s ease-in-out infinite",
        float: "float 3.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
