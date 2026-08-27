import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies API + SSE calls to the FastAPI backend so the browser
// talks to a single origin (no CORS headaches during local development).
// BACKEND_URL lets docker-compose point at the `backend` service instead of
// localhost.
const backend = process.env.BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: backend,
        changeOrigin: true,
      },
    },
  },
});
