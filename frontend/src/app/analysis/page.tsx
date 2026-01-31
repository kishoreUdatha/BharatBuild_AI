'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  FileText, Shield, Brain, Upload, CheckCircle2, AlertTriangle,
  XCircle, Loader2, Copy, FileSearch, Lightbulb, BookOpen,
  ArrowRight, RefreshCw, Download, Eye, Target, Sparkles
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface PlagiarismResult {
  overall_score: number
  original_percentage: number
  plagiarized_percentage: number
  sources_found: Array<{ source: string; matched_text: string; similarity: number }>
  highlighted_sections: Array<{ text: string; type: string; risk: string }>
  recommendations: string[]
  status: string
}

interface AIDetectionResult {
  ai_probability: number
  human_probability: number
  confidence: number
  analysis: {
    sentence_count: number
    avg_sentence_length: number
    vocabulary_richness: number
    ai_patterns_found: number
    word_count: number
  }
  verdict: string
  recommendations: string[]
}

interface IEEEAnalysisResult {
  title: string
  authors: string[]
  abstract: string
  keywords: string[]
  sections: Array<{ name: string; content: string; word_count: number }>
  methodology: string
  findings: string[]
  references_count: number
  suggested_next_steps: string[]
  research_gaps: string[]
  implementation_ideas: string[]
  word_count: number
}

interface APIStatus {
  copyscape: { enabled: boolean; status: string }
  gptzero: { enabled: boolean; status: string }
}

export default function ContentAnalysisPage() {
  const [activeTab, setActiveTab] = useState('plagiarism')
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [apiStatus, setApiStatus] = useState<APIStatus | null>(null)

  // Results
  const [plagiarismResult, setPlagiarismResult] = useState<PlagiarismResult | null>(null)
  const [aiResult, setAIResult] = useState<AIDetectionResult | null>(null)
  const [ieeeResult, setIEEEResult] = useState<IEEEAnalysisResult | null>(null)

  // Fetch API status on mount
  useState(() => {
    fetch(`${API_URL}/analysis/status`)
      .then(res => res.json())
      .then(data => setApiStatus(data))
      .catch(() => {})
  })

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token')
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }

  const checkPlagiarism = async () => {
    if (!text.trim() || text.length < 50) {
      setError('Please enter at least 50 characters')
      return
    }

    setLoading(true)
    setError('')
    setPlagiarismResult(null)

    try {
      // Use test endpoint (no auth required) for development
      const response = await fetch(`${API_URL}/analysis/plagiarism/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, check_type: 'full' })
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to check plagiarism')
      }

      const result = await response.json()
      setPlagiarismResult(result)
    } catch (err: any) {
      setError(err.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const checkAIContent = async () => {
    if (!text.trim() || text.length < 100) {
      setError('Please enter at least 100 characters')
      return
    }

    setLoading(true)
    setError('')
    setAIResult(null)

    try {
      // Use test endpoint (no auth required) for development
      const response = await fetch(`${API_URL}/analysis/ai-detection/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to check AI content')
      }

      const result = await response.json()
      setAIResult(result)
    } catch (err: any) {
      setError(err.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const analyzeIEEEPaper = async () => {
    if (!text.trim() || text.length < 500) {
      setError('Please enter at least 500 characters (paste paper content)')
      return
    }

    setLoading(true)
    setError('')
    setIEEEResult(null)

    try {
      const formData = new FormData()
      formData.append('text', text)

      // Use test endpoint (no auth required) for development
      const response = await fetch(`${API_URL}/analysis/ieee-paper/test`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to analyze paper')
      }

      const result = await response.json()
      setIEEEResult(result)
    } catch (err: any) {
      setError(err.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass': return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'warning': return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
      case 'fail': return 'bg-red-500/20 text-red-400 border-red-500/30'
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30'
    }
  }

  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'human': return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'mixed': return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
      case 'ai': return 'bg-red-500/20 text-red-400 border-red-500/30'
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30'
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/30 rounded-full px-4 py-2 mb-4">
            <Sparkles className="h-4 w-4 text-cyan-400" />
            <span className="text-cyan-400 text-sm font-medium">Content Analysis Tools</span>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            Plagiarism & AI Detection
          </h1>
          <p className="text-slate-400">
            Check your content for originality and AI-generated text
          </p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 bg-slate-900 border border-slate-800 p-1">
            <TabsTrigger
              value="plagiarism"
              className="data-[state=active]:bg-cyan-500 data-[state=active]:text-white"
            >
              <Shield className="h-4 w-4 mr-2" />
              Plagiarism Check
            </TabsTrigger>
            <TabsTrigger
              value="ai-detection"
              className="data-[state=active]:bg-purple-500 data-[state=active]:text-white"
            >
              <Brain className="h-4 w-4 mr-2" />
              AI Detection
            </TabsTrigger>
            <TabsTrigger
              value="ieee-paper"
              className="data-[state=active]:bg-amber-500 data-[state=active]:text-white"
            >
              <FileSearch className="h-4 w-4 mr-2" />
              IEEE Paper Analysis
            </TabsTrigger>
          </TabsList>

          {/* Plagiarism Check Tab */}
          <TabsContent value="plagiarism" className="space-y-6">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Shield className="h-5 w-5 text-cyan-400" />
                  Plagiarism Checker
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Paste your text here to check for plagiarism (minimum 50 characters)..."
                  rows={10}
                  className="bg-slate-800 border-slate-700 text-white resize-none"
                />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">
                    {text.length} characters | {text.split(/\s+/).filter(Boolean).length} words
                  </span>
                  <Button
                    onClick={checkPlagiarism}
                    disabled={loading || text.length < 50}
                    className="bg-cyan-500 hover:bg-cyan-600"
                  >
                    {loading ? (
                      <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Checking...</>
                    ) : (
                      <><Shield className="h-4 w-4 mr-2" /> Check Plagiarism</>
                    )}
                  </Button>
                </div>

                {error && (
                  <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
                    <p className="text-red-400 text-sm">{error}</p>
                  </div>
                )}

                {plagiarismResult && (
                  <div className="space-y-4 pt-4 border-t border-slate-800">
                    {/* Score Card */}
                    <div className="grid grid-cols-3 gap-4">
                      <Card className="bg-slate-800 border-slate-700">
                        <CardContent className="p-4 text-center">
                          <div className={`text-3xl font-bold ${
                            plagiarismResult.original_percentage >= 90 ? 'text-green-400' :
                            plagiarismResult.original_percentage >= 75 ? 'text-amber-400' : 'text-red-400'
                          }`}>
                            {plagiarismResult.original_percentage.toFixed(1)}%
                          </div>
                          <p className="text-slate-400 text-sm">Original Content</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-slate-800 border-slate-700">
                        <CardContent className="p-4 text-center">
                          <div className={`text-3xl font-bold ${
                            plagiarismResult.plagiarized_percentage < 10 ? 'text-green-400' :
                            plagiarismResult.plagiarized_percentage < 25 ? 'text-amber-400' : 'text-red-400'
                          }`}>
                            {plagiarismResult.plagiarized_percentage.toFixed(1)}%
                          </div>
                          <p className="text-slate-400 text-sm">Similarity Found</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-slate-800 border-slate-700">
                        <CardContent className="p-4 text-center">
                          <Badge className={getStatusColor(plagiarismResult.status)}>
                            {plagiarismResult.status === 'pass' && <CheckCircle2 className="h-4 w-4 mr-1" />}
                            {plagiarismResult.status === 'warning' && <AlertTriangle className="h-4 w-4 mr-1" />}
                            {plagiarismResult.status === 'fail' && <XCircle className="h-4 w-4 mr-1" />}
                            {plagiarismResult.status.toUpperCase()}
                          </Badge>
                          <p className="text-slate-400 text-sm mt-2">Status</p>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Progress Bar */}
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-green-400">Original: {plagiarismResult.original_percentage.toFixed(1)}%</span>
                        <span className="text-red-400">Similar: {plagiarismResult.plagiarized_percentage.toFixed(1)}%</span>
                      </div>
                      <div className="h-4 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-green-500 to-green-400"
                          style={{ width: `${plagiarismResult.original_percentage}%` }}
                        />
                      </div>
                    </div>

                    {/* Recommendations */}
                    <Card className="bg-slate-800/50 border-slate-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-white text-sm flex items-center gap-2">
                          <Lightbulb className="h-4 w-4 text-amber-400" />
                          Recommendations
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {plagiarismResult.recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                              <ArrowRight className="h-4 w-4 text-cyan-400 mt-0.5 flex-shrink-0" />
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI Detection Tab */}
          <TabsContent value="ai-detection" className="space-y-6">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Brain className="h-5 w-5 text-purple-400" />
                  AI Content Detector
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Paste your text here to check for AI-generated content (minimum 100 characters)..."
                  rows={10}
                  className="bg-slate-800 border-slate-700 text-white resize-none"
                />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">
                    {text.length} characters | {text.split(/\s+/).filter(Boolean).length} words
                  </span>
                  <Button
                    onClick={checkAIContent}
                    disabled={loading || text.length < 100}
                    className="bg-purple-500 hover:bg-purple-600"
                  >
                    {loading ? (
                      <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Analyzing...</>
                    ) : (
                      <><Brain className="h-4 w-4 mr-2" /> Detect AI Content</>
                    )}
                  </Button>
                </div>

                {error && (
                  <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
                    <p className="text-red-400 text-sm">{error}</p>
                  </div>
                )}

                {aiResult && (
                  <div className="space-y-4 pt-4 border-t border-slate-800">
                    {/* Score Cards */}
                    <div className="grid grid-cols-3 gap-4">
                      <Card className="bg-slate-800 border-slate-700">
                        <CardContent className="p-4 text-center">
                          <div className={`text-3xl font-bold ${
                            aiResult.human_probability >= 80 ? 'text-green-400' :
                            aiResult.human_probability >= 50 ? 'text-amber-400' : 'text-red-400'
                          }`}>
                            {aiResult.human_probability.toFixed(0)}%
                          </div>
                          <p className="text-slate-400 text-sm">Human Written</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-slate-800 border-slate-700">
                        <CardContent className="p-4 text-center">
                          <div className={`text-3xl font-bold ${
                            aiResult.ai_probability < 20 ? 'text-green-400' :
                            aiResult.ai_probability < 50 ? 'text-amber-400' : 'text-red-400'
                          }`}>
                            {aiResult.ai_probability.toFixed(0)}%
                          </div>
                          <p className="text-slate-400 text-sm">AI Generated</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-slate-800 border-slate-700">
                        <CardContent className="p-4 text-center">
                          <Badge className={getVerdictColor(aiResult.verdict)}>
                            {aiResult.verdict === 'human' && <CheckCircle2 className="h-4 w-4 mr-1" />}
                            {aiResult.verdict === 'mixed' && <AlertTriangle className="h-4 w-4 mr-1" />}
                            {aiResult.verdict === 'ai' && <Brain className="h-4 w-4 mr-1" />}
                            {aiResult.verdict.toUpperCase()}
                          </Badge>
                          <p className="text-slate-400 text-sm mt-2">Verdict</p>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Analysis Details */}
                    <Card className="bg-slate-800/50 border-slate-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-white text-sm flex items-center gap-2">
                          <Target className="h-4 w-4 text-cyan-400" />
                          Analysis Details
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-slate-400">Word Count</p>
                            <p className="text-white font-medium">{aiResult.analysis.word_count}</p>
                          </div>
                          <div>
                            <p className="text-slate-400">Sentences</p>
                            <p className="text-white font-medium">{aiResult.analysis.sentence_count}</p>
                          </div>
                          <div>
                            <p className="text-slate-400">Avg Sentence Length</p>
                            <p className="text-white font-medium">{aiResult.analysis.avg_sentence_length} words</p>
                          </div>
                          <div>
                            <p className="text-slate-400">Vocabulary Richness</p>
                            <p className="text-white font-medium">{aiResult.analysis.vocabulary_richness}%</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Recommendations */}
                    <Card className="bg-slate-800/50 border-slate-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-white text-sm flex items-center gap-2">
                          <Lightbulb className="h-4 w-4 text-amber-400" />
                          Recommendations
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {aiResult.recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                              <ArrowRight className="h-4 w-4 text-purple-400 mt-0.5 flex-shrink-0" />
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* IEEE Paper Analysis Tab */}
          <TabsContent value="ieee-paper" className="space-y-6">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <FileSearch className="h-5 w-5 text-amber-400" />
                  IEEE Paper Analyzer
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Paste the IEEE paper content here (minimum 500 characters). Include abstract, methodology, results sections..."
                  rows={12}
                  className="bg-slate-800 border-slate-700 text-white resize-none"
                />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">
                    {text.length} characters | {text.split(/\s+/).filter(Boolean).length} words
                  </span>
                  <Button
                    onClick={analyzeIEEEPaper}
                    disabled={loading || text.length < 500}
                    className="bg-amber-500 hover:bg-amber-600 text-black"
                  >
                    {loading ? (
                      <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Analyzing...</>
                    ) : (
                      <><FileSearch className="h-4 w-4 mr-2" /> Analyze Paper</>
                    )}
                  </Button>
                </div>

                {error && (
                  <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
                    <p className="text-red-400 text-sm">{error}</p>
                  </div>
                )}

                {ieeeResult && (
                  <div className="space-y-4 pt-4 border-t border-slate-800">
                    {/* Paper Info */}
                    <Card className="bg-slate-800/50 border-slate-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-white text-lg">{ieeeResult.title}</CardTitle>
                        <p className="text-slate-400 text-sm">
                          Authors: {ieeeResult.authors.join(', ')}
                        </p>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2 mb-4">
                          {ieeeResult.keywords.map((keyword, i) => (
                            <Badge key={i} className="bg-amber-500/20 text-amber-400 border-amber-500/30">
                              {keyword}
                            </Badge>
                          ))}
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-slate-400">Word Count</p>
                            <p className="text-white font-medium">{ieeeResult.word_count}</p>
                          </div>
                          <div>
                            <p className="text-slate-400">References</p>
                            <p className="text-white font-medium">{ieeeResult.references_count}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Abstract */}
                    <Card className="bg-slate-800/50 border-slate-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-white text-sm flex items-center gap-2">
                          <BookOpen className="h-4 w-4 text-cyan-400" />
                          Abstract
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-slate-300 text-sm">{ieeeResult.abstract}</p>
                      </CardContent>
                    </Card>

                    {/* Key Findings */}
                    <Card className="bg-slate-800/50 border-slate-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-white text-sm flex items-center gap-2">
                          <Target className="h-4 w-4 text-green-400" />
                          Key Findings
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {ieeeResult.findings.map((finding, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                              <CheckCircle2 className="h-4 w-4 text-green-400 mt-0.5 flex-shrink-0" />
                              {finding}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>

                    {/* Research Gaps */}
                    <Card className="bg-slate-800/50 border-slate-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-white text-sm flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-amber-400" />
                          Research Gaps
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {ieeeResult.research_gaps.map((gap, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                              <ArrowRight className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
                              {gap}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>

                    {/* Suggested Next Steps */}
                    <Card className="bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border-cyan-500/30">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-white text-sm flex items-center gap-2">
                          <Lightbulb className="h-4 w-4 text-cyan-400" />
                          Suggested Next Steps for Your Project
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {ieeeResult.suggested_next_steps.map((step, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-white">
                              <span className="text-cyan-400 font-bold">{i + 1}.</span>
                              {step}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>

                    {/* Implementation Ideas */}
                    <Card className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 border-purple-500/30">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-white text-sm flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-purple-400" />
                          Implementation Ideas
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {ieeeResult.implementation_ideas.map((idea, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-white">
                              <ArrowRight className="h-4 w-4 text-purple-400 mt-0.5 flex-shrink-0" />
                              {idea}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Requirements Badge */}
        <div className="mt-8 text-center space-y-4">
          <div className="inline-flex items-center gap-4 text-sm text-slate-400">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4 text-green-400" />
              Plagiarism &lt; 10%
            </span>
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4 text-green-400" />
              AI Usage &lt; 20%
            </span>
          </div>

          {/* API Status */}
          <div className="flex justify-center gap-4 text-xs">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-full">
              <div className={`w-2 h-2 rounded-full ${apiStatus?.copyscape?.enabled ? 'bg-green-400' : 'bg-amber-400'}`} />
              <span className="text-slate-400">
                Copyscape: {apiStatus?.copyscape?.enabled ? 'Active' : 'Demo Mode'}
              </span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-full">
              <div className={`w-2 h-2 rounded-full ${apiStatus?.gptzero?.enabled ? 'bg-green-400' : 'bg-amber-400'}`} />
              <span className="text-slate-400">
                GPTZero: {apiStatus?.gptzero?.enabled ? 'Active' : 'Demo Mode'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
