import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => ({
  define:
    mode === "test"
      ? {
          "import.meta.env.VITE_API_BASE_URL": JSON.stringify("http://localhost:8000"),
        }
      : undefined,
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    pool: "threads",
    setupFiles: "./src/test/setup.ts",
  },
}));
