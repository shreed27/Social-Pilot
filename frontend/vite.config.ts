import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// `npm run build`          → frontend/dist, served by FastAPI at /
// `npm run build:artifact` → one self-contained HTML file running on demo data
export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss(), ...(mode === "artifact" ? [viteSingleFile()] : [])],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  define: { __DEMO_ONLY__: JSON.stringify(mode === "artifact") },
  build: { outDir: mode === "artifact" ? "dist-artifact" : "dist", chunkSizeWarningLimit: 2000 },
  server: {
    proxy: { "/api": "http://localhost:8000", "/media": "http://localhost:8000" },
  },
}));
