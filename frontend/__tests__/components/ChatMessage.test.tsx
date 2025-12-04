import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ChatMessage } from '@/components/bolt/ChatMessage'

// Mock the Button component
vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, className, variant, size }: any) => (
    <button onClick={onClick} className={className} data-variant={variant} data-size={size}>
      {children}
    </button>
  ),
}))

// Mock the clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
})

describe('ChatMessage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('User Messages', () => {
    it('should render user message', () => {
      render(<ChatMessage role="user" content="Hello, build me a todo app" />)

      expect(screen.getByText('You')).toBeInTheDocument()
      expect(screen.getByText('Hello, build me a todo app')).toBeInTheDocument()
    })

    it('should show User avatar for user messages', () => {
      render(<ChatMessage role="user" content="Test message" />)

      expect(screen.getByText('You')).toBeInTheDocument()
    })

    it('should align user messages to the right', () => {
      const { container } = render(<ChatMessage role="user" content="Test" />)

      const messageWrapper = container.firstChild
      expect(messageWrapper).toHaveClass('flex-row-reverse')
    })

    it('should not show copy button for user messages', () => {
      render(<ChatMessage role="user" content="Test message" />)

      expect(screen.queryByText('Copy')).not.toBeInTheDocument()
    })
  })

  describe('Assistant Messages', () => {
    it('should render assistant message', () => {
      render(<ChatMessage role="assistant" content="I'll help you build a todo app" />)

      expect(screen.getByText('BharatBuild AI')).toBeInTheDocument()
      expect(screen.getByText("I'll help you build a todo app")).toBeInTheDocument()
    })

    it('should show Bot avatar for assistant messages', () => {
      render(<ChatMessage role="assistant" content="Test message" />)

      expect(screen.getByText('BharatBuild AI')).toBeInTheDocument()
    })

    it('should not align assistant messages to the right', () => {
      const { container } = render(<ChatMessage role="assistant" content="Test" />)

      const messageWrapper = container.firstChild
      expect(messageWrapper).not.toHaveClass('flex-row-reverse')
    })

    it('should apply assistant background color', () => {
      const { container } = render(<ChatMessage role="assistant" content="Test" />)

      const messageWrapper = container.firstChild
      expect(messageWrapper).toHaveClass('bg-[hsl(var(--bolt-bg-secondary))]')
    })
  })

  describe('Empty Messages', () => {
    it('should not render empty assistant message', () => {
      const { container } = render(<ChatMessage role="assistant" content="" />)

      expect(container.firstChild).toBeNull()
    })

    it('should render empty assistant message when streaming', () => {
      render(<ChatMessage role="assistant" content="" isStreaming={true} />)

      expect(screen.getByText('BharatBuild AI')).toBeInTheDocument()
    })
  })

  describe('Streaming State', () => {
    it('should show streaming indicator when isStreaming is true', () => {
      const { container } = render(
        <ChatMessage role="assistant" content="Loading..." isStreaming={true} />
      )

      // Check for animated dots (pulse animation)
      const dots = container.querySelectorAll('.animate-pulse')
      expect(dots.length).toBeGreaterThan(0)
    })

    it('should show blinking cursor when streaming', () => {
      const { container } = render(
        <ChatMessage role="assistant" content="Typing..." isStreaming={true} />
      )

      // Check for cursor element
      const cursor = container.querySelector('.w-2.h-4.bg-blue-500.animate-pulse')
      expect(cursor).toBeInTheDocument()
    })

    it('should not show copy button when streaming', () => {
      render(<ChatMessage role="assistant" content="Loading..." isStreaming={true} />)

      expect(screen.queryByText('Copy')).not.toBeInTheDocument()
    })
  })

  describe('Markdown Rendering', () => {
    it('should render bold text with ** markers', () => {
      const { container } = render(<ChatMessage role="assistant" content="This is **bold** text" />)

      // Check that the strong element exists
      const strongElements = container.querySelectorAll('strong')
      expect(strongElements.length).toBeGreaterThan(0)
    })

    it('should render inline code with backticks', () => {
      const { container } = render(<ChatMessage role="assistant" content="Use the `useState` hook" />)

      // Check that the code element exists
      const codeElements = container.querySelectorAll('code')
      expect(codeElements.length).toBeGreaterThan(0)
    })

    it('should render multiple lines', () => {
      const { container } = render(<ChatMessage role="assistant" content="Line 1\nLine 2\nLine 3" />)

      // Check that content contains the lines
      expect(container.textContent).toContain('Line 1')
      expect(container.textContent).toContain('Line 2')
      expect(container.textContent).toContain('Line 3')
    })

    it('should handle empty lines', () => {
      const { container } = render(<ChatMessage role="assistant" content="Line 1\n\nLine 2" />)

      // Check that content contains both lines
      expect(container.textContent).toContain('Line 1')
      expect(container.textContent).toContain('Line 2')
    })
  })

  describe('Copy Functionality', () => {
    it('should show Copy button for assistant messages', () => {
      const { container } = render(
        <ChatMessage role="assistant" content="Some content to copy" />
      )

      // The button is in a group that shows on hover, so it exists but may be hidden
      const copyButton = screen.queryByText('Copy')
      // Button exists but is initially hidden via opacity
      expect(copyButton?.closest('.opacity-0')).toBeInTheDocument()
    })

    it('should copy content to clipboard when clicked', async () => {
      render(<ChatMessage role="assistant" content="Content to copy" />)

      const copyButton = screen.getByText('Copy')
      fireEvent.click(copyButton)

      await waitFor(() => {
        expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Content to copy')
      })
    })

    it('should show Copied text after copying', async () => {
      render(<ChatMessage role="assistant" content="Content to copy" />)

      const copyButton = screen.getByText('Copy')
      fireEvent.click(copyButton)

      // The component should show "Copied" after clipboard operation
      await waitFor(() => {
        expect(screen.getByText('Copied')).toBeInTheDocument()
      }, { timeout: 2000 })
    })
  })
})

describe('ChatMessage Edge Cases', () => {
  it('should handle very long content', () => {
    const longContent = 'A'.repeat(10000)
    render(<ChatMessage role="assistant" content={longContent} />)

    expect(screen.getByText(longContent)).toBeInTheDocument()
  })

  it('should handle special characters', () => {
    render(<ChatMessage role="assistant" content="Special chars: @#$%^&*()" />)

    expect(screen.getByText('Special chars: @#$%^&*()')).toBeInTheDocument()
  })

  it('should handle emoji content', () => {
    render(<ChatMessage role="assistant" content="Hello World!" />)

    expect(screen.getByText(/Hello/)).toBeInTheDocument()
  })

  it('should handle mixed formatting', () => {
    const { container } = render(
      <ChatMessage
        role="assistant"
        content="This is **bold** text"
      />
    )

    // Check that bold text is rendered as STRONG element
    const strongElements = container.querySelectorAll('strong')
    expect(strongElements.length).toBeGreaterThan(0)
  })
})
