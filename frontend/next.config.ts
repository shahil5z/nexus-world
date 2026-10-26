import type { NextConfig } from "next";

// Local only: proxy /api/* to the FastAPI server. Read when the config loads, so set NEXUS_BACKEND_URL for both `next build` and `next dev`.
// On Vercel, /api/* is routed to the Python service by vercel.json, so no rewrite is needed.
const backend = process.env.NEXUS_BACKEND_URL;

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return backend ? [{ source: "/api/:path*", destination: `${backend}/api/:path*` }] : [];
  },
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "X-Frame-Options", value: "DENY" },
      ],
    }];
  },
};

export default config;
