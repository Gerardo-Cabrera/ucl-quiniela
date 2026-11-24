import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // Un solo chunk A PROPÓSITO: con chunks por página, un despliegue rompería las
    // pestañas ya abiertas (y las hay abiertas durante horas en los partidos). El aviso
    // por defecto (500 kB) recomienda partir el bundle; se sube el umbral para que solo
    // salte si el tamaño crece de verdad.
    chunkSizeWarningLimit: 650,
  },
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
