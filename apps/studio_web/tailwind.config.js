/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#122033",
        muted: "#64748b",
        line: "#d8e0eb",
        brand: "#174ea6"
      }
    }
  },
  plugins: []
};
