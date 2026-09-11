import { defineConfig, loadEnv, Plugin } from "vite";
import react from "@vitejs/plugin-react";

function previewCacheHeadersPlugin(): Plugin {
  return {
    name: "configure-preview-cache-headers",
    configurePreviewServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url && req.url.startsWith("/assets/")) {
          // Hashed static assets can be cached immutably by browser and CDN
          res.setHeader("Cache-Control", "public, max-age=31536000, immutable");
        } else if (req.url === "/" || (req.url && (req.url.endsWith(".html") || !req.url.includes(".")))) {
          // SPA entry HTML must be revalidated
          res.setHeader("Cache-Control", "no-cache");
        }
        next();
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const allowedHosts = (env.VITE_ALLOWED_HOSTS || env.APP_HOSTNAME || "localhost")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const apiProxy = {
    "/api": {
      target: env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8602",
      changeOrigin: true,
    },
  };
  return {
    plugins: [react(), previewCacheHeadersPlugin()],
    server: {
      host: env.VITE_HOST || "127.0.0.1",
      port: Number(env.VITE_PORT || "8601"),
      allowedHosts,
      proxy: apiProxy,
    },
    preview: {
      host: env.VITE_PREVIEW_HOST || "127.0.0.1",
      port: Number(env.VITE_PREVIEW_PORT || env.VITE_PORT || "8601"),
      allowedHosts,
      proxy: apiProxy,
    },
  };
});
