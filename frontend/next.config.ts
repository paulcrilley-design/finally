import type { NextConfig } from "next";

// Static export: FastAPI serves frontend/out, so there is no Node server.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
