'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  BookOpen, Code, Brain, ChevronRight, CheckCircle2, Lock,
  Sparkles, Clock, Target, Trophy, ArrowLeft, Play, Layers,
  FileText, Zap, Star, CircleDot
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface Lab {
  id: string
  name: string
  code: string
  description?: string
  branch: string
  semester: string
  technologies?: string[]
  total_topics: number
  total_mcqs: number
  total_coding_problems: number
}

interface Topic {
  id: string
  lab_id: string
  title: string
  description?: string
  week_number: number
  order_index: number
  mcq_count: number
  coding_count: number
  prerequisites?: string[]
  is_active: boolean
}

interface TopicProgress {
  topic_id: string
  status: 'not_started' | 'in_progress' | 'completed'
  concept_read: boolean
  mcq_score: number
  coding_score: number
  progress_percentage: number
}

interface LabProgress {
  overall_progress: number
  topics_completed: number
  mcqs_attempted: number
  mcqs_correct: number
  problems_solved: number
  mcq_score: number
  coding_score: number
}

export default function LabTopicsPage() {
  const router = useRouter()
  const params = useParams()
  const labId = params.labId as string

  const [lab, setLab] = useState<Lab | null>(null)
  const [topics, setTopics] = useState<Topic[]>([])
  const [topicProgress, setTopicProgress] = useState<Record<string, TopicProgress>>({})
  const [labProgress, setLabProgress] = useState<LabProgress | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (labId) {
      fetchLabData()
    }
  }, [labId])

  const fetchLabData = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      // Fetch lab details and topics from public endpoints (no auth required)
      // Progress requires auth
      const [labRes, topicsRes, progressRes] = await Promise.all([
        fetch(`${API_URL}/lab/public/labs/${labId}`),
        fetch(`${API_URL}/lab/public/labs/${labId}/topics`),
        token ? fetch(`${API_URL}/lab/labs/${labId}/topics-progress`, { headers }).catch(() => null) : Promise.resolve(null)
      ])

      if (labRes.ok) {
        const labData = await labRes.json()
        setLab(labData)
      }

      if (topicsRes.ok) {
        const topicsData = await topicsRes.json()
        setTopics(topicsData)
      }

      if (progressRes?.ok) {
        const progressData = await progressRes.json()
        // Convert array to map
        const progressMap: Record<string, TopicProgress> = {}
        progressData.forEach((p: TopicProgress) => {
          progressMap[p.topic_id] = p
        })
        setTopicProgress(progressMap)
      }

      // Fetch overall lab progress
      const labProgressRes = await fetch(`${API_URL}/lab/labs/${labId}/progress`, { headers }).catch(() => null)
      if (labProgressRes?.ok) {
        const lpData = await labProgressRes.json()
        setLabProgress(lpData)
      }

    } catch (error) {
      console.error('Error fetching lab data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getTopicStatus = (topic: Topic): 'locked' | 'not_started' | 'in_progress' | 'completed' => {
    const progress = topicProgress[topic.id]
    if (progress) {
      return progress.status
    }

    // Check prerequisites
    if (topic.prerequisites && topic.prerequisites.length > 0) {
      const allPrereqsComplete = topic.prerequisites.every(prereqId => {
        const prereqProgress = topicProgress[prereqId]
        return prereqProgress?.status === 'completed'
      })
      if (!allPrereqsComplete) return 'locked'
    }

    return 'not_started'
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-400" />
      case 'in_progress':
        return <Play className="h-5 w-5 text-cyan-400" />
      case 'locked':
        return <Lock className="h-5 w-5 text-slate-500" />
      default:
        return <CircleDot className="h-5 w-5 text-slate-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'border-green-500/50 bg-green-500/5'
      case 'in_progress':
        return 'border-cyan-500/50 bg-cyan-500/5'
      case 'locked':
        return 'border-slate-700 bg-slate-800/30 opacity-60'
      default:
        return 'border-slate-700 hover:border-cyan-500/50'
    }
  }

  // Group topics by week
  const topicsByWeek = topics.reduce((acc, topic) => {
    const week = topic.week_number
    if (!acc[week]) acc[week] = []
    acc[week].push(topic)
    return acc
  }, {} as Record<number, Topic[]>)

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-20 h-20 border-4 border-cyan-500/30 rounded-full animate-spin border-t-cyan-500"></div>
            <Sparkles className="absolute inset-0 m-auto h-8 w-8 text-cyan-400 animate-pulse" />
          </div>
          <p className="mt-4 text-cyan-400 font-medium">Loading Topics...</p>
        </div>
      </div>
    )
  }

  if (!lab) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Lab Not Found</h2>
          <Link href="/lab">
            <Button variant="outline" className="border-cyan-500/50 text-cyan-400">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Labs
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-3xl"></div>
      </div>
      <div className="fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px] pointer-events-none"></div>

      <div className="relative z-10 py-8 px-4">
        <div className="max-w-6xl mx-auto">
          {/* Back Button */}
          <Link href="/lab" className="inline-flex items-center text-slate-400 hover:text-cyan-400 mb-6 transition-colors">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Labs
          </Link>

          {/* Lab Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <span className="px-3 py-1 bg-cyan-500/10 text-cyan-400 text-sm rounded-lg font-medium">
                {lab.code}
              </span>
              <span className="px-3 py-1 bg-purple-500/10 text-purple-400 text-sm rounded-lg">
                {lab.branch.toUpperCase()} - {lab.semester.replace('sem_', 'Semester ')}
              </span>
            </div>

            <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">{lab.name}</h1>
            {lab.description && (
              <p className="text-slate-400 text-lg max-w-3xl">{lab.description}</p>
            )}

            {/* Technologies */}
            {lab.technologies && lab.technologies.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-4">
                {lab.technologies.map((tech, i) => (
                  <span key={i} className="px-3 py-1 bg-slate-800 text-slate-300 text-sm rounded-lg">
                    {tech}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Progress Overview */}
          {labProgress && (
            <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800 mb-8">
              <CardContent className="p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Target className="h-5 w-5 text-cyan-400" />
                  Your Progress
                </h3>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                  <div className="text-center p-4 bg-slate-800/50 rounded-xl">
                    <Layers className="h-6 w-6 text-cyan-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{labProgress.topics_completed}/{lab.total_topics}</p>
                    <p className="text-xs text-slate-400">Topics</p>
                  </div>
                  <div className="text-center p-4 bg-slate-800/50 rounded-xl">
                    <Brain className="h-6 w-6 text-purple-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{labProgress.mcqs_correct}/{labProgress.mcqs_attempted}</p>
                    <p className="text-xs text-slate-400">MCQs Correct</p>
                  </div>
                  <div className="text-center p-4 bg-slate-800/50 rounded-xl">
                    <Code className="h-6 w-6 text-green-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{labProgress.problems_solved}</p>
                    <p className="text-xs text-slate-400">Problems Solved</p>
                  </div>
                  <div className="text-center p-4 bg-slate-800/50 rounded-xl">
                    <Star className="h-6 w-6 text-amber-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{Math.round(labProgress.mcq_score)}%</p>
                    <p className="text-xs text-slate-400">MCQ Score</p>
                  </div>
                  <div className="text-center p-4 bg-slate-800/50 rounded-xl">
                    <Trophy className="h-6 w-6 text-amber-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{Math.round(labProgress.coding_score)}%</p>
                    <p className="text-xs text-slate-400">Coding Score</p>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-slate-400">Overall Progress</span>
                    <span className="text-cyan-400 font-semibold">{Math.round(labProgress.overall_progress)}%</span>
                  </div>
                  <Progress value={labProgress.overall_progress} className="h-3 bg-slate-800" />
                </div>
              </CardContent>
            </Card>
          )}

          {/* Topics by Week */}
          <div className="space-y-8">
            {Object.keys(topicsByWeek).sort((a, b) => Number(a) - Number(b)).map(week => (
              <div key={week}>
                <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  <Clock className="h-5 w-5 text-cyan-400" />
                  Week {week}
                </h2>

                <div className="space-y-4">
                  {topicsByWeek[Number(week)].sort((a, b) => a.order_index - b.order_index).map(topic => {
                    const status = getTopicStatus(topic)
                    const progress = topicProgress[topic.id]
                    const isLocked = status === 'locked'

                    return (
                      <Card
                        key={topic.id}
                        className={`bg-slate-900/60 backdrop-blur-xl border transition-all duration-300 ${getStatusColor(status)} ${!isLocked ? 'cursor-pointer hover:shadow-lg hover:shadow-cyan-500/10' : ''}`}
                        onClick={() => !isLocked && router.push(`/lab/topic/${topic.id}`)}
                      >
                        <CardContent className="p-6">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                                status === 'completed' ? 'bg-green-500/20' :
                                status === 'in_progress' ? 'bg-cyan-500/20' :
                                'bg-slate-800'
                              }`}>
                                {getStatusIcon(status)}
                              </div>

                              <div>
                                <h3 className={`text-lg font-semibold ${isLocked ? 'text-slate-500' : 'text-white'}`}>
                                  {topic.title}
                                </h3>
                                {topic.description && (
                                  <p className="text-sm text-slate-400 mt-1 line-clamp-1">{topic.description}</p>
                                )}

                                <div className="flex items-center gap-4 mt-2">
                                  <span className="flex items-center gap-1 text-xs text-slate-400">
                                    <FileText className="h-3 w-3" /> Concepts
                                  </span>
                                  <span className="flex items-center gap-1 text-xs text-slate-400">
                                    <Brain className="h-3 w-3" /> {topic.mcq_count} MCQs
                                  </span>
                                  <span className="flex items-center gap-1 text-xs text-slate-400">
                                    <Code className="h-3 w-3" /> {topic.coding_count} Problems
                                  </span>
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-4">
                              {progress && progress.progress_percentage > 0 && (
                                <div className="text-right">
                                  <p className="text-sm text-cyan-400 font-semibold">{Math.round(progress.progress_percentage)}%</p>
                                  <Progress value={progress.progress_percentage} className="w-24 h-2 bg-slate-800" />
                                </div>
                              )}

                              {!isLocked && (
                                <ChevronRight className="h-5 w-5 text-slate-400" />
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>

          {topics.length === 0 && (
            <div className="text-center py-16">
              <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <BookOpen className="h-10 w-10 text-slate-600" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">No Topics Yet</h3>
              <p className="text-slate-400">Topics for this lab will be added soon.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
