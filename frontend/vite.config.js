import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy API calls to the FastAPI backend during development so the frontend
// can use same-origin relative URLs (/analyze, /export/*).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/analyze": "http://localhost:8000",
      "/export": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
