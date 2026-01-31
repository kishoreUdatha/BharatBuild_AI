'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Code, Play, CheckCircle2, XCircle, Clock, ArrowLeft,
  Terminal, AlertCircle, Copy, Check, Zap, Settings,
  Plus, Trash2, ChevronDown, ChevronUp, Cpu, HardDrive
} from 'lucide-react'
import Editor from '@monaco-editor/react'
import {
  usePlayground,
  formatExecutionTime,
  formatMemoryUsage,
  getStatusColor,
  getStatusMessage,
  POPULAR_LANGUAGES,
  TestCase,
  ExecutionResult,
  TestRunResult
} from '@/hooks/usePlayground'

// Monaco editor themes
const EDITOR_THEME = 'vs-dark'

// Language to Monaco language mapping
const monacoLanguageMap: Record<string, string> = {
  python: 'python',
  python3: 'python',
  javascript: 'javascript',
  typescript: 'typescript',
  java: 'java',
  c: 'c',
  cpp: 'cpp',
  'c++': 'cpp',
  csharp: 'csharp',
  'c#': 'csharp',
  go: 'go',
  rust: 'rust',
  ruby: 'ruby',
  php: 'php',
  swift: 'swift',
  kotlin: 'kotlin',
  scala: 'scala',
  sql: 'sql',
  bash: 'shell',
  shell: 'shell',
  r: 'r',
  perl: 'perl',
  lua: 'lua',
  haskell: 'haskell',
  dart: 'dart',
}

export default function PlaygroundPage() {
  // State
  const [code, setCode] = useState('')
  const [selectedLanguage, setSelectedLanguage] = useState('python')
  const [stdin, setStdin] = useState('')
  const [activeTab, setActiveTab] = useState('output')
  const [copied, setCopied] = useState(false)
  const [testCases, setTestCases] = useState<TestCase[]>([])
  const [showTestCases, setShowTestCases] = useState(false)
  const [timeLimitSec, setTimeLimitSec] = useState(2)
  const [memoryLimitMb, setMemoryLimitMb] = useState(128)
  const [showSettings, setShowSettings] = useState(false)

  // Hook
  const {
    isRunning,
    result,
    testResult,
    error,
    languages,
    languagesLoading,
    runCode: executeCode,
    runWithTests,
    loadLanguages,
    getTemplate,
    checkHealth,
    clearResults
  } = usePlayground()

  // Load languages on mount
  useEffect(() => {
    loadLanguages()
    loadDefaultTemplate('python')
  }, [])

  // Load template for a language
  const loadDefaultTemplate = async (lang: string) => {
    const template = await getTemplate(lang)
    setCode(template)
  }

  // Handle language change
  const handleLanguageChange = async (lang: string) => {
    setSelectedLanguage(lang)
    clearResults()
    await loadDefaultTemplate(lang)
  }

  // Copy code to clipboard
  const copyCode = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Run code
  const handleRunCode = async () => {
    setActiveTab('output')
    await executeCode(code, selectedLanguage, stdin, {
      timeLimitSec,
      memoryLimitMb
    })
  }

  // Run with test cases
  const handleRunTests = async () => {
    if (testCases.length === 0) return
    setActiveTab('tests')
    await runWithTests(code, selectedLanguage, testCases, {
      timeLimitSec,
      memoryLimitMb
    })
  }

  // Add test case
  const addTestCase = () => {
    setTestCases([...testCases, { input: '', expected_output: '' }])
  }

  // Remove test case
  const removeTestCase = (index: number) => {
    setTestCases(testCases.filter((_, i) => i !== index))
  }

  // Update test case
  const updateTestCase = (index: number, field: 'input' | 'expected_output', value: string) => {
    const updated = [...testCases]
    updated[index] = { ...updated[index], [field]: value }
    setTestCases(updated)
  }

  // Get Monaco language
  const getMonacoLanguage = (lang: string): string => {
    return monacoLanguageMap[lang.toLowerCase()] || 'plaintext'
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {/* Header */}
      <header className="bg-[#12121a] border-b border-gray-800 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-gray-400 hover:text-white transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-2">
              <Code className="w-6 h-6 text-blue-500" />
              <h1 className="text-lg font-semibold text-white">Code Playground</h1>
            </div>
            <Badge variant="outline" className="text-xs border-blue-500/50 text-blue-400">
              60+ Languages
            </Badge>
          </div>

          <div className="flex items-center gap-3">
            {/* Language Selector */}
            <Select value={selectedLanguage} onValueChange={handleLanguageChange}>
              <SelectTrigger className="w-[180px] bg-[#1a1a24] border-gray-700 text-white">
                <SelectValue placeholder="Select Language" />
              </SelectTrigger>
              <SelectContent className="bg-[#1a1a24] border-gray-700">
                {POPULAR_LANGUAGES.map((lang) => (
                  <SelectItem key={lang.id} value={lang.name.toLowerCase()}>
                    <span className="flex items-center gap-2">
                      <span>{lang.icon}</span>
                      <span>{lang.name}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Settings Toggle */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSettings(!showSettings)}
              className="bg-[#1a1a24] border-gray-700 text-gray-300 hover:text-white"
            >
              <Settings className="w-4 h-4" />
            </Button>

            {/* Copy Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={copyCode}
              className="bg-[#1a1a24] border-gray-700 text-gray-300 hover:text-white"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </Button>

            {/* Run Button */}
            <Button
              onClick={handleRunCode}
              disabled={isRunning || !code.trim()}
              className="bg-green-600 hover:bg-green-700 text-white px-4"
            >
              {isRunning ? (
                <>
                  <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run
                </>
              )}
            </Button>
          </div>
        </div>
      </header>

      {/* Settings Panel */}
      {showSettings && (
        <div className="bg-[#12121a] border-b border-gray-800 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-400">Time Limit:</span>
              <Select value={timeLimitSec.toString()} onValueChange={(v) => setTimeLimitSec(parseInt(v))}>
                <SelectTrigger className="w-24 bg-[#1a1a24] border-gray-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a1a24] border-gray-700">
                  {[1, 2, 3, 5, 10].map((t) => (
                    <SelectItem key={t} value={t.toString()}>{t}s</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-400">Memory Limit:</span>
              <Select value={memoryLimitMb.toString()} onValueChange={(v) => setMemoryLimitMb(parseInt(v))}>
                <SelectTrigger className="w-28 bg-[#1a1a24] border-gray-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a1a24] border-gray-700">
                  {[64, 128, 256, 512].map((m) => (
                    <SelectItem key={m} value={m.toString()}>{m} MB</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex h-[calc(100vh-60px)]">
        {/* Code Editor - Left Panel */}
        <div className="flex-1 flex flex-col border-r border-gray-800">
          <Editor
            height="100%"
            language={getMonacoLanguage(selectedLanguage)}
            theme={EDITOR_THEME}
            value={code}
            onChange={(value) => setCode(value || '')}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              tabSize: 2,
              wordWrap: 'on',
              padding: { top: 16, bottom: 16 },
            }}
          />
        </div>

        {/* Output Panel - Right Panel */}
        <div className="w-[450px] flex flex-col bg-[#0d0d12]">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <TabsList className="bg-[#12121a] border-b border-gray-800 rounded-none p-1">
              <TabsTrigger value="output" className="data-[state=active]:bg-[#1a1a24]">
                <Terminal className="w-4 h-4 mr-2" />
                Output
              </TabsTrigger>
              <TabsTrigger value="input" className="data-[state=active]:bg-[#1a1a24]">
                Input
              </TabsTrigger>
              <TabsTrigger value="tests" className="data-[state=active]:bg-[#1a1a24]">
                Test Cases
              </TabsTrigger>
            </TabsList>

            {/* Output Tab */}
            <TabsContent value="output" className="flex-1 p-4 overflow-auto m-0">
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {result && (
                <div className="space-y-4">
                  {/* Status */}
                  <div className="flex items-center gap-2">
                    {result.is_success ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-500" />
                    )}
                    <span className={`font-medium ${getStatusColor(result.status)}`}>
                      {getStatusMessage(result.status)}
                    </span>
                  </div>

                  {/* Metrics */}
                  <div className="flex gap-4 text-sm">
                    <div className="flex items-center gap-1 text-gray-400">
                      <Cpu className="w-4 h-4" />
                      <span>{formatExecutionTime(result.time_ms)}</span>
                    </div>
                    <div className="flex items-center gap-1 text-gray-400">
                      <HardDrive className="w-4 h-4" />
                      <span>{formatMemoryUsage(result.memory_kb)}</span>
                    </div>
                  </div>

                  {/* Output */}
                  {result.stdout && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-300 mb-2">Output:</h4>
                      <pre className="bg-[#1a1a24] p-3 rounded-lg text-sm text-green-400 overflow-auto max-h-48">
                        {result.stdout}
                      </pre>
                    </div>
                  )}

                  {/* Stderr */}
                  {result.stderr && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-300 mb-2">Stderr:</h4>
                      <pre className="bg-[#1a1a24] p-3 rounded-lg text-sm text-red-400 overflow-auto max-h-48">
                        {result.stderr}
                      </pre>
                    </div>
                  )}

                  {/* Compile Output */}
                  {result.compile_output && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-300 mb-2">Compilation:</h4>
                      <pre className="bg-[#1a1a24] p-3 rounded-lg text-sm text-orange-400 overflow-auto max-h-48">
                        {result.compile_output}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {!result && !error && !isRunning && (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <Terminal className="w-12 h-12 mb-4 opacity-50" />
                  <p>Click "Run" to execute your code</p>
                </div>
              )}

              {isRunning && (
                <div className="flex flex-col items-center justify-center h-full">
                  <div className="animate-spin w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full mb-4" />
                  <p className="text-gray-400">Executing code...</p>
                </div>
              )}
            </TabsContent>

            {/* Input Tab */}
            <TabsContent value="input" className="flex-1 p-4 m-0">
              <div className="h-full flex flex-col">
                <h4 className="text-sm font-medium text-gray-300 mb-2">Standard Input (stdin):</h4>
                <Textarea
                  value={stdin}
                  onChange={(e) => setStdin(e.target.value)}
                  placeholder="Enter input for your program..."
                  className="flex-1 bg-[#1a1a24] border-gray-700 text-white font-mono resize-none"
                />
              </div>
            </TabsContent>

            {/* Test Cases Tab */}
            <TabsContent value="tests" className="flex-1 p-4 overflow-auto m-0">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-gray-300">Test Cases</h4>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={addTestCase}
                      className="bg-[#1a1a24] border-gray-700 text-gray-300"
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Add
                    </Button>
                    {testCases.length > 0 && (
                      <Button
                        size="sm"
                        onClick={handleRunTests}
                        disabled={isRunning}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        <Zap className="w-4 h-4 mr-1" />
                        Run Tests
                      </Button>
                    )}
                  </div>
                </div>

                {/* Test Case List */}
                {testCases.map((tc, index) => (
                  <Card key={index} className="bg-[#1a1a24] border-gray-700">
                    <CardContent className="p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-300">Test #{index + 1}</span>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removeTestCase(index)}
                          className="text-gray-400 hover:text-red-400 h-6 w-6 p-0"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500">Input:</label>
                        <Textarea
                          value={tc.input}
                          onChange={(e) => updateTestCase(index, 'input', e.target.value)}
                          className="bg-[#12121a] border-gray-700 text-white font-mono text-sm h-16 mt-1"
                          placeholder="Input..."
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500">Expected Output:</label>
                        <Textarea
                          value={tc.expected_output}
                          onChange={(e) => updateTestCase(index, 'expected_output', e.target.value)}
                          className="bg-[#12121a] border-gray-700 text-white font-mono text-sm h-16 mt-1"
                          placeholder="Expected output..."
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}

                {/* Test Results */}
                {testResult && (
                  <div className="space-y-3 mt-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-medium text-gray-300">Results</h4>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={testResult.all_passed ? 'default' : 'destructive'}
                          className={testResult.all_passed ? 'bg-green-600' : ''}
                        >
                          {testResult.passed_tests}/{testResult.total_tests} Passed
                        </Badge>
                        <span className="text-xs text-gray-400">
                          ({testResult.pass_percentage.toFixed(0)}%)
                        </span>
                      </div>
                    </div>

                    {testResult.results.map((r) => (
                      <Card
                        key={r.test_case_id}
                        className={`border ${r.passed ? 'bg-green-900/20 border-green-600/30' : 'bg-red-900/20 border-red-600/30'}`}
                      >
                        <CardContent className="p-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {r.passed ? (
                                <CheckCircle2 className="w-4 h-4 text-green-500" />
                              ) : (
                                <XCircle className="w-4 h-4 text-red-500" />
                              )}
                              <span className="text-sm font-medium text-gray-300">
                                Test #{r.test_case_id}
                              </span>
                            </div>
                            <span className="text-xs text-gray-400">
                              {formatExecutionTime(r.time_ms)}
                            </span>
                          </div>

                          {!r.passed && (
                            <div className="space-y-1 text-xs">
                              <div>
                                <span className="text-gray-500">Expected: </span>
                                <code className="text-green-400">{r.expected_output}</code>
                              </div>
                              <div>
                                <span className="text-gray-500">Got: </span>
                                <code className="text-red-400">{r.actual_output || '(empty)'}</code>
                              </div>
                              {r.error && (
                                <div className="text-orange-400 mt-1">{r.error}</div>
                              )}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}

                {testCases.length === 0 && !testResult && (
                  <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                    <p className="text-sm">No test cases added</p>
                    <p className="text-xs mt-1">Click "Add" to create a test case</p>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}
