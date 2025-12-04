"""
Pydantic schemas for Bolt.new endpoints
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import datetime


class ProjectFileSchema(BaseModel):
    """Project file schema"""
    path: str = Field(..., description="File path relative to project root")
    content: Optional[str] = Field(None, description="File content")
    language: str = Field(default="plaintext", description="Programming language")
    type: Literal["file", "folder"] = Field(default="file", description="File or folder")


class BoltChatRequest(BaseModel):
    """Request for Bolt chat streaming"""
    message: str = Field(..., description="User message/prompt")
    files: List[ProjectFileSchema] = Field(default_factory=list, description="Project files")
    project_name: str = Field(default="Project", description="Project name")
    selected_file: Optional[str] = Field(None, description="Currently selected file path")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous messages in conversation"
    )
    max_tokens: int = Field(default=4000, description="Max tokens to generate")
    temperature: float = Field(default=0.7, description="Temperature for generation")


class BoltChatResponse(BaseModel):
    """Response from Bolt chat"""
    content: str = Field(..., description="AI response content")
    model: str = Field(..., description="Model used")
    input_tokens: int = Field(..., description="Input tokens")
    output_tokens: int = Field(..., description="Output tokens")
    total_tokens: int = Field(..., description="Total tokens")


class ApplyPatchRequest(BaseModel):
    """Request to apply a unified diff patch"""
    file_path: str = Field(..., description="Path to file to patch")
    patch: str = Field(..., description="Unified diff patch")
    original_content: str = Field(..., description="Original file content")
    project_id: Optional[int] = Field(None, description="Project ID (if saving to DB)")


class ApplyPatchResponse(BaseModel):
    """Response from applying patch"""
    success: bool = Field(..., description="Whether patch was successful")
    new_content: Optional[str] = Field(None, description="New file content after patch")
    error: Optional[str] = Field(None, description="Error message if failed")
    conflicts: Optional[List[str]] = Field(None, description="Conflict details if any")


class CreateFileRequest(BaseModel):
    """Request to create a new file"""
    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")
    language: str = Field(default="plaintext", description="Programming language")
    project_id: Optional[str] = Field(None, description="Project ID (UUID)")


class UpdateFileRequest(BaseModel):
    """Request to update a file"""
    path: str = Field(..., description="File path")
    content: str = Field(..., description="New file content")
    project_id: Optional[str] = Field(None, description="Project ID (UUID)")


class DeleteFileRequest(BaseModel):
    """Request to delete a file"""
    path: str = Field(..., description="File path")
    project_id: Optional[str] = Field(None, description="Project ID (UUID)")


class FileOperationResponse(BaseModel):
    """Generic file operation response"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Status message")
    file: Optional[ProjectFileSchema] = Field(None, description="File data if applicable")


class ExecuteCodeRequest(BaseModel):
    """Request to execute code in sandbox"""
    files: List[ProjectFileSchema] = Field(..., description="Project files to execute")
    command: str = Field(default="npm run dev", description="Command to run")
    timeout: int = Field(default=30, description="Timeout in seconds")
    environment: Literal["node", "python", "react"] = Field(
        default="node",
        description="Execution environment"
    )


class ExecuteCodeResponse(BaseModel):
    """Response from code execution"""
    success: bool = Field(..., description="Whether execution was successful")
    output: str = Field(..., description="Standard output")
    error: Optional[str] = Field(None, description="Error output if any")
    exit_code: int = Field(..., description="Process exit code")
    execution_time: float = Field(..., description="Execution time in seconds")


class StreamEvent(BaseModel):
    """Server-sent event for streaming"""
    type: Literal["status", "content", "file_change", "error", "done"] = Field(
        ...,
        description="Event type"
    )
    data: Dict = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class VersionControlCommit(BaseModel):
    """Version control commit"""
    id: str = Field(..., description="Commit ID")
    message: str = Field(..., description="Commit message")
    author: Literal["user", "ai"] = Field(..., description="Commit author")
    timestamp: datetime = Field(..., description="Commit timestamp")
    file_changes: List[Dict] = Field(..., description="File changes in this commit")


class BoltProjectSchema(BaseModel):
    """Bolt project schema"""
    id: Optional[int] = Field(None, description="Project ID")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    files: List[ProjectFileSchema] = Field(default_factory=list, description="Project files")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    user_id: Optional[int] = Field(None, description="Owner user ID")


class ExportProjectRequest(BaseModel):
    """Request to export project as ZIP"""
    project_id: str = Field(..., description="Project ID to export (UUID)")
    include_node_modules: bool = Field(default=False, description="Include node_modules")
    include_dot_files: bool = Field(default=True, description="Include dot files")
    include_git_folder: bool = Field(default=False, description="Include .git folder")


class BulkSyncFilesRequest(BaseModel):
    """Request to sync multiple files at once"""
    project_id: str = Field(..., description="Project ID (UUID)")
    files: List[ProjectFileSchema] = Field(..., description="Files to sync")


class BulkSyncFilesResponse(BaseModel):
    """Response from bulk file sync"""
    success: bool = Field(..., description="Whether sync was successful")
    files_created: int = Field(default=0, description="Number of files created")
    files_updated: int = Field(default=0, description="Number of files updated")
    files_deleted: int = Field(default=0, description="Number of files deleted")
    message: str = Field(..., description="Status message")


class GetProjectFilesResponse(BaseModel):
    """Response with project files"""
    success: bool = Field(..., description="Whether request was successful")
    project_id: str = Field(..., description="Project ID")
    files: List[ProjectFileSchema] = Field(default_factory=list, description="Project files")
    total_files: int = Field(default=0, description="Total number of files")


# Project Generation Schemas (Bolt.new Workflow)

class GenerateProjectRequest(BaseModel):
    """Request to generate a complete project using Bolt.new workflow"""
    description: str = Field(..., description="Project description/request")
    project_name: Optional[str] = Field(None, description="Optional project name")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Additional metadata")


class GenerateProjectResponse(BaseModel):
    """Response from project generation"""
    success: bool = Field(..., description="Whether generation was successful")
    project_id: str = Field(..., description="Generated project ID")
    plan: Dict = Field(..., description="Project plan from Planner Agent")
    total_steps: int = Field(..., description="Total implementation steps")
    steps_completed: int = Field(..., description="Steps successfully completed")
    total_files_created: int = Field(..., description="Total files created")
    total_commands_executed: int = Field(..., description="Total commands executed")
    files_created: List[Dict] = Field(..., description="List of all files created")
    commands_executed: List[Dict] = Field(..., description="List of all commands executed")
    started_at: str = Field(..., description="Start timestamp")
    completed_at: str = Field(..., description="Completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")


class GenerateProjectStreamEvent(BaseModel):
    """Streaming event for project generation"""
    type: Literal["progress", "step_start", "step_complete", "file_created", "command_executed", "done", "error"] = Field(
        ...,
        description="Event type"
    )
    data: Dict = Field(..., description="Event data")
    timestamp: str = Field(..., description="Event timestamp")
