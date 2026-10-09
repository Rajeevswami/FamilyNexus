import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vite";

export default defineConfig({
  base: process.env.VITE_BASE_PATH ?? "/",
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    host: true,
    port: 5173,
    allowedHosts: true,
    // In dev the browser only ever talks to this dev server (same origin).
    // Requests under /api are proxied server-side to Django, so the app also
    // works behind a remote preview host where "localhost:8000" is unreachable.
    proxy: {
      "/api": {
        target: process.env.VITE_DEV_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      "/media": {
        target: process.env.VITE_DEV_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
