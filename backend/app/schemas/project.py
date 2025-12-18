from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
from uuid import UUID


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
    progress: Optional[int] = 0
    current_agent: Optional[str] = None
    total_tokens: Optional[int] = 0
    total_cost: Optional[int] = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int
