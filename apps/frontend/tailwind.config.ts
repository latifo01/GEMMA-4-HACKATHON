import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202a",
        mist: "#f6f8fa",
        clinical: {
          blue: "#2563eb",
          teal: "#0f766e",
          green: "#15803d",
          amber: "#b45309",
          red: "#b91c1c"
        }
      },
      boxShadow: {
        subtle: "0 18px 45px rgba(23, 32, 42, 0.08)"
      }
    }
  },
  plugins: []
} satisfies Config;
