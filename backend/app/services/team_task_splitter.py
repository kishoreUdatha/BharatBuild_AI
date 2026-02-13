"""
AI-Powered Task Splitter for Team Collaboration

Uses Claude to intelligently split a project into tasks based on:
- Project description and requirements
- Tech stack and file structure
- Number of team members
- Workload balancing preferences

The AI analyzes the project and creates a balanced task distribution
that maximizes parallel work while respecting dependencies.
"""

import json
from typing import List, Dict, Any, Optional
from anthropic import AsyncAnthropic

from app.core.config import settings
from app.core.logging_config import logger
from app.models.project import Project
from app.models.team import TeamMember
from app.schemas.team import (
    TaskSplitResponse, SuggestedTask, TaskPriorityEnum
)


# Singleton client
_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    """Get or create Anthropic client"""
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


TASK_SPLIT_SYSTEM_PROMPT = """You are an expert project manager and software architect. Your task is to analyze a software project and split it into discrete, assignable tasks for a team of developers.

GUIDELINES FOR TASK SPLITTING:
1. Each task should be self-contained and completable by one person
2. Tasks should have clear boundaries (specific files/features)
3. Minimize dependencies between tasks to allow parallel work
4. Balance workload across team members based on complexity
5. Consider the tech stack when estimating complexity and time
6. Frontend, backend, and database tasks can often be parallelized
7. Authentication/core functionality should come early
8. Testing and integration tasks should come last

TASK STRUCTURE:
- Title: Clear, action-oriented (e.g., "Implement user authentication API")
- Description: What needs to be done, acceptance criteria
- Priority: Based on dependencies and importance
- Estimated hours: Realistic estimate for a skilled developer
- Complexity: 1-10 scale (1=trivial, 10=very complex)
- File paths: Specific files this task will create/modify
- Dependencies: Which tasks must complete first (by index)

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{
  "tasks": [
    {
      "title": "string",
      "description": "string",
      "priority": "low|medium|high|urgent",
      "estimated_hours": number,
      "complexity_score": number (1-10),
      "file_paths": ["path/to/file.ts", ...],
      "dependencies": [task_indices],
      "suggested_assignee_index": number or null
    }
  ],
  "analysis_summary": "Brief analysis of the project structure",
  "split_strategy": "Explanation of how tasks were divided"
}
"""


async def split_project_into_tasks(
    project: Project,
    team_members: List[TeamMember],
    balance_workload: bool = True,
    max_tasks: int = 20,
    include_file_mapping: bool = True
) -> TaskSplitResponse:
    """
    Use AI to split a project into tasks for team members.

    Args:
        project: The project to split
        team_members: Active team members to distribute work to
        balance_workload: Whether to balance hours across members
        max_tasks: Maximum number of tasks to create
        include_file_mapping: Whether to map specific files to tasks

    Returns:
        TaskSplitResponse with suggested tasks and distribution
    """
    client = _get_client()

    # Build project context
    tech_stack = []
    if project.tech_stack:
        if isinstance(project.tech_stack, dict):
            # Extract tech from dict
            for key, value in project.tech_stack.items():
                if isinstance(value, str):
                    tech_stack.append(value)
                elif isinstance(value, list):
                    tech_stack.extend(value)
        elif isinstance(project.tech_stack, list):
            tech_stack = project.tech_stack

    # Get file structure from plan if available
    file_structure = []
    if project.plan_json and isinstance(project.plan_json, dict):
        if "files" in project.plan_json:
            file_structure = [f.get("path", f) if isinstance(f, dict) else str(f)
                           for f in project.plan_json["files"][:50]]  # Limit to 50 files
        if "modules" in project.plan_json:
            file_structure.extend(project.plan_json["modules"])

    # Build member info for assignment suggestions (including skills)
    member_info = []
    for idx, member in enumerate(team_members):
        # Get skills if available
        skills_list = []
        if hasattr(member, 'skills') and member.skills:
            skills_list = [
                f"{s.skill_name} (L{s.proficiency_level})"
                for s in sorted(member.skills, key=lambda x: (-x.is_primary, -x.proficiency_level))[:5]
            ]

        member_info.append({
            "index": idx,
            "role": member.role.value,
            "user_id": str(member.user_id),
            "skills": skills_list
        })

    # Construct the prompt
    user_prompt = f"""Please analyze this project and split it into tasks for a team of {len(team_members)} members.

PROJECT DETAILS:
Title: {project.title}
Description: {project.description or 'No description provided'}
Mode: {project.mode.value if project.mode else 'unknown'}
Tech Stack: {', '.join(tech_stack) if tech_stack else 'Not specified'}

{"FILE STRUCTURE:" if include_file_mapping and file_structure else ""}
{chr(10).join(f"- {f}" for f in file_structure[:30]) if include_file_mapping and file_structure else ""}

TEAM MEMBERS:
{chr(10).join(f"- Member {m['index']}: {m['role']}" + (f" - Skills: {', '.join(m['skills'])}" if m.get('skills') else "") for m in member_info)}

REQUIREMENTS:
- Create up to {max_tasks} tasks maximum
- {"Balance workload evenly across members" if balance_workload else "Prioritize task clarity over balance"}
- {"Map specific files to each task" if include_file_mapping else "Focus on feature-level tasks"}
- Consider parallel work opportunities
- Identify critical path tasks that block others

Please return the JSON response with tasks and analysis."""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=TASK_SPLIT_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # Parse response
        response_text = response.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        json_str = response_text
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(json_str)

        # Build suggested tasks
        suggested_tasks = []
        total_hours = 0
        workload_distribution: Dict[str, int] = {}

        for task_data in result.get("tasks", []):
            priority_str = task_data.get("priority", "medium").lower()
            priority = TaskPriorityEnum.MEDIUM
            if priority_str == "low":
                priority = TaskPriorityEnum.LOW
            elif priority_str == "high":
                priority = TaskPriorityEnum.HIGH
            elif priority_str == "urgent":
                priority = TaskPriorityEnum.URGENT

            hours = task_data.get("estimated_hours", 4)
            total_hours += hours

            # Track workload by suggested assignee
            assignee_idx = task_data.get("suggested_assignee_index")
            if assignee_idx is not None and assignee_idx < len(team_members):
                member_id = str(team_members[assignee_idx].user_id)
                workload_distribution[member_id] = workload_distribution.get(member_id, 0) + hours

            suggested_tasks.append(SuggestedTask(
                title=task_data.get("title", "Untitled Task"),
                description=task_data.get("description", ""),
                priority=priority,
                estimated_hours=hours,
                complexity_score=min(10, max(1, task_data.get("complexity_score", 5))),
                file_paths=task_data.get("file_paths", []),
                dependencies=task_data.get("dependencies", []),
                suggested_assignee_index=assignee_idx
            ))

        logger.info(f"AI split project {project.id} into {len(suggested_tasks)} tasks, {total_hours} total hours")

        return TaskSplitResponse(
            suggested_tasks=suggested_tasks,
            total_estimated_hours=total_hours,
            workload_distribution=workload_distribution,
            analysis_summary=result.get("analysis_summary", "Project analyzed successfully"),
            split_strategy=result.get("split_strategy", "Tasks split by feature and complexity")
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        # Return a fallback with generic tasks
        return _create_fallback_split(project, team_members, max_tasks)
    except Exception as e:
        logger.error(f"Error in AI task split: {e}")
        return _create_fallback_split(project, team_members, max_tasks)


def _create_fallback_split(
    project: Project,
    team_members: List[TeamMember],
    max_tasks: int
) -> TaskSplitResponse:
    """Create a simple fallback task split when AI fails"""

    # Generic task templates based on common project structure
    generic_tasks = [
        SuggestedTask(
            title="Set up project structure and dependencies",
            description="Initialize the project with required dependencies, configure build tools, and set up the basic folder structure.",
            priority=TaskPriorityEnum.HIGH,
            estimated_hours=4,
            complexity_score=3,
            file_paths=["package.json", "tsconfig.json", "vite.config.ts"],
            dependencies=[],
            suggested_assignee_index=0
        ),
        SuggestedTask(
            title="Implement core data models",
            description="Create the core data models/types that will be used throughout the application.",
            priority=TaskPriorityEnum.HIGH,
            estimated_hours=6,
            complexity_score=5,
            file_paths=["src/types/", "src/models/"],
            dependencies=[0],
            suggested_assignee_index=1 if len(team_members) > 1 else 0
        ),
        SuggestedTask(
            title="Build main UI components",
            description="Create the primary UI components including layout, navigation, and shared elements.",
            priority=TaskPriorityEnum.MEDIUM,
            estimated_hours=8,
            complexity_score=6,
            file_paths=["src/components/"],
            dependencies=[0],
            suggested_assignee_index=2 if len(team_members) > 2 else 0
        ),
        SuggestedTask(
            title="Implement API integration",
            description="Set up API client, implement data fetching, and connect to backend services.",
            priority=TaskPriorityEnum.MEDIUM,
            estimated_hours=6,
            complexity_score=5,
            file_paths=["src/api/", "src/services/"],
            dependencies=[1],
            suggested_assignee_index=1 if len(team_members) > 1 else 0
        ),
        SuggestedTask(
            title="Add state management",
            description="Implement application state management for data flow between components.",
            priority=TaskPriorityEnum.MEDIUM,
            estimated_hours=4,
            complexity_score=6,
            file_paths=["src/store/", "src/context/"],
            dependencies=[1, 2],
            suggested_assignee_index=0
        ),
        SuggestedTask(
            title="Implement authentication flow",
            description="Add user authentication including login, logout, and session management.",
            priority=TaskPriorityEnum.HIGH,
            estimated_hours=6,
            complexity_score=7,
            file_paths=["src/auth/"],
            dependencies=[3, 4],
            suggested_assignee_index=1 if len(team_members) > 1 else 0
        ),
        SuggestedTask(
            title="Add styling and responsive design",
            description="Apply styling, theming, and ensure responsive design across devices.",
            priority=TaskPriorityEnum.LOW,
            estimated_hours=4,
            complexity_score=3,
            file_paths=["src/styles/"],
            dependencies=[2],
            suggested_assignee_index=2 if len(team_members) > 2 else 0
        ),
        SuggestedTask(
            title="Testing and bug fixes",
            description="Write unit tests, integration tests, and fix any bugs found during testing.",
            priority=TaskPriorityEnum.MEDIUM,
            estimated_hours=6,
            complexity_score=5,
            file_paths=["src/__tests__/", "tests/"],
            dependencies=[5, 6],
            suggested_assignee_index=0
        ),
    ]

    # Limit to max_tasks
    tasks = generic_tasks[:max_tasks]
    total_hours = sum(t.estimated_hours for t in tasks)

    # Calculate workload distribution
    workload_distribution: Dict[str, int] = {}
    for task in tasks:
        if task.suggested_assignee_index is not None:
            idx = task.suggested_assignee_index
            if idx < len(team_members):
                member_id = str(team_members[idx].user_id)
                workload_distribution[member_id] = workload_distribution.get(member_id, 0) + task.estimated_hours

    return TaskSplitResponse(
        suggested_tasks=tasks,
        total_estimated_hours=total_hours,
        workload_distribution=workload_distribution,
        analysis_summary="Generated generic task structure (AI service unavailable)",
        split_strategy="Tasks distributed by typical project phases"
    )
