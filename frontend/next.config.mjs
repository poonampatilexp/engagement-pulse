/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  optimizeFonts: false,
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*/',
        destination: 'http://127.0.0.1:8000/api/:path*/',
      },
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*/',
      },
    ];
  },
};

export default nextConfig;
