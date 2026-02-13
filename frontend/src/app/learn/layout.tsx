import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Learn AI Development - Tutorials & Guides',
  description: 'Learn how to build projects with AI. Tutorials, guides, and best practices for using BharatBuild AI to create web apps, mobile apps, and academic projects.',
  keywords: [
    'AI development tutorial',
    'learn coding with AI',
    'BharatBuild guide',
    'project building tutorial',
    'code generation guide',
    'AI programming course',
    'learn AI coding',
    'developer tutorials'
  ],
  openGraph: {
    title: 'Learn to Build with AI - BharatBuild Tutorials',
    description: 'Step-by-step guides to master AI-powered development. From beginner to advanced.',
    url: 'https://bharatbuild.ai/learn',
  },
  alternates: {
    canonical: 'https://bharatbuild.ai/learn',
  },
}

export default function LearnLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
