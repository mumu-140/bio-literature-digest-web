import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const allowedHosts = (env.VITE_ALLOWED_HOSTS || env.APP_HOSTNAME || "localhost")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  return {
    plugins: [react()],
    server: {
      host: env.VITE_HOST || "127.0.0.1",
      port: Number(env.VITE_PORT || "8601"),
      allowedHosts,
      proxy: {
        "/api": {
          target: env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8602",
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: env.VITE_PREVIEW_HOST || "127.0.0.1",
      port: Number(env.VITE_PREVIEW_PORT || env.VITE_PORT || "8601"),
      allowedHosts,
    },
  };
});
