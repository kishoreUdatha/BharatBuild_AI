from celery import Task
from sqlalchemy import select
from typing import Dict, Any
import asyncio
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.project import Project, ProjectStatus
from app.models.document import Document, DocumentType
from app.models.agent_task import AgentTask, AgentTaskStatus, AgentType
from app.modules.orchestrator.dynamic_orchestrator import dynamic_orchestrator
from app.utils.document_generator import document_generator
from app.utils.storage_client import storage_client
from app.core.logging_config import logger
from app.core.config import settings


class ProjectExecutionTask(Task):
    """Custom Celery task with database session management"""

    def __init__(self):
        self.db_session = None

    async def async_execute_project(self, project_id: str):
        """Async project execution logic"""
        async with AsyncSessionLocal() as db:
            try:
                # Get project
                result = await db.execute(
                    select(Project).where(Project.id == project_id)
                )
                project = result.scalar_one_or_none()

                if not project:
                    logger.error(f"Project not found: {project_id}")
                    return

                # Update project status
                project.status = ProjectStatus.PROCESSING
                project.progress = 0
                await db.commit()

                # Prepare project data
                project_data = {
                    "title": project.title,
                    "description": project.description,
                    "mode": project.mode.value,
                    "domain": project.domain,
                    "tech_stack": project.tech_stack or {},
                    "features": project.config.get("features", []) if project.config else [],
                    "requirements": project.requirements
                }

                # Progress callback
                async def update_progress(progress: int, message: str):
                    project.progress = progress
                    project.current_agent = message
                    await db.commit()
                    logger.info(f"Project {project_id}: {progress}% - {message}")

                # Execute dynamic orchestrator workflow
                # Collect results from async generator
                results = {"files_created": [], "metadata": {}}
                async for event in dynamic_orchestrator.execute_workflow(
                    user_request=project.description,
                    project_id=str(project.id),
                    workflow_name="bolt_standard",
                    metadata={"mode": project.mode.value, "project_type": "Academic" if project.mode.value == "student" else "Commercial"}
                ):
                    # Update progress based on events
                    if hasattr(event, 'type'):
                        event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
                        if event_type == "status":
                            await update_progress(project.progress + 5, event.data.get("message", ""))
                        elif event_type == "file_operation":
                            results["files_created"].append(event.data)
                        elif event_type == "complete":
                            results["metadata"] = event.data

                # Save results
                total_tokens = results.get("metadata", {}).get("total_tokens", 0)
                project.total_tokens = total_tokens

                # Calculate cost (example: Haiku pricing)
                from app.utils.claude_client import claude_client
                project.total_cost = claude_client.calculate_cost_in_paise(
                    total_tokens // 2,  # Approximate input
                    total_tokens // 2,  # Approximate output
                    "haiku"
                )

                # Generate and save documents
                await self._save_documents(db, project, results)

                # Update project as completed
                project.status = ProjectStatus.COMPLETED
                project.progress = 100
                project.current_agent = None
                project.completed_at = datetime.utcnow()
                await db.commit()

                logger.info(f"Project {project_id} completed successfully")

            except Exception as e:
                logger.error(f"Error executing project {project_id}: {e}", exc_info=True)
                project.status = ProjectStatus.FAILED
                project.current_agent = f"Error: {str(e)}"
                await db.commit()

    async def _save_documents(self, db, project: Project, results: Dict[str, Any]):
        """Save generated documents to storage and database"""
        try:
            # Save SRS
            if "srs" in results:
                srs_content = results["srs"].get("content", "")
                doc_path = document_generator.generate_srs_docx(
                    srs_content,
                    project.title
                )

                # Upload to storage
                object_name = f"projects/{project.id}/srs.docx"
                url = storage_client.upload_file(doc_path, object_name)

                # Save to database
                doc = Document(
                    project_id=project.id,
                    title="Software Requirements Specification",
                    doc_type=DocumentType.SRS,
                    content=srs_content,
                    file_url=url,
                    agent_generated=True
                )
                db.add(doc)

            # Save Code
            if "code" in results:
                code_content = results["code"].get("content", "")
                doc = Document(
                    project_id=project.id,
                    title="Generated Source Code",
                    doc_type=DocumentType.CODE,
                    content=code_content,
                    agent_generated=True
                )
                db.add(doc)

            # Save PRD
            if "prd" in results:
                prd_content = results["prd"].get("content", "")
                doc_path = document_generator.generate_report_docx(
                    prd_content,
                    project.title
                )

                object_name = f"projects/{project.id}/prd.docx"
                url = storage_client.upload_file(doc_path, object_name)

                doc = Document(
                    project_id=project.id,
                    title="Product Requirements Document",
                    doc_type=DocumentType.PRD,
                    content=prd_content,
                    file_url=url,
                    agent_generated=True
                )
                db.add(doc)

            await db.commit()
            logger.info(f"Documents saved for project {project.id}")

        except Exception as e:
            logger.error(f"Error saving documents: {e}")


@celery_app.task(bind=True, base=ProjectExecutionTask)
def execute_project_task(self, project_id: str):
    """
    Execute project generation (Celery task)

    Args:
        project_id: UUID of the project
    """
    logger.info(f"Starting project execution: {project_id}")

    # Run async code
    loop = asyncio.get_event_loop()
    loop.run_until_complete(self.async_execute_project(project_id))

    return {"project_id": project_id, "status": "completed"}


@celery_app.task
def cleanup_old_files():
    """Periodic task to clean up old temporary files"""
    from pathlib import Path
    import time
    import os

    temp_dir = Path(__file__).parent.parent.parent / "temp"
    current_time = time.time()
    days_old = settings.PROJECT_CLEANUP_DAYS  # From .env

    if temp_dir.exists():
        for file_path in temp_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > (days_old * 86400):  # 7 days in seconds
                    try:
                        file_path.unlink()
                        logger.info(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {e}")

    return {"cleaned": "old_files"}
