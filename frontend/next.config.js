/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
      {
        source: "/renders/:path*",
        destination: "http://localhost:8000/renders/:path*",
      },
      {
        source: "/assets/:path*",
        destination: "http://localhost:8000/assets/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
