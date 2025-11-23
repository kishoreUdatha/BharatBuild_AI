'use client'

import { useState } from 'react'
import { TokenBalanceCard } from '@/components/dashboard/TokenBalanceCard'
import { CreateProjectForm } from '@/components/projects/CreateProjectForm'
import { ProjectExecutionView } from '@/components/projects/ProjectExecutionView'
import { TokenAnalytics } from '@/components/analytics/TokenAnalytics'
import { TokenPurchase } from '@/components/tokens/TokenPurchase'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  LayoutDashboard,
  FolderPlus,
  BarChart3,
  ShoppingCart,
  Coins
} from 'lucide-react'

export default function DashboardPage() {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)

  const handleProjectCreated = (project: any) => {
    setActiveProjectId(project.id)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b bg-white">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold">BharatBuild AI Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            AI-powered project generation platform
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5 lg:w-auto">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <LayoutDashboard className="h-4 w-4" />
              <span className="hidden sm:inline">Overview</span>
            </TabsTrigger>
            <TabsTrigger value="create" className="flex items-center gap-2">
              <FolderPlus className="h-4 w-4" />
              <span className="hidden sm:inline">Create</span>
            </TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Analytics</span>
            </TabsTrigger>
            <TabsTrigger value="tokens" className="flex items-center gap-2">
              <Coins className="h-4 w-4" />
              <span className="hidden sm:inline">Tokens</span>
            </TabsTrigger>
            <TabsTrigger value="purchase" className="flex items-center gap-2">
              <ShoppingCart className="h-4 w-4" />
              <span className="hidden sm:inline">Purchase</span>
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <TokenBalanceCard />

            {activeProjectId ? (
              <ProjectExecutionView projectId={activeProjectId} />
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle>Welcome to BharatBuild AI</CardTitle>
                  <CardDescription>
                    Get started by creating your first project
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 border rounded-lg">
                      <h3 className="font-semibold mb-2">Student Mode</h3>
                      <p className="text-sm text-muted-foreground">
                        Generate complete academic projects with SRS, code, reports, and presentations
                      </p>
                    </div>
                    <div className="p-4 border rounded-lg">
                      <h3 className="font-semibold mb-2">Developer Mode</h3>
                      <p className="text-sm text-muted-foreground">
                        Build production-ready applications with AI-generated code
                      </p>
                    </div>
                    <div className="p-4 border rounded-lg">
                      <h3 className="font-semibold mb-2">Founder Mode</h3>
                      <p className="text-sm text-muted-foreground">
                        Create product requirements and business plans for your startup
                      </p>
                    </div>
                    <div className="p-4 border rounded-lg">
                      <h3 className="font-semibold mb-2">College Mode</h3>
                      <p className="text-sm text-muted-foreground">
                        Manage faculty and batches with automated systems
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Create Project Tab */}
          <TabsContent value="create">
            <CreateProjectForm onProjectCreated={handleProjectCreated} />
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics">
            <TokenAnalytics />
          </TabsContent>

          {/* Tokens Tab */}
          <TabsContent value="tokens" className="space-y-6">
            <TokenBalanceCard />

            <Card>
              <CardHeader>
                <CardTitle>Token Usage History</CardTitle>
                <CardDescription>
                  Recent token transactions and activity
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  View your complete transaction history in the Analytics tab
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Purchase Tab */}
          <TabsContent value="purchase">
            <TokenPurchase />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
