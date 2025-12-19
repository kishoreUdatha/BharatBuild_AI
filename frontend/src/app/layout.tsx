import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { UpgradeProvider } from '@/contexts/UpgradeContext'
import { ToastProvider } from '@/components/ui/toast'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'BharatBuild AI - AI-Powered Project Generation',
  description: 'Complete AI-driven platform for academic projects, code automation, and product building',
  icons: {
    icon: '/icon.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
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
