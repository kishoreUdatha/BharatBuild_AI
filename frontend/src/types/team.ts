/**
 * Team Collaboration Types
 * Matches backend schemas from app/schemas/team.py
 */

// Enums matching backend
export type TeamRole = 'leader' | 'member' | 'viewer'
export type TeamStatus = 'active' | 'archived' | 'deleted'
export type InvitationStatus = 'pending' | 'accepted' | 'declined' | 'expired'
export type TaskStatus = 'todo' | 'in_progress' | 'review' | 'done' | 'blocked'
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'
export type ReviewStatus = 'pending' | 'in_review' | 'approved' | 'changes_requested' | 'rejected'
export type MilestoneStatus = 'planning' | 'active' | 'completed' | 'cancelled'
export type NotificationType =
  | 'mention'
  | 'task_assigned'
  | 'task_due_soon'
  | 'task_overdue'
  | 'review_requested'
  | 'review_completed'
  | 'milestone_due_soon'
  | 'invitation_received'
  | 'member_joined'

export type ActivityType =
  | 'team_created'
  | 'member_joined'
  | 'member_left'
  | 'member_removed'
  | 'task_created'
  | 'task_updated'
  | 'task_assigned'
  | 'task_completed'
  | 'task_commented'
  | 'file_created'
  | 'file_modified'
  | 'file_deleted'
  | 'code_merged'
  | 'review_requested'
  | 'review_completed'
  | 'milestone_created'
  | 'milestone_completed'
  | 'chat_message'

// ============ Core Types ============

export interface MemberSkill {
  id: string
  skill_name: string
  proficiency_level: number
  is_primary: boolean
}

export interface TeamMember {
  id: string
  user_id: string
  team_id: string
  role: TeamRole
  joined_at: string
  is_active: boolean
  user_name?: string
  user_email?: string
  user_avatar?: string
  skills?: MemberSkill[]
  // Computed fields for UI
  status?: 'online' | 'offline' | 'coding'
  current_task?: string
  tasks_completed?: number
  total_tasks?: number
}

export interface Team {
  id: string
  project_id: string
  name: string
  description?: string
  status: TeamStatus
  max_members: number
  created_at: string
  updated_at?: string
  // Relationships
  members?: TeamMember[]
  tasks?: TeamTask[]
  milestones?: TeamMilestone[]
  project_title?: string
}

export interface TeamTask {
  id: string
  team_id: string
  title: string
  description?: string
  status: TaskStatus
  priority: TaskPriority
  assignee_id?: string
  milestone_id?: string
  estimated_hours?: number
  actual_hours?: number
  complexity_score?: number
  file_paths?: string[]
  dependencies?: string[]
  due_date?: string
  started_at?: string
  completed_at?: string
  created_at: string
  updated_at?: string
  // Relationships
  assignee?: TeamMember
  comments?: TaskComment[]
  time_logs?: TaskTimeLog[]
  ai_generated?: boolean
}

export interface TeamInvitation {
  id: string
  team_id: string
  inviter_id: string
  invitee_email: string
  role: TeamRole
  status: InvitationStatus
  token: string
  expires_at: string
  created_at: string
  accepted_at?: string
  // For display
  team_name?: string
  inviter_name?: string
}

// ============ Extended Feature Types ============

export interface TaskComment {
  id: string
  task_id: string
  author_id: string
  parent_id?: string
  content: string
  mentions?: string[]
  is_edited: boolean
  created_at: string
  updated_at?: string
  // For display
  author_name?: string
  author_avatar?: string
  replies?: TaskComment[]
}

export interface TeamActivity {
  id: string
  team_id: string
  actor_id?: string
  activity_type: ActivityType
  description: string
  target_type?: string
  target_id?: string
  activity_data?: Record<string, any>
  created_at: string
  // For display
  actor_name?: string
  actor_avatar?: string
}

export interface TeamChatMessage {
  id: string
  team_id: string
  sender_id?: string
  content: string
  mentions?: string[]
  message_type?: 'text' | 'file' | 'system'
  attachment_url?: string
  attachment_name?: string
  is_edited: boolean
  is_deleted: boolean
  created_at: string
  updated_at?: string
  // For display
  sender_name?: string
  sender_avatar?: string
}

export interface CodeReview {
  id: string
  team_id: string
  requester_id: string
  reviewer_id?: string
  title: string
  description?: string
  status: ReviewStatus
  file_paths: string[]
  feedback?: string
  comments?: Record<string, any>[]
  task_id?: string
  created_at: string
  updated_at?: string
  reviewed_at?: string
  // For display
  requester_name?: string
  reviewer_name?: string
}

export interface TaskTimeLog {
  id: string
  task_id: string
  member_id: string
  description?: string
  started_at: string
  ended_at?: string
  duration_minutes?: number
  is_running: boolean
  // For display
  member_name?: string
}

export interface TeamMilestone {
  id: string
  team_id: string
  created_by: string
  title: string
  description?: string
  status: MilestoneStatus
  start_date?: string
  due_date?: string
  completed_at?: string
  progress: number
  order_index: number
  created_at: string
  updated_at?: string
  // Relationships
  tasks?: TeamTask[]
}

export interface TeamNotification {
  id: string
  user_id: string
  team_id: string
  actor_id?: string
  notification_type: NotificationType
  title: string
  message?: string
  target_type?: string
  target_id?: string
  is_read: boolean
  read_at?: string
  created_at: string
  // For display
  actor_name?: string
  actor_avatar?: string
}

// ============ Request/Response Types ============

export interface CreateTeamRequest {
  project_id: string
  name?: string
  description?: string
  max_members?: number
}

export interface UpdateTeamRequest {
  name?: string
  description?: string
  status?: TeamStatus
}

export interface InviteMemberRequest {
  email: string
  role?: TeamRole
}

export interface CreateTaskRequest {
  title: string
  description?: string
  priority?: TaskPriority
  assignee_id?: string
  milestone_id?: string
  estimated_hours?: number
  file_paths?: string[]
  dependencies?: string[]
  due_date?: string
}

export interface UpdateTaskRequest {
  title?: string
  description?: string
  status?: TaskStatus
  priority?: TaskPriority
  assignee_id?: string
  milestone_id?: string
  estimated_hours?: number
  file_paths?: string[]
  dependencies?: string[]
  due_date?: string
}

export interface TaskSplitRequest {
  balance_workload?: boolean
  max_tasks?: number
  include_file_mapping?: boolean
}

export interface SuggestedTask {
  title: string
  description: string
  priority: TaskPriority
  estimated_hours: number
  complexity_score: number
  file_paths: string[]
  dependencies: number[]
  suggested_assignee_index?: number
}

export interface TaskSplitResponse {
  suggested_tasks: SuggestedTask[]
  total_estimated_hours: number
  workload_distribution: Record<string, number>
  analysis_summary: string
  split_strategy: string
}

export interface ApplyTaskSplitRequest {
  suggested_tasks: SuggestedTask[]
  assign_to_members?: boolean
}

export interface CreateCommentRequest {
  content: string
  parent_id?: string
  mentions?: string[]
}

export interface CreateMilestoneRequest {
  title: string
  description?: string
  start_date?: string
  due_date?: string
}

export interface UpdateMilestoneRequest {
  title?: string
  description?: string
  status?: MilestoneStatus
  start_date?: string
  due_date?: string
}

export interface SendChatMessageRequest {
  content: string
  mentions?: string[]
  message_type?: 'text' | 'file'
  attachment_url?: string
  attachment_name?: string
}

export interface CreateCodeReviewRequest {
  title: string
  description?: string
  file_paths: string[]
  reviewer_id?: string
  task_id?: string
}

export interface SubmitReviewRequest {
  status: 'approved' | 'changes_requested' | 'rejected'
  feedback?: string
  comments?: Record<string, any>[]
}

export interface AddSkillRequest {
  skill_name: string
  proficiency_level?: number
  is_primary?: boolean
}

export interface StartTimeLogRequest {
  description?: string
}

export interface TeamAnalytics {
  total_tasks: number
  completed_tasks: number
  in_progress_tasks: number
  blocked_tasks: number
  overdue_tasks: number
  completion_rate: number
  average_task_completion_hours: number
  member_workload: Record<string, {
    assigned: number
    completed: number
    in_progress: number
    total_hours: number
  }>
  tasks_by_priority: Record<TaskPriority, number>
  tasks_by_status: Record<TaskStatus, number>
  recent_activity_count: number
  milestone_progress: Array<{
    id: string
    title: string
    progress: number
    total_tasks: number
    completed_tasks: number
  }>
}

// ============ WebSocket Types ============

export interface TeamPresenceInfo {
  user_id: string
  user_name: string
  user_avatar?: string
  status: 'online' | 'coding' | 'idle'
  current_file?: string
  last_seen: string
}

export interface TeamWebSocketMessage {
  type:
    | 'presence_update'
    | 'member_joined'
    | 'member_left'
    | 'task_updated'
    | 'file_changed'
    | 'chat_message'
    | 'file_locked'
    | 'file_unlocked'
    | 'cursor_update'
    | 'typing_indicator'
  payload: any
  timestamp: string
  sender_id?: string
}

export interface FileLock {
  file_path: string
  locked_by: string
  locked_by_name: string
  locked_at: string
}
