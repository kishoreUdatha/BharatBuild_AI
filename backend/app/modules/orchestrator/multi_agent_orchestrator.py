from typing import Dict, Any, List, Optional
from datetime import datetime
from app.modules.agents.idea_agent import IdeaAgent
from app.modules.agents.srs_agent import SRSAgent
from app.modules.agents.code_agent import CodeAgent
from app.modules.agents.prd_agent import PRDAgent
from app.modules.agents.uml_agent import UMLAgent
from app.modules.agents.report_agent import ReportAgent
from app.modules.agents.ppt_agent import PPTAgent
from app.modules.agents.viva_agent import VivaAgent
from app.core.logging_config import logger


class MultiAgentOrchestrator:
    """Orchestrates multiple agents to complete complex tasks"""

    def __init__(self):
        self.agents = {
            "idea": IdeaAgent(),
            "srs": SRSAgent(),
            "code": CodeAgent(),
            "prd": PRDAgent(),
            "uml": UMLAgent(),
            "report": ReportAgent(),
            "ppt": PPTAgent(),
            "viva": VivaAgent(),
        }

    async def execute_student_mode(
        self,
        project_data: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute student mode: Full academic project generation

        Args:
            project_data: Project configuration
            progress_callback: Optional callback for progress updates

        Returns:
            Complete project artifacts
        """
        results = {}
        total_tokens = 0
        total_cost = 0

        try:
            # Step 1: Idea refinement (10%)
            if progress_callback:
                await progress_callback(10, "Refining project idea...")

            idea_result = await self.agents["idea"].execute({
                "description": project_data.get("description"),
                "domain": project_data.get("domain"),
                "mode": "student"
            })
            results["idea"] = idea_result
            total_tokens += idea_result.get("total_tokens", 0)

            # Step 2: SRS Generation (30%)
            if progress_callback:
                await progress_callback(30, "Generating SRS document...")

            srs_result = await self.agents["srs"].execute({
                "title": project_data.get("title"),
                "description": idea_result["content"],
                "features": project_data.get("features", []),
                "tech_stack": project_data.get("tech_stack", {}),
                "target_users": "Students and academic evaluators"
            })
            results["srs"] = srs_result
            total_tokens += srs_result.get("total_tokens", 0)

            # Step 3: Code Generation (60%)
            if progress_callback:
                await progress_callback(60, "Generating source code...")

            code_result = await self.agents["code"].execute({
                "title": project_data.get("title"),
                "requirements": srs_result["content"],
                "tech_stack": project_data.get("tech_stack", {}),
                "features": project_data.get("features", [])
            })
            results["code"] = code_result
            total_tokens += code_result.get("total_tokens", 0)

            # Step 4: UML Diagrams (70%)
            if progress_callback:
                await progress_callback(70, "Generating UML diagrams...")

            uml_result = await self.agents["uml"].execute({
                "title": project_data.get("title"),
                "srs_content": srs_result["content"],
                "features": project_data.get("features", []),
                "tech_stack": project_data.get("tech_stack", {})
            })
            results["uml"] = uml_result
            total_tokens += uml_result.get("total_tokens", 0)

            # Step 5: Project Report (85%)
            if progress_callback:
                await progress_callback(85, "Generating project report...")

            report_result = await self.agents["report"].execute({
                "title": project_data.get("title"),
                "srs_content": srs_result["content"],
                "code_summary": code_result["content"][:500],
                "tech_stack": project_data.get("tech_stack", {}),
                "features": project_data.get("features", [])
            })
            results["report"] = report_result
            total_tokens += report_result.get("total_tokens", 0)

            # Step 6: PowerPoint Presentation (92%)
            if progress_callback:
                await progress_callback(92, "Creating presentation...")

            ppt_result = await self.agents["ppt"].execute({
                "title": project_data.get("title"),
                "description": idea_result["content"][:300],
                "features": project_data.get("features", []),
                "tech_stack": project_data.get("tech_stack", {}),
                "report_summary": report_result["content"][:500]
            })
            results["ppt"] = ppt_result
            total_tokens += ppt_result.get("total_tokens", 0)

            # Step 7: Viva Q&A Preparation (96%)
            if progress_callback:
                await progress_callback(96, "Preparing viva Q&A...")

            viva_result = await self.agents["viva"].execute({
                "title": project_data.get("title"),
                "domain": project_data.get("domain"),
                "tech_stack": project_data.get("tech_stack", {}),
                "features": project_data.get("features", []),
                "srs_summary": srs_result["content"][:300],
                "report_summary": report_result["content"][:300]
            })
            results["viva"] = viva_result
            total_tokens += viva_result.get("total_tokens", 0)

            # Step 8: Finalize (100%)
            if progress_callback:
                await progress_callback(100, "Project generation complete!")

            results["metadata"] = {
                "total_tokens": total_tokens,
                "completed_at": datetime.utcnow().isoformat(),
                "mode": "student"
            }

            logger.info(f"Student mode completed. Total tokens: {total_tokens}")

            return results

        except Exception as e:
            logger.error(f"Student mode execution error: {e}")
            raise

    async def execute_developer_mode(
        self,
        project_data: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Execute developer mode: Code automation"""

        results = {}

        try:
            if progress_callback:
                await progress_callback(20, "Analyzing requirements...")

            # Generate code directly
            if progress_callback:
                await progress_callback(50, "Generating application code...")

            code_result = await self.agents["code"].execute({
                "title": project_data.get("title"),
                "requirements": project_data.get("description"),
                "tech_stack": project_data.get("tech_stack", {}),
                "features": project_data.get("features", [])
            })
            results["code"] = code_result

            if progress_callback:
                await progress_callback(100, "Code generation complete!")

            results["metadata"] = {
                "total_tokens": code_result.get("total_tokens", 0),
                "completed_at": datetime.utcnow().isoformat(),
                "mode": "developer"
            }

            return results

        except Exception as e:
            logger.error(f"Developer mode execution error: {e}")
            raise

    async def execute_founder_mode(
        self,
        project_data: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Execute founder mode: Product building"""

        results = {}
        total_tokens = 0

        try:
            # Idea refinement
            if progress_callback:
                await progress_callback(20, "Analyzing business idea...")

            idea_result = await self.agents["idea"].execute({
                "description": project_data.get("description"),
                "domain": project_data.get("industry"),
                "mode": "founder"
            })
            results["idea"] = idea_result
            total_tokens += idea_result.get("total_tokens", 0)

            # PRD Generation
            if progress_callback:
                await progress_callback(50, "Creating PRD...")

            prd_result = await self.agents["prd"].execute({
                "title": project_data.get("title"),
                "description": idea_result["content"],
                "target_market": project_data.get("target_market"),
                "features": project_data.get("features", [])
            })
            results["prd"] = prd_result
            total_tokens += prd_result.get("total_tokens", 0)

            if progress_callback:
                await progress_callback(100, "Founder package complete!")

            results["metadata"] = {
                "total_tokens": total_tokens,
                "completed_at": datetime.utcnow().isoformat(),
                "mode": "founder"
            }

            return results

        except Exception as e:
            logger.error(f"Founder mode execution error: {e}")
            raise

    async def execute_project(
        self,
        mode: str,
        project_data: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute project based on mode

        Args:
            mode: student/developer/founder
            project_data: Project configuration
            progress_callback: Optional callback

        Returns:
            Project results
        """
        if mode == "student":
            return await self.execute_student_mode(project_data, progress_callback)
        elif mode == "developer":
            return await self.execute_developer_mode(project_data, progress_callback)
        elif mode == "founder":
            return await self.execute_founder_mode(project_data, progress_callback)
        else:
            raise ValueError(f"Invalid mode: {mode}")


# Singleton instance
orchestrator = MultiAgentOrchestrator()
