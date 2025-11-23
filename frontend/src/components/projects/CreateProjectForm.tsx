'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { apiClient } from '@/lib/api-client'
import { BookOpen, Code, Rocket, GraduationCap } from 'lucide-react'

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

export function CreateProjectForm({ onProjectCreated }: CreateProjectFormProps) {
  const [selectedMode, setSelectedMode] = useState<string>('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [techStack, setTechStack] = useState('')
  const [features, setFeatures] = useState<string[]>([])
  const [featureInput, setFeatureInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

    setLoading(true)

    try {
      const project = await apiClient.createProject({
        title,
        description,
        mode: selectedMode as any,
        tech_stack: techStack,
        features: features.length > 0 ? features : undefined,
      })

      // Execute the project immediately
      await apiClient.executeProject(project.id)

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
      setError(err.response?.data?.detail || 'Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  const selectedModeInfo = PROJECT_MODES.find(m => m.id === selectedMode)

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Create New Project</CardTitle>
        <CardDescription>
          Choose your mode and let AI agents build your project
        </CardDescription>
      </CardHeader>
      <CardContent>
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
            disabled={loading || !selectedMode || !title}
          >
            {loading ? 'Creating Project...' : 'Create & Execute Project'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
