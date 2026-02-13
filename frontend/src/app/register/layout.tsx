import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Sign Up Free - Start Building Projects with AI Today',
  description: 'Create your free BharatBuild account. Get 3 free projects, AI code generation, and complete documentation. Students, developers & founders welcome.',
  keywords: [
    'BharatBuild signup',
    'create account',
    'free registration',
    'AI code generator signup',
    'student registration',
    'developer signup',
    'free AI tool registration'
  ],
  openGraph: {
    title: 'Join BharatBuild AI - Start Building for Free',
    description: 'Sign up and get 3 free projects. Generate code, documentation & more with AI.',
    url: 'https://bharatbuild.ai/register',
  },
  alternates: {
    canonical: 'https://bharatbuild.ai/register',
  },
}

export default function RegisterLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
