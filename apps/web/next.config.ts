import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
