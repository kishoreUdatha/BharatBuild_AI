import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from '@/components/bolt/ChatInput'

// Mock the Button component
vi.mock('@/components/ui/button', () => ({
  Button: ({ children, disabled, type, onClick, className }: any) => (
    <button type={type} disabled={disabled} onClick={onClick} className={className}>
      {children}
    </button>
  ),
}))

describe('ChatInput Component', () => {
  const mockOnSend = vi.fn()

  beforeEach(() => {
    mockOnSend.mockClear()
  })

  it('should render with default placeholder', () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project/i)
    expect(textarea).toBeInTheDocument()
  })

  it('should render with custom placeholder', () => {
    render(<ChatInput onSend={mockOnSend} placeholder="Custom placeholder" />)

    const textarea = screen.getByPlaceholderText('Custom placeholder')
    expect(textarea).toBeInTheDocument()
  })

  it('should update input value on change', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project/i)
    await userEvent.type(textarea, 'Build a todo app')

    expect(textarea).toHaveValue('Build a todo app')
  })

  it('should call onSend when form is submitted', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project/i)
    await userEvent.type(textarea, 'Build a todo app')

    const form = textarea.closest('form')
    fireEvent.submit(form!)

    expect(mockOnSend).toHaveBeenCalledWith('Build a todo app')
  })

  it('should clear input after submission', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project/i)
    await userEvent.type(textarea, 'Build a todo app')

    const form = textarea.closest('form')
    fireEvent.submit(form!)

    expect(textarea).toHaveValue('')
  })

  it('should not submit empty message', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project/i)
    const form = textarea.closest('form')
    fireEvent.submit(form!)

    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('should not submit whitespace-only message', async () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/describe your project/i)
    await userEvent.type(textarea, '   ')

    const form = textarea.closest('form')
    fireEvent.submit(form!)

    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('should disable input when loading', () => {
    render(<ChatInput onSend={mockOnSend} isLoading={true} />)

    const textarea = screen.getByPlaceholderText(/describe your project/i)
    expect(textarea).toBeDisabled()
  })

  it('should not submit when loading', async () => {
    render(<ChatInput onSend={mockOnSend} isLoading={true} />)

    const textarea = screen.getByPlaceholderText(/describe your project/i)
    fireEvent.change(textarea, { target: { value: 'Build a todo app' } })

    const form = textarea.closest('form')
    fireEvent.submit(form!)

    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('should show Ready status indicator', () => {
    render(<ChatInput onSend={mockOnSend} />)

    expect(screen.getByText('Ready')).toBeInTheDocument()
  })

  it('should show helper text for keyboard shortcuts', () => {
    render(<ChatInput onSend={mockOnSend} />)

    expect(screen.getByText(/press enter to send/i)).toBeInTheDocument()
  })
})
