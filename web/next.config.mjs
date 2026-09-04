/** @type {import('next').NextConfig} */
const allowedDevOrigins = process.env.NEXT_ALLOWED_DEV_ORIGINS
  ? process.env.NEXT_ALLOWED_DEV_ORIGINS.split(",")
      .map((origin) => origin.trim())
      .filter(Boolean)
  : [];

const nextConfig = {
  agentRules: false,
  allowedDevOrigins,
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: process.env.API_INTERNAL_BASE_URL
          ? `${process.env.API_INTERNAL_BASE_URL}/api/v1/:path*`
          : "http://localhost:8000/api/v1/:path*"
      }
    ];
  },
  async headers() {
    return [
      {
        source: "/admin/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "no-store, no-cache, max-age=0, must-revalidate"
          }
        ]
      }
    ];
  },
  typescript: {
    ignoreBuildErrors: true
  }
};

export default nextConfig;
