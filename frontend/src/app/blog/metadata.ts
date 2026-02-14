import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Blog - AI Development Tutorials & Project Guides',
  description: 'Expert guides on AI code generation, final year projects, tech stacks, Flutter development, machine learning, and more. Learn to build with BharatBuild AI.',
  keywords: [
    'AI coding tutorials',
    'final year project guide',
    'React vs Next.js',
    'Flutter tutorial',
    'machine learning projects',
    'SRS document guide',
    'IEEE format report',
    'tech stack comparison',
    'MVP development',
    'CSE project ideas',
    'code generation tutorial',
    'BharatBuild blog'
  ],
  openGraph: {
    title: 'BharatBuild AI Blog - Tutorials & Guides',
    description: 'Expert guides on AI development, project building, and tech careers. Learn to build complete projects with AI.',
    url: 'https://bharatbuild.ai/blog',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'BharatBuild AI Blog',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'BharatBuild AI Blog - Tutorials & Guides',
    description: 'Expert guides on AI development and project building.',
    images: ['/twitter-image.png'],
    creator: '@bharatbuild',
  },
  alternates: {
    canonical: 'https://bharatbuild.ai/blog',
  },
}
