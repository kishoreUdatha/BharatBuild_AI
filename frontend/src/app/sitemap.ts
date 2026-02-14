import { MetadataRoute } from 'next'

// Blog post slugs for sitemap
const blogPosts = [
  { slug: 'react-vs-nextjs-which-to-choose-2025', date: '2025-02-14' },
  { slug: 'flutter-app-development-beginners-guide', date: '2025-02-10' },
  { slug: 'machine-learning-projects-for-students', date: '2025-02-05' },
  { slug: 'how-to-write-srs-document', date: '2025-01-28' },
  { slug: 'best-tech-stack-for-web-development-2025', date: '2025-01-20' },
  { slug: 'complete-final-year-project-with-ai', date: '2025-01-15' },
  { slug: 'ieee-format-project-report-guide', date: '2025-01-10' },
  { slug: 'ai-code-generators-compared', date: '2025-01-05' },
  { slug: 'build-mvp-without-coding', date: '2025-01-02' },
  { slug: '50-final-year-project-ideas-cse', date: '2025-01-01' },
]

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://bharatbuild.ai'

  // Static pages
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: `${baseUrl}/features`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/pricing`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/register`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/showcase`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/learn`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/campus-drive`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.7,
    },
    {
      url: `${baseUrl}/paper`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.7,
    },
    {
      url: `${baseUrl}/docs`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.7,
    },
    {
      url: `${baseUrl}/privacy`,
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
  ]

  // Blog posts
  const blogPages: MetadataRoute.Sitemap = blogPosts.map((post) => ({
    url: `${baseUrl}/blog/${post.slug}`,
    lastModified: new Date(post.date),
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }))

  return [...staticPages, ...blogPages]
}
