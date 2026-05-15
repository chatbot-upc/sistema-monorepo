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
};

export default nextConfig;
