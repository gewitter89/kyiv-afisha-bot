/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0f19",
        card: "#151d30",
        border: "#1e293b",
        primary: "#6366f1",
        secondary: "#a855f7",
        success: "#10b981",
        warning: "#f59e0b",
        danger: "#ef4444",
        muted: "#94a3b8",
        text: "#f8fafc"
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
