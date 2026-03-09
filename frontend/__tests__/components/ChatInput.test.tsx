import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from '@/components/bolt/ChatInput'

describe('ChatInput Component', () => {
  const mockOnSend = vi.fn()

  beforeEach(() => {
    mockOnSend.mockClear()
  })

  it('should render with default placeholder', () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project idea/i)
    expect(textarea).toBeInTheDocument()
  })

  it('should render with custom placeholder', () => {
    render(<ChatInput onSend={mockOnSend} placeholder="Custom placeholder" />)

    const textarea = screen.getByPlaceholderText('Custom placeholder')
    expect(textarea).toBeInTheDocument()
  })

  it('should update input value on change', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project idea/i)
    await userEvent.type(textarea, 'Build a todo app')

    expect(textarea).toHaveValue('Build a todo app')
  })

  it('should call onSend when Enter key is pressed', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project idea/i)
    await userEvent.type(textarea, 'Build a todo app')
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' })

    // onSend is called with (message, attachedFileContent) - undefined when no file attached
    expect(mockOnSend).toHaveBeenCalledWith('Build a todo app', undefined)
  })

  it('should clear input after submission', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project idea/i)
    await userEvent.type(textarea, 'Build a todo app')
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' })

    expect(textarea).toHaveValue('')
  })

  it('should not submit empty message', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project idea/i)
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' })

    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('should not submit whitespace-only message', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project idea/i)
    await userEvent.type(textarea, '   ')
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' })

    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('should disable input when loading', () => {
    render(<ChatInput onSend={mockOnSend} isLoading={true} />)

    const textarea = screen.getByPlaceholderText(/describe your project idea/i)
    expect(textarea).toBeDisabled()
  })

  it('should not submit when loading', async () => {
    render(<ChatInput onSend={mockOnSend} isLoading={true} />)

    const textarea = screen.getByPlaceholderText(/describe your project idea/i)
    fireEvent.change(textarea, { target: { value: 'Build a todo app' } })
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' })

    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('should show helper text for keyboard shortcuts', () => {
    render(<ChatInput onSend={mockOnSend} />)

    // Text is split across elements with <kbd> tags
    expect(screen.getByText('Enter')).toBeInTheDocument()
    expect(screen.getByText(/to send/)).toBeInTheDocument()
    expect(screen.getByText('Shift + Enter')).toBeInTheDocument()
    expect(screen.getByText(/for new line/)).toBeInTheDocument()
  })

  it('should show loading indicator when generating', () => {
    render(<ChatInput onSend={mockOnSend} isLoading={true} />)

    expect(screen.getByText(/Generating/)).toBeInTheDocument()
  })

  it('should allow new line with Shift+Enter', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project idea/i)
    await userEvent.type(textarea, 'Line 1')
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: true })

    // Shift+Enter should not submit
    expect(mockOnSend).not.toHaveBeenCalled()
  })
})
