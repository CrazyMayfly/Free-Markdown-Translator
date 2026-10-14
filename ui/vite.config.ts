import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";

// Dev mode talks to the API through the vite proxy (mdtx --ui-port 8000).
// Inside Tauri, Rust injects window.__MDTX_API_BASE__ and the app calls the
// sidecar directly.
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Override with MDTX_API_TARGET when 8000 is taken in dev.
      "/api": {
        target: process.env.MDTX_API_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
