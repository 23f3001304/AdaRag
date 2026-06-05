import type { NextConfig } from "next";

// Proxy /api/* to the FastAPI backend so the browser hits a same-origin path (no CORS in dev).
// Point BACKEND_URL at the host API (:8001) or the Docker api service (:8000).
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/:path*` }];
  },
};

export default nextConfig;
