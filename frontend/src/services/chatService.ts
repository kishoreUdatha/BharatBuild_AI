/**
 * Chat Service - Real conversational AI support
 *
 * This service provides real-time conversational AI capabilities
 * using Claude API for natural conversations, explanations, and help.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  message: string
  conversation_history?: ChatMessage[]
  context?: {
    project_id?: string
    current_file?: string
    has_project?: boolean
  }
}

export interface ChatResponse {
  success: boolean
  response: string
  intent?: string
}

// Error detection patterns - detects pasted error messages
const ERROR_PATTERNS = [
  // JavaScript/TypeScript errors
  /TypeError:/i,
  /ReferenceError:/i,
  /SyntaxError:/i,
  /RangeError:/i,
  /URIError:/i,
  /EvalError:/i,

  // Node.js/npm errors
  /Cannot find module/i,
  /Module not found/i,
  /npm ERR!/i,
  /ENOENT/i,
  /EACCES/i,
  /EPERM/i,

  // Build errors
  /failed to compile/i,
  /Build failed/i,
  /Compilation failed/i,
  /error TS\d+/i,  // TypeScript errors
  /error\[E\d+\]/i,  // Rust errors

  // Python errors
  /Traceback \(most recent call last\)/i,
  /IndentationError/i,
  /ImportError/i,
  /ModuleNotFoundError/i,
  /NameError/i,
  /AttributeError/i,
  /KeyError/i,
  /ValueError/i,
  /ZeroDivisionError/i,

  // Stack trace patterns
  /at .+:\d+:\d+/,  // JavaScript stack trace
  /File ".+", line \d+/,  // Python stack trace
  /at .+\(.+:\d+\)/,  // Alternative JS stack trace

  // General error indicators
  /\berror\b.*:/i,
  /\bfailed\b/i,
  /\bexception\b/i,
  /\bcrash/i,
  /FATAL/i,
  /CRITICAL/i,
]

/**
 * Check if a message contains pasted error messages
 */
export function detectPastedError(content: string): boolean {
  // Must have minimum length to be an error
  if (content.length < 20) return false

  // Check against error patterns
  for (const pattern of ERROR_PATTERNS) {
    if (pattern.test(content)) {
      return true
    }
  }

  // Check for multiple line numbers (common in stack traces)
  const lineNumberMatches = content.match(/:\d+/g)
  if (lineNumberMatches && lineNumberMatches.length >= 2) {
    return true
  }

  return false
}

/**
 * Extract error details from pasted error message
 */
export function extractErrorDetails(content: string): {
  errorType: string
  message: string
  file?: string
  line?: number
  stack?: string
} {
  let errorType = 'Unknown Error'
  let message = content
  let file: string | undefined
  let line: number | undefined
  let stack: string | undefined

  // Try to extract error type
  const errorTypeMatch = content.match(/(TypeError|ReferenceError|SyntaxError|Error|Exception):/i)
  if (errorTypeMatch) {
    errorType = errorTypeMatch[1]
  }

  // Try to extract file and line
  const locationMatch = content.match(/(?:at\s+)?([^\s:]+):(\d+)(?::\d+)?/)
  if (locationMatch) {
    file = locationMatch[1]
    line = parseInt(locationMatch[2], 10)
  }

  // Python style
  const pythonMatch = content.match(/File "([^"]+)", line (\d+)/)
  if (pythonMatch) {
    file = pythonMatch[1]
    line = parseInt(pythonMatch[2], 10)
  }

  // Extract stack trace
  const stackMatch = content.match(/((?:at .+\n?)+)/m)
  if (stackMatch) {
    stack = stackMatch[1]
  }

  return { errorType, message, file, line, stack }
}

/**
 * Get authentication headers
 */
function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  }
}

/**
 * Send a chat message and get AI response
 */
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  try {
    const response = await fetch(`${API_URL}/chat/message`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      // If API fails, return a friendly fallback
      return {
        success: false,
        response: getFallbackResponse(request.message)
      }
    }

    return await response.json()
  } catch (error) {
    console.error('[ChatService] Error:', error)
    return {
      success: false,
      response: getFallbackResponse(request.message)
    }
  }
}

/**
 * Stream a chat response for real-time display
 */
export async function streamChatMessage(
  request: ChatRequest,
  onChunk: (text: string) => void,
  onComplete: () => void,
  onError: (error: string) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_URL}/chat/stream`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'chunk' && data.content) {
              onChunk(data.content)
            } else if (data.type === 'done') {
              onComplete()
              return
            } else if (data.type === 'error') {
              onError(data.message)
              return
            }
          } catch (e) {
            // Ignore parse errors for partial chunks
          }
        }
      }
    }

    onComplete()
  } catch (error: any) {
    console.error('[ChatService] Stream error:', error)
    onError(error.message || 'Stream failed')
  }
}

/**
 * Fallback response when API is unavailable
 */
function getFallbackResponse(message: string): string {
  const normalizedMessage = message.toLowerCase().trim()

  // Greetings
  if (/^(hi|hello|hey|hola|namaste)/i.test(normalizedMessage)) {
    return `Hello! 👋 I'm **BharatBuild AI**, your AI-powered development assistant.

I can help you:
- **Build** complete web applications
- **Fix** code errors automatically
- **Explain** programming concepts
- **Generate** documentation

What would you like to create today?`
  }

  // Help request
  if (/help|what can you do/i.test(normalizedMessage)) {
    return `## What I Can Do

**🚀 Project Generation**
- "Create a React dashboard with charts"
- "Build an e-commerce site with Next.js"

**🔧 Error Fixing**
- Paste any error message and I'll fix it
- "Fix the blank page issue"

**📚 Explanations**
- "Explain React hooks"
- "How does async/await work?"

**📄 Documentation**
- "Generate README for my project"
- "Create API documentation"

Just describe what you need!`
  }

  // Thanks
  if (/thanks|thank you/i.test(normalizedMessage)) {
    return `You're welcome! 😊

Is there anything else I can help you with? Feel free to:
- Ask questions about your code
- Request new features
- Get explanations on any topic`
  }

  // Default
  return `I'm here to help! You can:

1. **Build something**: "Create a todo app with React"
2. **Fix errors**: Paste any error message
3. **Ask questions**: "How do I use useState?"
4. **Get documentation**: "Generate README"

What would you like to do?`
}

export default {
  sendChatMessage,
  streamChatMessage,
  detectPastedError,
  extractErrorDetails
}
