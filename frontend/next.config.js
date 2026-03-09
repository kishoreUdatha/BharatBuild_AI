/** @type {import('next').NextConfig} */

// Parse image domains from environment variable
const imageDomains = (process.env.NEXT_PUBLIC_IMAGE_DOMAINS || 'localhost')
  .split(',')
  .map(d => d.trim())
  .filter(Boolean)

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: imageDomains,
    unoptimized: process.env.NODE_ENV === 'development'
  },
  // Environment variables are automatically loaded from .env.local
  // NEXT_PUBLIC_ prefixed variables are available in the browser
  env: {
    // These serve as fallbacks if environment variables are not set
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  },
  // Headers for WebContainer support (cross-origin isolation)
  // Required for SharedArrayBuffer which WebContainer uses
  async headers() {
    return [
      {
        // Apply to /build page where WebContainer is used
        source: '/build/:path*',
        headers: [
          {
            key: 'Cross-Origin-Embedder-Policy',
            value: 'require-corp',
          },
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin',
          },
        ],
      },
      {
        // Also apply to the main /build route
        source: '/build',
        headers: [
          {
            key: 'Cross-Origin-Embedder-Policy',
            value: 'require-corp',
          },
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin',
          },
        ],
      },
      {
        // Apply to /preview pages for WebContainer full-page preview
        source: '/preview/:path*',
        headers: [
          {
            key: 'Cross-Origin-Embedder-Policy',
            value: 'require-corp',
          },
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin',
          },
        ],
      },
      {
        // Apply to /webcontainer routes
        source: '/webcontainer/:path*',
        headers: [
          {
            key: 'Cross-Origin-Embedder-Policy',
            value: 'require-corp',
          },
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin',
          },
        ],
      },
    ]
  },
}

module.exports = nextConfig
