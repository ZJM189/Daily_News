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
  typescript: {
    ignoreBuildErrors: true
  }
};

export default nextConfig;
