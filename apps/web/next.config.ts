import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Monorepo pnpm: la raiz debe ser la del repo (../../) porque las deps de
  // web (firebase, next-auth, etc.) viven en <raiz>/node_modules/.pnpm via
  // symlinks; con un root mas estrecho Turbopack no las resolveria.
  // Next 16 exige que turbopack.root y outputFileTracingRoot coincidan, asi
  // que fijamos ambos explicitamente. Esto, junto con haber borrado el
  // apps/web/package-lock.json sobrante, evita la mala inferencia de raiz que
  // hacia observar un arbol gigante (.venv, scrapping...) y disparaba la RAM.
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../../"),
  turbopack: {
    root: path.join(__dirname, "../../"),
  },
  // Permite servir HMR / dev assets cuando entras por un host distinto a
  // localhost (ngrok, túneles, otra IP en la LAN). Los ngrok-free dan URLs
  // tipo "5180-xxxx.ngrok-free.app" — el wildcard cubre cualquiera.
  allowedDevOrigins: [
    "*.ngrok-free.app",
    "*.ngrok.app",
    "*.ngrok.io",
  ],
  experimental: {
    serverActions: {
      // FileDrop limita en cliente a 10 MB; damos 12 MB de holgura al
      // payload total del Server Action (file + boundary). Default es 1 MB,
      // demasiado bajo para PDFs de mallas (~700KB-2MB).
      bodySizeLimit: "12mb",
    },
  },
};

export default nextConfig;
