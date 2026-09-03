'use client'

import { NotBuiltYet, PageShell } from '@/components/faculty/PageShell'

export default function AiAssistantPage() {
  return (
    <PageShell title="AI Assistant" subtitle="Ask questions about your sections, batches and reviews">
      <NotBuiltYet
        what="The AI Assistant"
        needs="This needs an endpoint that puts the faculty data in front of a model. Note the backend currently logs 'Your credit balance is too low to access the Anthropic API' on startup, so any AI feature will fail until that account has credits. The dashboard's AI Insight line is computed in plain Python, not by a model."
      />
    </PageShell>
  )
}
