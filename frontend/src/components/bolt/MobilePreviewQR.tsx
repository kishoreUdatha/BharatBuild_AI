'use client'

import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Smartphone, Copy, Check, ExternalLink, Monitor, Apple, Play, Package, Loader2 } from 'lucide-react'

interface MobilePreviewQRProps {
  expoUrl: string
  qrBase64?: string
  webFallbackUrl?: string
  onSwitchToWeb?: () => void
  onBuildAPK?: () => void
  onBuildIPA?: () => void
  isBuildingAPK?: boolean
  isBuildingIPA?: boolean
}

export function MobilePreviewQR({
  expoUrl,
  qrBase64,
  webFallbackUrl,
  onSwitchToWeb,
  onBuildAPK,
  onBuildIPA,
  isBuildingAPK = false,
  isBuildingIPA = false
}: MobilePreviewQRProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(expoUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center h-full bg-[hsl(var(--bolt-bg-primary))] p-6 overflow-auto">
      {/* Header */}
      <div className="flex items-center gap-2 mb-6">
        <Smartphone className="w-6 h-6 text-[hsl(var(--bolt-accent))]" />
        <h2 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">Mobile Preview</h2>
      </div>

      {/* QR Code */}
      <div className="bg-white p-4 rounded-xl shadow-lg mb-6">
        {qrBase64 ? (
          <img
            src={`data:image/png;base64,${qrBase64}`}
            alt="Expo QR Code"
            className="w-64 h-64"
          />
        ) : (
          <QRCodeSVG
            value={expoUrl}
            size={256}
            level="L"
            includeMargin={true}
          />
        )}
      </div>

      {/* Instructions */}
      <p className="text-[hsl(var(--bolt-text-secondary))] text-center mb-4">
        Scan with{' '}
        <span className="font-semibold text-[hsl(var(--bolt-accent))]">Expo Go</span>
        {' '}app on your phone
      </p>

      {/* URL Display with Copy */}
      <div className="flex items-center gap-2 bg-[hsl(var(--bolt-bg-secondary))] px-4 py-2 rounded-lg mb-4 max-w-full">
        <code className="text-xs text-[hsl(var(--bolt-text-secondary))] truncate max-w-[200px] sm:max-w-[300px]">
          {expoUrl}
        </code>
        <button
          onClick={handleCopy}
          className="p-1.5 rounded hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors flex-shrink-0"
          title="Copy URL"
        >
          {copied ? (
            <Check className="w-4 h-4 text-green-500" />
          ) : (
            <Copy className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
          )}
        </button>
      </div>

      {/* Web Fallback Button */}
      {webFallbackUrl && onSwitchToWeb && (
        <button
          onClick={onSwitchToWeb}
          className="flex items-center gap-2 text-sm text-[hsl(var(--bolt-text-tertiary))] hover:text-[hsl(var(--bolt-accent))] transition-colors mb-6"
        >
          <Monitor className="w-4 h-4" />
          <span>Switch to Web Preview</span>
        </button>
      )}

      {/* App Store Links */}
      <div className="flex flex-col items-center gap-3 mt-4">
        <p className="text-xs text-[hsl(var(--bolt-text-tertiary))]">
          Don&apos;t have Expo Go? Download it:
        </p>
        <div className="flex gap-4">
          <a
            href="https://apps.apple.com/app/expo-go/id982107779"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] text-xs transition-colors"
          >
            <Apple className="w-4 h-4" />
            <span>iOS</span>
            <ExternalLink className="w-3 h-3 opacity-50" />
          </a>
          <a
            href="https://play.google.com/store/apps/details?id=host.exp.exponent"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] text-xs transition-colors"
          >
            <Play className="w-4 h-4" />
            <span>Android</span>
            <ExternalLink className="w-3 h-3 opacity-50" />
          </a>
        </div>
      </div>

      {/* Build Standalone App Section */}
      {(onBuildAPK || onBuildIPA) && (
        <div className="mt-6 p-4 bg-[hsl(var(--bolt-bg-secondary))] rounded-lg max-w-sm">
          <div className="flex items-center gap-2 mb-3">
            <Package className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
            <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
              Build Standalone App
            </h3>
          </div>
          <p className="text-xs text-[hsl(var(--bolt-text-secondary))] mb-3">
            Generate a downloadable APK or IPA file that works without Expo Go
          </p>
          <div className="flex gap-2">
            {onBuildAPK && (
              <button
                onClick={onBuildAPK}
                disabled={isBuildingAPK}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
              >
                {isBuildingAPK ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Smartphone className="w-4 h-4" />
                )}
                <span>{isBuildingAPK ? 'Building...' : 'Build APK'}</span>
              </button>
            )}
            {onBuildIPA && (
              <button
                onClick={onBuildIPA}
                disabled={isBuildingIPA}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
              >
                {isBuildingIPA ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Apple className="w-4 h-4" />
                )}
                <span>{isBuildingIPA ? 'Building...' : 'Build IPA'}</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Help Text */}
      <div className="mt-6 p-4 bg-[hsl(var(--bolt-bg-secondary))] rounded-lg max-w-sm">
        <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
          How to use:
        </h3>
        <ol className="text-xs text-[hsl(var(--bolt-text-secondary))] space-y-1.5 list-decimal list-inside">
          <li>Install Expo Go on your phone</li>
          <li>Open Expo Go app</li>
          <li>Tap &quot;Scan QR code&quot;</li>
          <li>Point your camera at the QR code above</li>
          <li>Your app will load on your phone!</li>
        </ol>
      </div>
    </div>
  )
}
