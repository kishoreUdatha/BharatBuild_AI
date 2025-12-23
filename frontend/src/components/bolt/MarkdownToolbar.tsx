'use client'

import React, { useCallback } from 'react'
import {
  Bold,
  Italic,
  Strikethrough,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  CheckSquare,
  Code,
  Quote,
  Link,
  Image,
  Table,
  Minus,
  FileCode,
} from 'lucide-react'

interface MarkdownToolbarProps {
  editorRef: React.MutableRefObject<any>
  onContentChange?: (content: string) => void
}

interface ToolbarButton {
  icon: React.ReactNode
  label: string
  action: () => void
  divider?: boolean
}

export function MarkdownToolbar({ editorRef, onContentChange }: MarkdownToolbarProps) {
  // Helper to get Monaco editor instance
  const getEditor = useCallback(() => {
    return editorRef.current
  }, [editorRef])

  // Helper to insert text at cursor position
  const insertText = useCallback((text: string, selectText?: string) => {
    const editor = getEditor()
    if (!editor) return

    const selection = editor.getSelection()
    const model = editor.getModel()

    if (!selection || !model) return

    // If there's selected text and we have a selectText pattern, wrap it
    const selectedText = model.getValueInRange(selection)

    let textToInsert = text
    if (selectedText && selectText) {
      textToInsert = text.replace(selectText, selectedText)
    }

    // Insert the text
    editor.executeEdits('markdown-toolbar', [{
      range: selection,
      text: textToInsert,
      forceMoveMarkers: true
    }])

    // Focus back on editor
    editor.focus()

    // Trigger content change
    if (onContentChange) {
      onContentChange(model.getValue())
    }
  }, [getEditor, onContentChange])

  // Helper to wrap selected text with prefix/suffix
  const wrapText = useCallback((prefix: string, suffix: string = prefix) => {
    const editor = getEditor()
    if (!editor) return

    const selection = editor.getSelection()
    const model = editor.getModel()

    if (!selection || !model) return

    const selectedText = model.getValueInRange(selection)

    if (selectedText) {
      // Wrap the selected text
      insertText(`${prefix}${selectedText}${suffix}`)
    } else {
      // Insert placeholder with cursor in the middle
      const placeholder = 'text'
      insertText(`${prefix}${placeholder}${suffix}`)

      // Select the placeholder text
      const newPosition = selection.getStartPosition()
      const newSelection = {
        startLineNumber: newPosition.lineNumber,
        startColumn: newPosition.column + prefix.length,
        endLineNumber: newPosition.lineNumber,
        endColumn: newPosition.column + prefix.length + placeholder.length
      }
      editor.setSelection(newSelection)
    }

    editor.focus()
  }, [getEditor, insertText])

  // Helper to insert at line start
  const insertAtLineStart = useCallback((prefix: string) => {
    const editor = getEditor()
    if (!editor) return

    const selection = editor.getSelection()
    const model = editor.getModel()

    if (!selection || !model) return

    const lineNumber = selection.startLineNumber
    const lineContent = model.getLineContent(lineNumber)

    // Check if line already has this prefix
    if (lineContent.startsWith(prefix)) {
      // Remove the prefix
      editor.executeEdits('markdown-toolbar', [{
        range: {
          startLineNumber: lineNumber,
          startColumn: 1,
          endLineNumber: lineNumber,
          endColumn: prefix.length + 1
        },
        text: '',
        forceMoveMarkers: true
      }])
    } else {
      // Add the prefix
      editor.executeEdits('markdown-toolbar', [{
        range: {
          startLineNumber: lineNumber,
          startColumn: 1,
          endLineNumber: lineNumber,
          endColumn: 1
        },
        text: prefix,
        forceMoveMarkers: true
      }])
    }

    editor.focus()

    if (onContentChange) {
      onContentChange(model.getValue())
    }
  }, [getEditor, onContentChange])

  // Toolbar actions
  const handleBold = useCallback(() => wrapText('**'), [wrapText])
  const handleItalic = useCallback(() => wrapText('*'), [wrapText])
  const handleStrikethrough = useCallback(() => wrapText('~~'), [wrapText])

  const handleHeading1 = useCallback(() => insertAtLineStart('# '), [insertAtLineStart])
  const handleHeading2 = useCallback(() => insertAtLineStart('## '), [insertAtLineStart])
  const handleHeading3 = useCallback(() => insertAtLineStart('### '), [insertAtLineStart])

  const handleBulletList = useCallback(() => insertAtLineStart('- '), [insertAtLineStart])
  const handleNumberedList = useCallback(() => insertAtLineStart('1. '), [insertAtLineStart])
  const handleCheckbox = useCallback(() => insertAtLineStart('- [ ] '), [insertAtLineStart])

  const handleInlineCode = useCallback(() => wrapText('`'), [wrapText])
  const handleCodeBlock = useCallback(() => {
    const editor = getEditor()
    if (!editor) return

    const selection = editor.getSelection()
    const model = editor.getModel()

    if (!selection || !model) return

    const selectedText = model.getValueInRange(selection)
    const codeBlock = selectedText
      ? `\`\`\`\n${selectedText}\n\`\`\``
      : '```\ncode here\n```'

    insertText(codeBlock)
  }, [getEditor, insertText])

  const handleBlockquote = useCallback(() => insertAtLineStart('> '), [insertAtLineStart])

  const handleLink = useCallback(() => {
    const editor = getEditor()
    if (!editor) return

    const selection = editor.getSelection()
    const model = editor.getModel()

    if (!selection || !model) return

    const selectedText = model.getValueInRange(selection)

    if (selectedText) {
      insertText(`[${selectedText}](url)`)
    } else {
      insertText('[link text](url)')
    }
  }, [getEditor, insertText])

  const handleImage = useCallback(() => {
    insertText('![alt text](image-url)')
  }, [insertText])

  const handleTable = useCallback(() => {
    const tableTemplate = `| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |`
    insertText(tableTemplate)
  }, [insertText])

  const handleHorizontalRule = useCallback(() => {
    insertText('\n---\n')
  }, [insertText])

  const buttons: ToolbarButton[] = [
    { icon: <Bold className="w-4 h-4" />, label: 'Bold (Ctrl+B)', action: handleBold },
    { icon: <Italic className="w-4 h-4" />, label: 'Italic (Ctrl+I)', action: handleItalic },
    { icon: <Strikethrough className="w-4 h-4" />, label: 'Strikethrough', action: handleStrikethrough },
    { icon: <Heading1 className="w-4 h-4" />, label: 'Heading 1', action: handleHeading1, divider: true },
    { icon: <Heading2 className="w-4 h-4" />, label: 'Heading 2', action: handleHeading2 },
    { icon: <Heading3 className="w-4 h-4" />, label: 'Heading 3', action: handleHeading3 },
    { icon: <List className="w-4 h-4" />, label: 'Bullet List', action: handleBulletList, divider: true },
    { icon: <ListOrdered className="w-4 h-4" />, label: 'Numbered List', action: handleNumberedList },
    { icon: <CheckSquare className="w-4 h-4" />, label: 'Checkbox', action: handleCheckbox },
    { icon: <Code className="w-4 h-4" />, label: 'Inline Code', action: handleInlineCode, divider: true },
    { icon: <FileCode className="w-4 h-4" />, label: 'Code Block', action: handleCodeBlock },
    { icon: <Quote className="w-4 h-4" />, label: 'Blockquote', action: handleBlockquote },
    { icon: <Link className="w-4 h-4" />, label: 'Link', action: handleLink, divider: true },
    { icon: <Image className="w-4 h-4" />, label: 'Image', action: handleImage },
    { icon: <Table className="w-4 h-4" />, label: 'Table', action: handleTable },
    { icon: <Minus className="w-4 h-4" />, label: 'Horizontal Rule', action: handleHorizontalRule },
  ]

  return (
    <div className="flex items-center gap-0.5 px-2 py-1 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
      <span className="text-xs text-[hsl(var(--bolt-text-tertiary))] mr-2 font-medium">Markdown:</span>

      {buttons.map((button, index) => (
        <React.Fragment key={index}>
          {button.divider && index > 0 && (
            <div className="w-px h-5 bg-[hsl(var(--bolt-border))] mx-1" />
          )}
          <button
            onClick={button.action}
            className="p-1.5 rounded hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            title={button.label}
          >
            {button.icon}
          </button>
        </React.Fragment>
      ))}
    </div>
  )
}
