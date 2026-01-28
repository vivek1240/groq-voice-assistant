/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  output: 'standalone', // Required for Docker deployment
};

module.exports = nextConfig;
