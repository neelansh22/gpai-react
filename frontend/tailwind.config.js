/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eefcff",
          100: "#d6f6ff",
          200: "#b3edff",
          300: "#7ee1ff",
          400: "#3fccff",
          500: "#0eb0f5",
          600: "#008dd1",
          700: "#0271a8",
          800: "#075f8a",
          900: "#0b4f72",
          950: "#06324c",
        },
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(14, 176, 245, 0.45)",
      },
      backgroundImage: {
        "grid-slate":
          "linear-gradient(to right, rgba(148,163,184,0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(148,163,184,0.08) 1px, transparent 1px)",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.55 },
        },
      },
      animation: {
        pulseGlow: "pulseGlow 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
