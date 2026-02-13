import type { Metadata } from 'next'
import Script from 'next/script'
import { Inter } from 'next/font/google'
import './globals.css'
import { UpgradeProvider } from '@/contexts/UpgradeContext'
import { ToastProvider } from '@/components/ui/toast'
import { OrganizationJsonLd, SoftwareApplicationJsonLd, FAQJsonLd, WebsiteJsonLd } from '@/components/seo/JsonLd'

const inter = Inter({ subsets: ['latin'] })

// Google Analytics Measurement ID - Replace with your actual GA4 ID
const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || 'G-XXXXXXXXXX'

export const metadata: Metadata = {
  metadataBase: new URL('https://bharatbuild.ai'),
  title: {
    default: "BharatBuild AI - India's #1 AI Code & Project Generator | Build Apps in Minutes",
    template: '%s | BharatBuild AI'
  },
  description: 'Generate complete projects with AI. Get production-ready code, documentation, PPT & viva Q&A in minutes. Trusted by 10,000+ students & developers across India.',
  keywords: [
    'AI code generator',
    'project generator India',
    'final year project',
    'AI app builder',
    'code generation tool',
    'BharatBuild',
    'automatic coding',
    'student project generator',
    'BTech project',
    'MCA project',
    'React app generator',
    'Next.js generator',
    'Flutter app generator',
    'full stack generator',
    'MVP builder',
    'Bolt.new alternative',
    'code from description',
    'project report generator',
    'SRS document generator',
    'viva questions generator'
  ],
  authors: [{ name: 'BharatBuild AI', url: 'https://bharatbuild.ai' }],
  creator: 'BharatBuild AI',
  publisher: 'BharatBuild AI',
  icons: {
    icon: '/icon.svg',
    apple: '/apple-icon.png',
  },
  openGraph: {
    type: 'website',
    locale: 'en_IN',
    url: 'https://bharatbuild.ai',
    siteName: 'BharatBuild AI',
    title: "BharatBuild AI - India's #1 AI Code & Project Generator",
    description: 'Generate complete projects with AI. Get production-ready code, documentation & presentations in minutes. Trusted by 10,000+ students & developers.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'BharatBuild AI - AI Code Generator',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: "BharatBuild AI - India's #1 AI Code Generator",
    description: 'Build complete projects with AI. Code, documentation & deployment in minutes.',
    images: ['/twitter-image.png'],
    creator: '@bharatbuild',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: {
    canonical: 'https://bharatbuild.ai',
  },
  verification: {
    google: '7VNX8-inOI9mgtQvqIimZJyR8-ugHwo1jjhNzHsdkLc',
  },
  category: 'technology',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        {/* Google Analytics */}
        <Script
          src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
          strategy="afterInteractive"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', '${GA_MEASUREMENT_ID}', {
              page_path: window.location.pathname,
            });
          `}
        </Script>

        {/* Structured Data */}
        <OrganizationJsonLd />
        <SoftwareApplicationJsonLd />
        <FAQJsonLd />
        <WebsiteJsonLd />
      </head>
      <body className={inter.className}>
        <ToastProvider>
          <UpgradeProvider>
            {children}
          </UpgradeProvider>
        </ToastProvider>
      </body>
    </html>
  )
}
