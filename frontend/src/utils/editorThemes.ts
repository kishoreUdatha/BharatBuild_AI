/**
 * Custom Monaco Editor Theme for BharatBuild AI
 * Matches Bolt.new dark theme aesthetic
 */

export const monacoTheme = {
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
