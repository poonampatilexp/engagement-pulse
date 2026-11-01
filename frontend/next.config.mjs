/** @type {import('next').NextConfig} */
const BACKEND_INTERNAL_URL = (process.env.DJANGO_INTERNAL_URL || process.env.INTERNAL_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

const nextConfig = {
  reactStrictMode: true,
  optimizeFonts: false,
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*/',
        destination: `${BACKEND_INTERNAL_URL}/api/:path*/`,
      },
      {
        source: '/api/:path*',
        destination: `${BACKEND_INTERNAL_URL}/api/:path*/`,
      },
    ];
  },
};

export default nextConfig;
