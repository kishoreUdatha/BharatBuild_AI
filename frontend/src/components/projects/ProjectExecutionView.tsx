'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { apiClient } from '@/lib/api-client'
import { formatNumber } from '@/lib/utils'
import {
  CheckCircle2,
  Circle,
  Clock,
  Download,
  Loader2,
  AlertCircle,
} from 'lucide-react'

interface ProjectExecutionViewProps {
  projectId: string
}

interface AgentStatus {
  name: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progress: number
  tokensUsed?: number
  message?: string
}

const AGENT_STEPS: Record<string, AgentStatus[]> = {
  student: [
    { name: 'Idea Refinement', status: 'pending', progress: 0 },
    { name: 'SRS Generation', status: 'pending', progress: 0 },
    { name: 'Code Generation', status: 'pending', progress: 0 },
    { name: 'UML Diagrams', status: 'pending', progress: 0 },
    { name: 'Report Generation', status: 'pending', progress: 0 },
    { name: 'PPT Creation', status: 'pending', progress: 0 },
    { name: 'Viva Q&A', status: 'pending', progress: 0 },
  ],
  developer: [
    { name: 'Code Architecture', status: 'pending', progress: 0 },
    { name: 'Code Generation', status: 'pending', progress: 0 },
    { name: 'Testing Setup', status: 'pending', progress: 0 },
  ],
  founder: [
    { name: 'Business Analysis', status: 'pending', progress: 0 },
    { name: 'PRD Generation', status: 'pending', progress: 0 },
    { name: 'Technical Architecture', status: 'pending', progress: 0 },
  ],
  college: [
    { name: 'System Analysis', status: 'pending', progress: 0 },
    { name: 'Database Design', status: 'pending', progress: 0 },
    { name: 'Implementation', status: 'pending', progress: 0 },
  ],
}

export function ProjectExecutionView({ projectId }: ProjectExecutionViewProps) {
  const [project, setProject] = useState<any>(null)
  const [agentSteps, setAgentSteps] = useState<AgentStatus[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadProjectStatus()
    const interval = setInterval(loadProjectStatus, 3000) // Poll every 3 seconds
    return () => clearInterval(interval)
  }, [projectId])

  const loadProjectStatus = async () => {
    try {
      const data = await apiClient.getProjectStatus(projectId)
      setProject(data)

      // Initialize agent steps based on mode
      if (!agentSteps.length && data.mode) {
        setAgentSteps(AGENT_STEPS[data.mode] || [])
      }

      // Update agent steps based on progress
      updateAgentSteps(data.progress, data.status)
    } catch (error) {
      console.error('Failed to load project status:', error)
    } finally {
      setLoading(false)
    }
  }

  const updateAgentSteps = (progress: number, status: string) => {
    setAgentSteps((prev) => {
      if (!prev.length) return prev

      const stepsPerAgent = 100 / prev.length
      const currentStepIndex = Math.floor(progress / stepsPerAgent)

      return prev.map((step, index) => {
        if (index < currentStepIndex) {
          return { ...step, status: 'completed', progress: 100 }
        } else if (index === currentStepIndex) {
          const stepProgress = ((progress % stepsPerAgent) / stepsPerAgent) * 100
          return {
            ...step,
            status: status === 'failed' ? 'failed' : 'in_progress',
            progress: stepProgress,
          }
        }
        return step
      })
    })
  }

  const handleDownload = async (docType: string) => {
    try {
      const blob = await apiClient.downloadDocument(projectId, docType)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${project.title}-${docType}.${docType === 'zip' ? 'zip' : 'pdf'}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Download failed:', error)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (!project) return null

  const isCompleted = project.status === 'completed'
  const isFailed = project.status === 'failed'
  const isProcessing = project.status === 'processing' || project.status === 'in_progress'

  return (
    <div className="space-y-6">
      {/* Project Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle>{project.title}</CardTitle>
              <CardDescription>{project.description}</CardDescription>
            </div>
            <Badge
              variant={
                isCompleted ? 'success' :
                isFailed ? 'destructive' :
                isProcessing ? 'warning' : 'secondary'
              }
            >
              {project.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Overall Progress */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Overall Progress</span>
                <span className="text-sm text-muted-foreground">{project.progress}%</span>
              </div>
              <Progress value={project.progress} className="h-2" />
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div>
                <p className="text-xs text-muted-foreground">Tokens Used</p>
                <p className="text-lg font-semibold">{formatNumber(project.total_tokens || 0)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Cost (INR)</p>
                <p className="text-lg font-semibold">
                  ₹{((project.total_cost || 0) / 100).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Mode</p>
                <p className="text-lg font-semibold capitalize">{project.mode}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent Execution Steps */}
      <Card>
        <CardHeader>
          <CardTitle>AI Agent Execution</CardTitle>
          <CardDescription>Real-time progress of each AI agent</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {agentSteps.map((step, index) => (
              <div key={index} className="flex items-start gap-3">
                {/* Status Icon */}
                <div className="mt-1">
                  {step.status === 'completed' && (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  )}
                  {step.status === 'in_progress' && (
                    <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                  )}
                  {step.status === 'failed' && (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  )}
                  {step.status === 'pending' && (
                    <Circle className="h-5 w-5 text-gray-300" />
                  )}
                </div>

                {/* Step Details */}
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm">{step.name}</span>
                    {step.tokensUsed && (
                      <span className="text-xs text-muted-foreground">
                        {formatNumber(step.tokensUsed)} tokens
                      </span>
                    )}
                  </div>

                  {step.status === 'in_progress' && (
                    <Progress value={step.progress} className="h-1" />
                  )}

                  {step.message && (
                    <p className="text-xs text-muted-foreground">{step.message}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Download Section */}
      {isCompleted && (
        <Card>
          <CardHeader>
            <CardTitle>Download Generated Files</CardTitle>
            <CardDescription>All project deliverables are ready</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {project.mode === 'student' && (
                <>
                  <Button variant="outline" onClick={() => handleDownload('srs')}>
                    <Download className="h-4 w-4 mr-2" />
                    SRS Document
                  </Button>
                  <Button variant="outline" onClick={() => handleDownload('code')}>
                    <Download className="h-4 w-4 mr-2" />
                    Source Code
                  </Button>
                  <Button variant="outline" onClick={() => handleDownload('report')}>
                    <Download className="h-4 w-4 mr-2" />
                    Project Report
                  </Button>
                  <Button variant="outline" onClick={() => handleDownload('ppt')}>
                    <Download className="h-4 w-4 mr-2" />
                    Presentation
                  </Button>
                  <Button variant="outline" onClick={() => handleDownload('viva')}>
                    <Download className="h-4 w-4 mr-2" />
                    Viva Q&A
                  </Button>
                  <Button variant="outline" onClick={() => handleDownload('uml')}>
                    <Download className="h-4 w-4 mr-2" />
                    UML Diagrams
                  </Button>
                </>
              )}
              <Button variant="default" onClick={() => handleDownload('zip')} className="col-span-2">
                <Download className="h-4 w-4 mr-2" />
                Download All (ZIP)
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
