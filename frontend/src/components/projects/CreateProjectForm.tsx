'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { apiClient } from '@/lib/api-client'
import { BookOpen, Code, Rocket, GraduationCap, AlertTriangle, Crown } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useUpgrade } from '@/contexts/UpgradeContext'

interface CreateProjectFormProps {
  onProjectCreated?: (project: any) => void
}

const PROJECT_MODES = [
  {
    id: 'student',
    name: 'Student Mode',
    description: 'Complete academic project with SRS, Code, Reports, PPT, and Viva Q&A',
    icon: GraduationCap,
    estimatedTokens: 20000,
    color: 'bg-blue-500',
  },
  {
    id: 'developer',
    name: 'Developer Mode',
    description: 'Code automation like Bolt.new - Generate production-ready code',
    icon: Code,
    estimatedTokens: 15000,
    color: 'bg-green-500',
  },
  {
    id: 'founder',
    name: 'Founder Mode',
    description: 'Product building with PRD, business plan, and implementation',
    icon: Rocket,
    estimatedTokens: 18000,
    color: 'bg-purple-500',
  },
  {
    id: 'college',
    name: 'College Mode',
    description: 'Faculty and batch management system',
    icon: BookOpen,
    estimatedTokens: 12000,
    color: 'bg-orange-500',
  },
]

interface PlanStatus {
  plan: {
    name: string
    type: string
    is_free: boolean
    is_premium: boolean
  }
  projects: {
    created: number
    limit: number | null
    remaining: number | null
    can_create: boolean
  }
  features: {
    project_generation: boolean
  }
  needs_upgrade: boolean
  upgrade_message: string | null
}

export function CreateProjectForm({ onProjectCreated }: CreateProjectFormProps) {
  const router = useRouter()
  const { checkFeatureError, showUpgradePrompt } = useUpgrade()
  const [selectedMode, setSelectedMode] = useState<string>('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [techStack, setTechStack] = useState('')
  const [features, setFeatures] = useState<string[]>([])
  const [featureInput, setFeatureInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [planStatus, setPlanStatus] = useState<PlanStatus | null>(null)
  const [checkingPlan, setCheckingPlan] = useState(true)

  // Check subscription status on mount
  useEffect(() => {
    const checkPlanStatus = async () => {
      try {
        const status = await apiClient.getPlanStatus()
        setPlanStatus(status)
      } catch (err) {
        console.error('Failed to check plan status:', err)
      } finally {
        setCheckingPlan(false)
      }
    }
    checkPlanStatus()
  }, [])

  const handleAddFeature = () => {
    if (featureInput.trim()) {
      setFeatures([...features, featureInput.trim()])
      setFeatureInput('')
    }
  }

  const handleRemoveFeature = (index: number) => {
    setFeatures(features.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!selectedMode || !title) {
      setError('Please select a mode and enter a project title')
      return
    }

    // Check if user can create projects
    if (planStatus && !planStatus.projects.can_create) {
      showUpgradePrompt({
        feature: 'project_limit',
        currentPlan: `${planStatus.projects.created}/${planStatus.projects.limit} projects used`,
        upgradeTo: 'Premium',
        message: planStatus.upgrade_message || 'You have reached your project limit. Upgrade to create more projects.'
      })
      return
    }

    // Check if project generation feature is enabled
    if (planStatus && !planStatus.features.project_generation) {
      showUpgradePrompt({
        feature: 'project_generation',
        currentPlan: planStatus.plan.name,
        upgradeTo: 'Premium',
        message: 'Project generation is not available on your current plan.'
      })
      return
    }

    setLoading(true)

    try {
      const project = await apiClient.createProject({
        title,
        description,
        mode: selectedMode as any,
        tech_stack: techStack,
        features: features.length > 0 ? features : undefined,
      })

      // Execute the project only if subscription allows
      try {
        await apiClient.executeProject(project.id)
      } catch (execErr: any) {
        // Handle execution-specific errors (like limit reached)
        if (checkFeatureError(execErr)) {
          return // Upgrade modal shown
        }
        throw execErr
      }

      if (onProjectCreated) {
        onProjectCreated(project)
      }

      // Reset form
      setTitle('')
      setDescription('')
      setTechStack('')
      setFeatures([])
      setSelectedMode('')
    } catch (err: any) {
      // Check if it's a feature/limit restriction error
      if (checkFeatureError(err)) {
        return // Upgrade modal shown
      }

      const errorDetail = err.response?.data?.detail
      if (typeof errorDetail === 'object') {
        setError(errorDetail.message || 'Failed to create project')
      } else {
        setError(errorDetail || 'Failed to create project')
      }
    } finally {
      setLoading(false)
    }
  }

  const selectedModeInfo = PROJECT_MODES.find(m => m.id === selectedMode)

  // Check if user can generate projects
  const canGenerate = planStatus?.projects.can_create && planStatus?.features.project_generation
  const needsUpgrade = planStatus?.needs_upgrade || !canGenerate

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Create New Project</CardTitle>
        <CardDescription>
          Choose your mode and let AI agents build your project
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Upgrade Banner for FREE users */}
        {planStatus && needsUpgrade && (
          <div className="mb-6 p-4 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-amber-100 rounded-full">
                <Crown className="h-5 w-5 text-amber-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-amber-900">
                  {planStatus.plan.is_free ? 'Upgrade to Premium' : 'Project Limit Reached'}
                </h3>
                <p className="text-sm text-amber-700 mt-1">
                  {planStatus.upgrade_message || 'Upgrade your plan to create and generate projects.'}
                </p>
                {planStatus.projects.limit !== null && (
                  <p className="text-xs text-amber-600 mt-2">
                    Projects: {planStatus.projects.created} / {planStatus.projects.limit} used
                  </p>
                )}
                <Button
                  variant="default"
                  size="sm"
                  className="mt-3 bg-amber-600 hover:bg-amber-700"
                  onClick={() => router.push('/pricing')}
                >
                  <Crown className="h-4 w-4 mr-2" />
                  View Plans
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Loading state while checking plan */}
        {checkingPlan && (
          <div className="mb-4 p-3 bg-gray-50 rounded-lg text-center text-sm text-gray-500">
            Checking your subscription...
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Mode Selection */}
          <div className="space-y-3">
            <Label>Select Project Mode</Label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {PROJECT_MODES.map((mode) => {
                const Icon = mode.icon
                return (
                  <div
                    key={mode.id}
                    onClick={() => setSelectedMode(mode.id)}
                    className={`
                      relative cursor-pointer rounded-lg border-2 p-4 transition-all
                      ${selectedMode === mode.id
                        ? 'border-primary bg-primary/5'
                        : 'border-gray-200 hover:border-gray-300'
                      }
                    `}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`${mode.color} p-2 rounded-lg text-white`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-sm">{mode.name}</h3>
                        <p className="text-xs text-muted-foreground mt-1">
                          {mode.description}
                        </p>
                        <Badge variant="secondary" className="mt-2 text-xs">
                          ~{mode.estimatedTokens.toLocaleString()} tokens
                        </Badge>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Project Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Project Title *</Label>
            <Input
              id="title"
              placeholder="e.g., E-Commerce Platform, Task Manager App"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          {/* Project Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <textarea
              id="description"
              placeholder="Describe your project idea in detail..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          {/* Tech Stack */}
          {selectedMode !== 'college' && (
            <div className="space-y-2">
              <Label htmlFor="techStack">Tech Stack</Label>
              <Input
                id="techStack"
                placeholder="e.g., React, Node.js, PostgreSQL, AWS"
                value={techStack}
                onChange={(e) => setTechStack(e.target.value)}
              />
              {/* Quick Tech Stack Suggestions */}
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="text-xs text-muted-foreground">Quick select:</span>
                {[
                  { label: 'React + Node.js', value: 'React, Node.js, Express, PostgreSQL' },
                  { label: 'Next.js Full Stack', value: 'Next.js, TypeScript, Tailwind CSS, Prisma' },
                  { label: 'Python FastAPI', value: 'Python, FastAPI, SQLAlchemy, PostgreSQL' },
                  { label: 'Flutter Mobile', value: 'Flutter, Dart, Firebase' },
                  { label: 'React Native', value: 'React Native, Expo, TypeScript' },
                  { label: 'Spring Boot', value: 'Java, Spring Boot, Maven, MySQL' },
                ].map((suggestion) => (
                  <Badge
                    key={suggestion.label}
                    variant="outline"
                    className="cursor-pointer hover:bg-primary/10 transition-colors text-xs"
                    onClick={() => setTechStack(suggestion.value)}
                  >
                    {suggestion.label}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Features */}
          {selectedMode === 'student' || selectedMode === 'developer' ? (
            <div className="space-y-2">
              <Label>Key Features</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Add a feature and press Enter"
                  value={featureInput}
                  onChange={(e) => setFeatureInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddFeature()
                    }
                  }}
                />
                <Button type="button" variant="outline" onClick={handleAddFeature}>
                  Add
                </Button>
              </div>
              {features.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {features.map((feature, index) => (
                    <Badge key={index} variant="secondary" className="pl-2 pr-1">
                      {feature}
                      <button
                        type="button"
                        onClick={() => handleRemoveFeature(index)}
                        className="ml-1 hover:text-destructive"
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ) : null}

          {/* Error Message */}
          {error && (
            <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
              {error}
            </div>
          )}

          {/* Token Estimate */}
          {selectedModeInfo && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-blue-900">
                <strong>Estimated Token Usage:</strong> ~{selectedModeInfo.estimatedTokens.toLocaleString()} tokens
              </p>
              <p className="text-xs text-blue-700 mt-1">
                This project will be executed automatically by our AI agents
              </p>
            </div>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={loading || !selectedMode || !title || checkingPlan || !!(planStatus && !canGenerate)}
          >
            {loading ? (
              'Creating Project...'
            ) : checkingPlan ? (
              'Checking subscription...'
            ) : planStatus && !canGenerate ? (
              <>
                <Crown className="h-4 w-4 mr-2" />
                Upgrade to Create Projects
              </>
            ) : (
              'Create & Execute Project'
            )}
          </Button>

          {/* Show project count for users with limits */}
          {planStatus && planStatus.projects.limit !== null && canGenerate && (
            <p className="text-center text-xs text-muted-foreground">
              {planStatus.projects.remaining} project{planStatus.projects.remaining !== 1 ? 's' : ''} remaining on your {planStatus.plan.name} plan
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  )
}
