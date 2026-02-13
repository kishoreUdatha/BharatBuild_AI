import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/admin/',
          '/api/',
          '/auth/',
          '/dashboard',
          '/projects',
          '/profile',
          '/build',
          '/employees',
          '/import',
          '/complete-profile',
          '/forgot-password',
        ],
      },
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: [
          '/admin/',
          '/api/',
          '/auth/',
        ],
      },
    ],
    sitemap: 'https://bharatbuild.ai/sitemap.xml',
  }
}
