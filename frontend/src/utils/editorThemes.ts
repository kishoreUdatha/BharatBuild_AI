/**
 * Custom Monaco Editor Themes for BharatBuild AI
 * Dark and Light theme variants
 */

// Dark Theme - Matches Bolt.new dark theme aesthetic
export const monacoThemeDark = {
  base: 'vs-dark' as const,
  inherit: true,
  rules: [
    // Comments
    { token: 'comment', foreground: '6b7280', fontStyle: 'italic' },

    // Keywords
    { token: 'keyword', foreground: 'c084fc' },
    { token: 'keyword.control', foreground: 'c084fc' },

    // Strings
    { token: 'string', foreground: '4ade80' },
    { token: 'string.escape', foreground: '86efac' },

    // Numbers
    { token: 'number', foreground: 'facc15' },

    // Functions
    { token: 'function', foreground: '60a5fa' },
    { token: 'identifier.function', foreground: '60a5fa' },

    // Variables
    { token: 'variable', foreground: 'e4e6eb' },
    { token: 'variable.parameter', foreground: 'fca5a5' },

    // Types
    { token: 'type', foreground: '22d3ee' },
    { token: 'type.identifier', foreground: '22d3ee' },

    // Constants
    { token: 'constant', foreground: 'facc15' },

    // Operators
    { token: 'operator', foreground: 'c084fc' },
    { token: 'delimiter', foreground: '9ca3af' },

    // Tags (HTML/JSX)
    { token: 'tag', foreground: 'c084fc' },
    { token: 'tag.attribute', foreground: '60a5fa' },

    // Meta
    { token: 'meta', foreground: '9ca3af' },

    // Invalid
    { token: 'invalid', foreground: 'f87171', fontStyle: 'bold' },
  ],
  colors: {
    // Editor background
    'editor.background': '#1a1d23',
    'editor.foreground': '#e4e6eb',

    // Line highlighting
    'editor.lineHighlightBackground': '#22252b',
    'editor.lineHighlightBorder': '#2d3139',

    // Selection
    'editor.selectionBackground': '#0099ff33',
    'editor.selectionHighlightBackground': '#0099ff22',
    'editor.inactiveSelectionBackground': '#0099ff1a',

    // Cursor
    'editorCursor.foreground': '#0099ff',

    // Line numbers
    'editorLineNumber.foreground': '#6b7280',
    'editorLineNumber.activeForeground': '#9ca3af',

    // Gutter
    'editorGutter.background': '#1a1d23',
    'editorGutter.addedBackground': '#4ade80',
    'editorGutter.modifiedBackground': '#60a5fa',
    'editorGutter.deletedBackground': '#f87171',

    // Whitespace
    'editorWhitespace.foreground': '#374151',

    // Indentation guides
    'editorIndentGuide.background': '#2d3139',
    'editorIndentGuide.activeBackground': '#4b5563',

    // Brackets
    'editorBracketMatch.background': '#0099ff22',
    'editorBracketMatch.border': '#0099ff',

    // Scrollbar
    'scrollbar.shadow': '#00000066',
    'scrollbarSlider.background': '#4b556344',
    'scrollbarSlider.hoverBackground': '#4b556366',
    'scrollbarSlider.activeBackground': '#4b556388',

    // Widget (autocomplete, hover, etc.)
    'editorWidget.background': '#22252b',
    'editorWidget.border': '#374151',
    'editorSuggestWidget.background': '#22252b',
    'editorSuggestWidget.border': '#374151',
    'editorSuggestWidget.selectedBackground': '#0099ff33',
    'editorHoverWidget.background': '#22252b',
    'editorHoverWidget.border': '#374151',

    // Find/Replace
    'editor.findMatchBackground': '#facc1544',
    'editor.findMatchHighlightBackground': '#facc1522',
    'editor.findRangeHighlightBackground': '#0099ff22',

    // Error/Warning squiggles
    'editorError.foreground': '#f87171',
    'editorWarning.foreground': '#facc15',
    'editorInfo.foreground': '#60a5fa',

    // Minimap
    'minimap.background': '#1a1d23',
    'minimap.selectionHighlight': '#0099ff44',
    'minimap.findMatchHighlight': '#facc1544',

    // Overview ruler (scrollbar gutter)
    'editorOverviewRuler.border': '#2d3139',
    'editorOverviewRuler.errorForeground': '#f87171',
    'editorOverviewRuler.warningForeground': '#facc15',
    'editorOverviewRuler.infoForeground': '#60a5fa',
  }
}

// Light Theme - Clean and bright
export const monacoThemeLight = {
  base: 'vs' as const,
  inherit: true,
  rules: [
    // Comments
    { token: 'comment', foreground: '6b7280', fontStyle: 'italic' },

    // Keywords
    { token: 'keyword', foreground: '7c3aed' },
    { token: 'keyword.control', foreground: '7c3aed' },

    // Strings
    { token: 'string', foreground: '16a34a' },
    { token: 'string.escape', foreground: '22c55e' },

    // Numbers
    { token: 'number', foreground: 'ca8a04' },

    // Functions
    { token: 'function', foreground: '2563eb' },
    { token: 'identifier.function', foreground: '2563eb' },

    // Variables
    { token: 'variable', foreground: '1f2937' },
    { token: 'variable.parameter', foreground: 'dc2626' },

    // Types
    { token: 'type', foreground: '0891b2' },
    { token: 'type.identifier', foreground: '0891b2' },

    // Constants
    { token: 'constant', foreground: 'ca8a04' },

    // Operators
    { token: 'operator', foreground: '7c3aed' },
    { token: 'delimiter', foreground: '6b7280' },

    // Tags (HTML/JSX)
    { token: 'tag', foreground: '7c3aed' },
    { token: 'tag.attribute', foreground: '2563eb' },

    // Meta
    { token: 'meta', foreground: '6b7280' },

    // Invalid
    { token: 'invalid', foreground: 'dc2626', fontStyle: 'bold' },
  ],
  colors: {
    // Editor background
    'editor.background': '#ffffff',
    'editor.foreground': '#1f2937',

    // Line highlighting
    'editor.lineHighlightBackground': '#f3f4f6',
    'editor.lineHighlightBorder': '#e5e7eb',

    // Selection
    'editor.selectionBackground': '#3b82f633',
    'editor.selectionHighlightBackground': '#3b82f622',
    'editor.inactiveSelectionBackground': '#3b82f61a',

    // Cursor
    'editorCursor.foreground': '#3b82f6',

    // Line numbers
    'editorLineNumber.foreground': '#9ca3af',
    'editorLineNumber.activeForeground': '#6b7280',

    // Gutter
    'editorGutter.background': '#ffffff',
    'editorGutter.addedBackground': '#22c55e',
    'editorGutter.modifiedBackground': '#3b82f6',
    'editorGutter.deletedBackground': '#ef4444',

    // Whitespace
    'editorWhitespace.foreground': '#e5e7eb',

    // Indentation guides
    'editorIndentGuide.background': '#e5e7eb',
    'editorIndentGuide.activeBackground': '#d1d5db',

    // Brackets
    'editorBracketMatch.background': '#3b82f622',
    'editorBracketMatch.border': '#3b82f6',

    // Scrollbar
    'scrollbar.shadow': '#00000011',
    'scrollbarSlider.background': '#d1d5db66',
    'scrollbarSlider.hoverBackground': '#d1d5db99',
    'scrollbarSlider.activeBackground': '#d1d5dbcc',

    // Widget (autocomplete, hover, etc.)
    'editorWidget.background': '#ffffff',
    'editorWidget.border': '#e5e7eb',
    'editorSuggestWidget.background': '#ffffff',
    'editorSuggestWidget.border': '#e5e7eb',
    'editorSuggestWidget.selectedBackground': '#3b82f622',
    'editorHoverWidget.background': '#ffffff',
    'editorHoverWidget.border': '#e5e7eb',

    // Find/Replace
    'editor.findMatchBackground': '#fbbf2444',
    'editor.findMatchHighlightBackground': '#fbbf2422',
    'editor.findRangeHighlightBackground': '#3b82f622',

    // Error/Warning squiggles
    'editorError.foreground': '#ef4444',
    'editorWarning.foreground': '#f59e0b',
    'editorInfo.foreground': '#3b82f6',

    // Minimap
    'minimap.background': '#ffffff',
    'minimap.selectionHighlight': '#3b82f644',
    'minimap.findMatchHighlight': '#fbbf2444',

    // Overview ruler (scrollbar gutter)
    'editorOverviewRuler.border': '#e5e7eb',
    'editorOverviewRuler.errorForeground': '#ef4444',
    'editorOverviewRuler.warningForeground': '#f59e0b',
    'editorOverviewRuler.infoForeground': '#3b82f6',
  }
}

// Legacy export for backward compatibility
export const monacoTheme = monacoThemeDark
