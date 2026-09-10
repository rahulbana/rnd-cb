import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build output goes to ../public, which the FastAPI server hosts at "/".
// In dev (`npm run dev`), the Vite server proxies /api to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../public",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.API_TARGET ?? "http://localhost:3000",
        changeOrigin: true,
      },
    },
  },
});
