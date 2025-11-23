from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str
    mode: str = Field(..., pattern="^(student|developer|founder|college)$")
    domain: Optional[str] = None
    tech_stack: Optional[Dict[str, Any]] = None
    requirements: Optional[str] = None
    framework: Optional[str] = None
    deployment_target: Optional[str] = None
    industry: Optional[str] = None
    target_market: Optional[str] = None
    features: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    mode: str
    status: str
    progress: int
    current_agent: Optional[str]
    total_tokens: int
    total_cost: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int
