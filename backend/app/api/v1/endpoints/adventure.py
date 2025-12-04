"""
🎮 Project Adventure API Endpoints

Interactive project generation with game-like experience.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid

from app.modules.adventure import project_adventure, ProjectTheme, Difficulty, UIPersonality
from app.core.logging_config import logger


router = APIRouter(prefix="/adventure", tags=["Project Adventure"])


# ============================================================================
# Request/Response Models
# ============================================================================

class StartAdventureResponse(BaseModel):
    """Response for starting a new adventure"""
    session_id: str
    stage: int
    title: str
    subtitle: str
    themes: List[Dict[str, Any]]
    difficulties: List[Dict[str, Any]]


class Stage1Request(BaseModel):
    """Stage 1: Theme & Difficulty selection"""
    session_id: str
    theme: str
    difficulty: str


class Stage2Request(BaseModel):
    """Stage 2: Smart questions answers"""
    session_id: str
    answers: Dict[str, Any]


class Stage3Request(BaseModel):
    """Stage 3: Features & Personality"""
    session_id: str
    features: List[str]
    personality: str
    project_name: str


class Stage4Request(BaseModel):
    """Stage 4: College info"""
    session_id: str
    college_info: Dict[str, Any]


class SurpriseMeResponse(BaseModel):
    """Surprise project response"""
    name: str
    description: str
    theme: str
    features: List[str]
    difficulty: str
    message: str


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/start", response_model=StartAdventureResponse)
async def start_adventure():
    """
    🚀 Start a new Project Adventure!

    Returns the Stage 1 options: themes and difficulties.
    """
    session_id = str(uuid.uuid4())
    project_adventure.create_session(session_id)

    options = project_adventure.get_stage_1_options()

    return {
        "session_id": session_id,
        **options
    }


@router.post("/stage1")
async def process_stage1(request: Stage1Request):
    """
    🎯 Process Stage 1: Theme & Difficulty Selection

    Student picks their project theme and difficulty level.
    """
    try:
        result = project_adventure.process_stage_1(
            session_id=request.session_id,
            theme=request.theme,
            difficulty=request.difficulty
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stage2/{session_id}")
async def get_stage2(session_id: str):
    """
    💬 Get Stage 2: Smart Questions

    Returns the interactive questions flow.
    """
    options = project_adventure.get_stage_2_options(session_id)
    return options


@router.post("/stage2")
async def process_stage2(request: Stage2Request):
    """
    💬 Process Stage 2: Smart Questions Answers

    Process answers to the conversational questions.
    """
    result = project_adventure.process_stage_2(
        session_id=request.session_id,
        answers=request.answers
    )
    return result


@router.get("/stage3/{session_id}")
async def get_stage3(session_id: str):
    """
    ⚡ Get Stage 3: Features & Personality

    Returns available features and UI personalities.
    """
    options = project_adventure.get_stage_3_options(session_id)
    return options


@router.post("/stage3")
async def process_stage3(request: Stage3Request):
    """
    ⚡ Process Stage 3: Features & Personality Selection

    Student picks features and UI style.
    """
    result = project_adventure.process_stage_3(
        session_id=request.session_id,
        features=request.features,
        personality=request.personality,
        project_name=request.project_name
    )
    return result


@router.get("/stage4/{session_id}")
async def get_stage4(session_id: str):
    """
    🎓 Get Stage 4: College Info Form

    Returns the college info form (if applicable).
    """
    options = project_adventure.get_stage_4_options(session_id)
    return options


@router.post("/stage4")
async def process_stage4(request: Stage4Request):
    """
    🎓 Process Stage 4: College Information

    Process college details for documentation.
    """
    result = project_adventure.process_stage_4(
        session_id=request.session_id,
        college_info=request.college_info
    )
    return result


@router.get("/config/{session_id}")
async def get_generation_config(session_id: str):
    """
    📋 Get Generation Config

    Returns the complete configuration for project generation.
    """
    config = project_adventure.build_generation_config(session_id)
    if not config:
        raise HTTPException(status_code=404, detail="Session not found")
    return config


@router.get("/surprise")
async def surprise_me():
    """
    🎁 Surprise Me!

    Get a random project idea with complete configuration.
    """
    return project_adventure.get_surprise_project()


@router.get("/themes")
async def get_themes():
    """
    📚 Get All Themes

    Returns all available project themes.
    """
    return {
        "themes": [
            {
                "id": theme.value,
                "icon": config["icon"],
                "name": config["name"],
                "description": config["description"]
            }
            for theme, config in project_adventure.THEMES.items()
        ]
    }


@router.get("/difficulties")
async def get_difficulties():
    """
    📊 Get All Difficulties

    Returns all difficulty levels with details.
    """
    return {
        "difficulties": [
            {
                "id": diff.value,
                "icon": config["icon"],
                "name": config["name"],
                "description": config["description"],
                "details": {
                    "files": config["file_count"],
                    "complexity": config["complexity"],
                    "time": config["estimated_time"]
                }
            }
            for diff, config in project_adventure.DIFFICULTIES.items()
        ]
    }


@router.get("/personalities")
async def get_personalities():
    """
    🎨 Get UI Personalities

    Returns all available UI style personalities.
    """
    return {
        "personalities": [
            {
                "id": personality.value,
                "icon": config["icon"],
                "name": config["name"],
                "colors": config["colors"],
                "style": config["style"]
            }
            for personality, config in project_adventure.PERSONALITIES.items()
        ]
    }


@router.get("/features")
async def get_features():
    """
    ⚡ Get All Features

    Returns all available features by category.
    """
    return {"features": project_adventure.FEATURES}


@router.get("/achievements")
async def get_achievements():
    """
    🏆 Get All Achievements

    Returns all possible achievement badges.
    """
    return {"achievements": project_adventure.ACHIEVEMENTS}


@router.post("/stats/{session_id}")
async def get_final_stats(session_id: str, generation_result: Dict[str, Any]):
    """
    🎉 Get Final Project Stats

    Returns celebration screen with project statistics.
    """
    stats = project_adventure.get_final_stats(session_id, generation_result)
    return stats
