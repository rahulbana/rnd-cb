import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api requests to the FastAPI backend during development so the
// frontend can call a same-origin path without CORS surprises.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
