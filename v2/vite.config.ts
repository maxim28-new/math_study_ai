import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: path.join(rootDir, "apps/web"),
  base: "/v2/",
  publicDir: false,
  resolve: {
    alias: {
      "@v2": path.join(rootDir, "apps/web/src"),
    },
  },
  build: {
    outDir: path.join(rootDir, "apps/web/dist"),
    emptyOutDir: true,
    sourcemap: true,
  },
  server: {
    host: true,
    port: 5173,
  },
  preview: {
    host: true,
    port: 4173,
  },
});
