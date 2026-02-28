import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// Backend URL — override with VITE_BACKEND_URL env var for Docker / remote deployments
const backendHttp = process.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8080";
const backendWs = backendHttp.replace(/^http/, "ws");

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 5173,
    hmr: {
      overlay: false,
    },
    proxy: {
      "/api": {
        target: backendHttp,
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: backendWs,
        ws: true,
        changeOrigin: true,
      },
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
