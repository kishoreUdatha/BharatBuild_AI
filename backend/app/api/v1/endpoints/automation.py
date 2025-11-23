"""
Automation API Endpoints
Complete Bolt.new-style automation with Claude AI
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
import json
from datetime import datetime

from app.core.logging_config import logger
from app.modules.auth.dependencies import get_current_user
from app.models.user import User
from app.modules.automation import automation_engine
from app.modules.agents import orchestrator, WorkflowMode


router = APIRouter(prefix="/automation", tags=["Automation"])


# Request/Response Models
class ProjectFile(BaseModel):
    path: str
    content: Optional[str] = None
    language: Optional[str] = None
    type: str = "file"  # "file" or "directory"


class AutomationRequest(BaseModel):
    project_id: str
    user_prompt: str
    project_files: List[ProjectFile] = []
    auto_fix_errors: bool = True
    tech_stack: Optional[str] = None  # "react", "python", "java", etc.


class CreateProjectRequest(BaseModel):
    name: str
    tech_stack: str
    description: Optional[str] = None


class MultiAgentRequest(BaseModel):
    project_id: str
    user_prompt: str
    mode: str = "full"  # "full", "code_only", "debug_only", "explain_only", "custom"
    custom_agents: Optional[List[str]] = None  # For custom mode
    include_tests: bool = True
    include_docs: bool = True
    include_academic_reports: bool = True  # SRS, SDS, Testing Plan, Project Report


@router.post("/execute/stream")
async def execute_automation_stream(
    request: AutomationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Main automation endpoint - processes user requests with full automation

    This endpoint:
    1. Sends request to Claude
    2. Parses Claude's response for actions
    3. Executes actions (files, packages, builds, preview)
    4. Streams all progress events to frontend
    5. Auto-fixes errors if encountered

    Returns:
        Server-Sent Events stream with progress updates
    """

    async def event_generator():
        try:
            logger.info(f"Starting automation for project {request.project_id}")

            # Convert Pydantic models to dicts
            project_files = [file.dict() for file in request.project_files]

            # Process request through automation engine
            async for event in automation_engine.process_user_request(
                project_id=request.project_id,
                user_prompt=request.user_prompt,
                project_files=project_files,
                auto_fix_errors=request.auto_fix_errors
            ):
                # Send event to frontend as SSE
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.error(f"Automation error: {e}", exc_info=True)
            error_event = {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/projects/create")
async def create_project(
    request: CreateProjectRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new project with automation

    This will:
    1. Create project directory
    2. Generate initial files based on tech stack
    3. Set up package.json/requirements.txt
    4. Initialize git repo
    """
    try:
        from app.modules.automation import file_manager
        import uuid

        # Generate project ID
        project_id = f"user-{current_user.id}-{uuid.uuid4().hex[:8]}"

        # Create project
        result = await file_manager.create_project(project_id, request.name)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error"))

        # Generate initial structure based on tech stack
        initial_prompt = f"Create a new {request.tech_stack} project structure for: {request.description or request.name}"

        return {
            "success": True,
            "project_id": project_id,
            "name": request.name,
            "tech_stack": request.tech_stack,
            "path": result["path"],
            "message": "Project created successfully",
            "next_step": f"Use /automation/execute/stream with prompt: {initial_prompt}"
        }

    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/files")
async def get_project_files(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get file tree for a project"""
    try:
        from app.modules.automation import file_manager

        files = await file_manager.get_file_tree(project_id)

        return {
            "success": True,
            "project_id": project_id,
            "files": files
        }

    except Exception as e:
        logger.error(f"Error getting project files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/files/{file_path:path}")
async def get_file_content(
    project_id: str,
    file_path: str,
    current_user: User = Depends(get_current_user)
):
    """Get content of a specific file"""
    try:
        from app.modules.automation import file_manager

        content = await file_manager.read_file(project_id, file_path)

        if content is None:
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "success": True,
            "path": file_path,
            "content": content
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/build")
async def build_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Build a project"""
    try:
        from app.modules.automation import build_system

        result = await build_system.build(project_id)

        return {
            "success": result["success"],
            "build_tool": result.get("build_tool"),
            "output": result.get("output"),
            "error": result.get("error"),
            "build_time": result.get("build_time")
        }

    except Exception as e:
        logger.error(f"Error building project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/build/stream")
async def build_project_stream(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Build a project with streaming output"""

    async def build_generator():
        try:
            from app.modules.automation import build_system

            async for line in build_system.build_stream(project_id):
                event = {
                    "type": "build_output",
                    "line": line,
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.error(f"Build error: {e}")
            error_event = {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        build_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.post("/projects/{project_id}/preview/start")
async def start_preview_server(
    project_id: str,
    port: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Start preview/dev server"""
    try:
        from app.modules.automation import preview_server_manager

        result = await preview_server_manager.start_server(project_id, port)

        return result

    except Exception as e:
        logger.error(f"Error starting preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/preview/stop")
async def stop_preview_server(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stop preview/dev server"""
    try:
        from app.modules.automation import preview_server_manager

        result = await preview_server_manager.stop_server(project_id)

        return result

    except Exception as e:
        logger.error(f"Error stopping preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/preview/status")
async def get_preview_status(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get preview server status"""
    try:
        from app.modules.automation import preview_server_manager

        status = await preview_server_manager.get_server_status(project_id)

        return status

    except Exception as e:
        logger.error(f"Error getting preview status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/install")
async def install_packages(
    project_id: str,
    packages: List[str],
    manager: Optional[str] = None,
    dev: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Install packages"""
    try:
        from app.modules.automation import package_manager
        from app.modules.automation.package_manager import PackageManagerType

        manager_enum = PackageManagerType(manager) if manager else None

        result = await package_manager.install(
            project_id=project_id,
            packages=packages,
            manager=manager_enum,
            dev=dev
        )

        return result

    except Exception as e:
        logger.error(f"Error installing packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a project"""
    try:
        from app.modules.automation import file_manager, preview_server_manager

        # Stop preview server if running
        await preview_server_manager.stop_server(project_id)

        # Delete project files
        result = await file_manager.delete_project(project_id)

        return result

    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-agent/execute/stream")
async def execute_multi_agent_stream(
    request: MultiAgentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Multi-Agent System Endpoint - Full AI-powered project generation

    This endpoint uses specialized AI agents to:
    1. Planner Agent - Understand and plan the project
    2. Architect Agent - Design system architecture and database
    3. Coder Agent - Generate complete production-ready code
    4. Tester Agent - Create comprehensive test suites
    5. Explainer Agent - Generate code documentation
    6. Document Generator - Create academic reports (SRS, SDS, etc.)

    Returns:
        Server-Sent Events stream with progress from each agent
    """

    async def event_generator():
        try:
            logger.info(f"[Multi-Agent] Starting workflow for project {request.project_id}")

            # Determine agents to run
            agents_to_run = []

            if request.mode == "custom" and request.custom_agents:
                agents_to_run = request.custom_agents
            else:
                # Build agent list based on options
                agents_to_run = ["planner", "architect", "coder"]

                if request.include_tests:
                    agents_to_run.append("tester")

                if request.include_docs:
                    agents_to_run.append("explainer")

                if request.include_academic_reports:
                    agents_to_run.append("document_generator")

            # Execute multi-agent workflow
            async for event in orchestrator.execute_workflow(
                project_id=request.project_id,
                user_request=request.user_prompt,
                mode=WorkflowMode(request.mode) if request.mode != "custom" else WorkflowMode.CUSTOM,
                custom_agents=agents_to_run if request.mode == "custom" else None
            ):
                # Map agent events to frontend format
                frontend_event = map_agent_event_to_frontend(event)
                yield f"data: {json.dumps(frontend_event)}\n\n"

        except Exception as e:
            logger.error(f"[Multi-Agent] Error: {e}", exc_info=True)
            error_event = {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


def map_agent_event_to_frontend(agent_event: dict) -> dict:
    """Map multi-agent events to frontend-compatible format"""

    event_type = agent_event.get("type")

    # Agent start event
    if event_type == "agent_start":
        return {
            "type": "status",
            "status": f"🤖 {agent_event['agent'].title()} Agent Working...",
            "agent": agent_event["agent"],
            "timestamp": agent_event["timestamp"]
        }

    # Agent complete event
    elif event_type == "agent_complete":
        agent_name = agent_event["agent"]
        result = agent_event.get("result", {})

        # Extract useful info from result
        response_text = ""
        if agent_name == "planner":
            plan = result.get("plan", {})
            response_text = f"✅ Project Plan Created: {plan.get('project_understanding', {}).get('name', 'Project')}"

        elif agent_name == "architect":
            arch = result.get("architecture", {})
            response_text = f"✅ Architecture Designed with {len(arch.get('database_schema', {}).get('entities', []))} database tables"

        elif agent_name == "coder":
            files = result.get("files_created", [])
            response_text = f"✅ Generated {len(files)} code files"

        elif agent_name == "tester":
            tests = result.get("test_files_created", [])
            response_text = f"✅ Created {len(tests)} test files"

        elif agent_name == "explainer":
            docs = result.get("files_created", [])
            response_text = f"✅ Generated {len(docs)} documentation files"

        elif agent_name == "document_generator":
            docs = result.get("files_created", [])
            response_text = f"✅ Generated {len(docs)} academic documents (SRS, SDS, Reports)"

        return {
            "type": "message",
            "role": "assistant",
            "content": response_text,
            "agent": agent_name,
            "timestamp": agent_event["timestamp"]
        }

    # Agent error event
    elif event_type == "agent_error":
        return {
            "type": "error",
            "message": f"❌ {agent_event['agent'].title()} Agent Error: {agent_event['error']}",
            "agent": agent_event["agent"],
            "timestamp": agent_event["timestamp"]
        }

    # Workflow complete event
    elif event_type == "workflow_complete":
        workflow_state = agent_event.get("workflow_state", {})

        summary_parts = []
        if workflow_state.get("plan"):
            summary_parts.append("✅ Project Planned")
        if workflow_state.get("architecture"):
            summary_parts.append("✅ Architecture Designed")
        if workflow_state.get("code_files"):
            summary_parts.append(f"✅ {len(workflow_state['code_files'])} Files Generated")
        if workflow_state.get("test_results"):
            summary_parts.append("✅ Tests Created")
        if workflow_state.get("documentation"):
            summary_parts.append("✅ Documentation Complete")

        return {
            "type": "message",
            "role": "assistant",
            "content": f"🎉 Project Complete!\n\n" + "\n".join(summary_parts),
            "timestamp": agent_event["timestamp"]
        }

    # Workflow error event
    elif event_type == "workflow_error":
        return {
            "type": "error",
            "message": f"❌ Workflow Error: {agent_event['error']}",
            "timestamp": agent_event["timestamp"]
        }

    # Default: pass through
    return agent_event


@router.get("/multi-agent/agents")
async def list_agents(current_user: User = Depends(get_current_user)):
    """List all available AI agents and their capabilities"""
    agents = orchestrator.list_agents()
    return {
        "success": True,
        "agents": agents
    }
