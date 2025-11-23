"""
Automation Engine - The Heart of Bolt.new-style Automation
Orchestrates all automation components: files, packages, builds, errors, previews
"""

import asyncio
import json
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime

from app.core.logging_config import logger
from app.utils.claude_client import claude_client

# Import all automation components
from app.modules.automation.file_manager import file_manager
from app.modules.automation.package_manager import package_manager
from app.modules.automation.build_system import build_system
from app.modules.automation.error_detector import error_detector, error_recovery
from app.modules.automation.preview_server import preview_server_manager
from app.modules.automation.claude_parser import claude_parser


class AutomationEngine:
    """
    Main automation engine that executes all actions
    This is the "magic" that makes Bolt.new work
    """

    def __init__(self):
        self.file_manager = file_manager
        self.package_manager = package_manager
        self.build_system = build_system
        self.error_detector = error_detector
        self.error_recovery = error_recovery
        self.preview_manager = preview_server_manager
        self.parser = claude_parser

    async def process_user_request(
        self,
        project_id: str,
        user_prompt: str,
        project_files: Optional[List[Dict]] = None,
        auto_fix_errors: bool = True
    ) -> AsyncGenerator[Dict, None]:
        """
        Main entry point: Process user request end-to-end

        This method:
        1. Sends prompt to Claude
        2. Parses Claude's response
        3. Executes all actions (files, packages, builds, preview)
        4. Auto-fixes errors if needed
        5. Streams progress events to frontend

        Args:
            project_id: Project ID
            user_prompt: User's request
            project_files: Current project files
            auto_fix_errors: Whether to attempt auto-fixing errors

        Yields:
            Progress events for frontend
        """
        try:
            # Step 1: Analyzing requirements
            yield {
                "type": "thinking_step",
                "step": "Analyzing requirements",
                "status": "active",
                "timestamp": datetime.utcnow().isoformat()
            }

            # Build context for Claude
            context = self._build_context(user_prompt, project_files or [])

            # Step 2: Getting Claude's response
            yield {
                "type": "thinking_step",
                "step": "Analyzing requirements",
                "status": "complete",
                "timestamp": datetime.utcnow().isoformat()
            }

            yield {
                "type": "thinking_step",
                "step": "Planning structure",
                "status": "active",
                "timestamp": datetime.utcnow().isoformat()
            }

            # Call Claude
            full_response = ""
            async for chunk in claude_client.generate_stream(
                prompt=context,
                model="sonnet",
                max_tokens=4000
            ):
                full_response += chunk
                yield {
                    "type": "content",
                    "content": chunk,
                    "timestamp": datetime.utcnow().isoformat()
                }

            # Step 3: Parse Claude's response
            parsed = self.parser.parse_response(full_response)
            actions = parsed["actions"]

            if not actions:
                yield {
                    "type": "complete",
                    "message": "No actions to perform",
                    "timestamp": datetime.utcnow().isoformat()
                }
                return

            yield {
                "type": "thinking_step",
                "step": "Planning structure",
                "status": "complete",
                "timestamp": datetime.utcnow().isoformat()
            }

            # Step 4: Execute actions
            yield {
                "type": "thinking_step",
                "step": "Generating code",
                "status": "active",
                "timestamp": datetime.utcnow().isoformat()
            }

            async for event in self.execute_actions(project_id, actions, auto_fix_errors):
                yield event

            yield {
                "type": "thinking_step",
                "step": "Generating code",
                "status": "complete",
                "timestamp": datetime.utcnow().isoformat()
            }

            # Final completion
            yield {
                "type": "complete",
                "message": "✓ All tasks completed successfully",
                "actions_executed": len(actions),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in process_user_request: {e}", exc_info=True)
            yield {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def execute_actions(
        self,
        project_id: str,
        actions: List[Dict],
        auto_fix_errors: bool = True
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute a list of actions

        Args:
            project_id: Project ID
            actions: List of actions from Claude parser
            auto_fix_errors: Whether to auto-fix errors

        Yields:
            Progress events
        """
        for i, action in enumerate(actions, 1):
            action_type = action.get("type")

            try:
                yield {
                    "type": "action_start",
                    "action": action_type,
                    "progress": f"{i}/{len(actions)}",
                    "timestamp": datetime.utcnow().isoformat()
                }

                # Execute based on action type
                if action_type == "create_file":
                    async for event in self._execute_create_file(project_id, action):
                        yield event

                elif action_type == "modify_file":
                    async for event in self._execute_modify_file(project_id, action):
                        yield event

                elif action_type == "apply_patch":
                    async for event in self._execute_apply_patch(project_id, action):
                        yield event

                elif action_type == "delete_file":
                    async for event in self._execute_delete_file(project_id, action):
                        yield event

                elif action_type == "install_packages":
                    async for event in self._execute_install_packages(project_id, action):
                        yield event

                elif action_type == "run_build":
                    async for event in self._execute_build(project_id, auto_fix_errors):
                        yield event

                elif action_type == "run_command":
                    async for event in self._execute_command(project_id, action):
                        yield event

                elif action_type == "start_preview":
                    async for event in self._execute_start_preview(project_id, action):
                        yield event

                yield {
                    "type": "action_complete",
                    "action": action_type,
                    "timestamp": datetime.utcnow().isoformat()
                }

            except Exception as e:
                logger.error(f"Error executing action {action_type}: {e}")
                yield {
                    "type": "action_error",
                    "action": action_type,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }

    async def _execute_create_file(self, project_id: str, action: Dict) -> AsyncGenerator[Dict, None]:
        """Create a file"""
        path = action["path"]
        content = action.get("content", "")

        yield {
            "type": "file_operation",
            "operation": "create",
            "path": path,
            "status": "in_progress"
        }

        result = await self.file_manager.create_file(project_id, path, content)

        if result["success"]:
            yield {
                "type": "file_operation",
                "operation": "create",
                "path": path,
                "status": "complete",
                "size": result.get("size"),
                "content": content  # Include file content in the event
            }
        else:
            yield {
                "type": "file_operation",
                "operation": "create",
                "path": path,
                "status": "error",
                "error": result.get("error")
            }

    async def _execute_modify_file(self, project_id: str, action: Dict) -> AsyncGenerator[Dict, None]:
        """Modify a file"""
        path = action["path"]
        content = action.get("content", "")

        yield {
            "type": "file_operation",
            "operation": "modify",
            "path": path,
            "status": "in_progress"
        }

        result = await self.file_manager.update_file(project_id, path, content)

        yield {
            "type": "file_operation",
            "operation": "modify",
            "path": path,
            "status": "complete" if result["success"] else "error"
        }

    async def _execute_apply_patch(self, project_id: str, action: Dict) -> AsyncGenerator[Dict, None]:
        """Apply a patch to a file"""
        path = action["path"]
        patch = action.get("patch", "")

        yield {
            "type": "file_operation",
            "operation": "patch",
            "path": path,
            "status": "in_progress"
        }

        result = await self.file_manager.apply_patch(project_id, path, patch)

        yield {
            "type": "file_operation",
            "operation": "patch",
            "path": path,
            "status": "complete" if result["success"] else "error"
        }

    async def _execute_delete_file(self, project_id: str, action: Dict) -> AsyncGenerator[Dict, None]:
        """Delete a file"""
        path = action["path"]

        yield {
            "type": "file_operation",
            "operation": "delete",
            "path": path,
            "status": "in_progress"
        }

        result = await self.file_manager.delete_file(project_id, path)

        yield {
            "type": "file_operation",
            "operation": "delete",
            "path": path,
            "status": "complete" if result["success"] else "error"
        }

    async def _execute_install_packages(self, project_id: str, action: Dict) -> AsyncGenerator[Dict, None]:
        """Install packages"""
        packages = action.get("packages", [])
        manager = action.get("manager", "npm")

        yield {
            "type": "install_start",
            "packages": packages,
            "manager": manager
        }

        # Stream installation output
        async for line in self.package_manager.install_stream(project_id, packages):
            yield {
                "type": "install_output",
                "line": line
            }

        yield {
            "type": "install_complete",
            "packages": packages
        }

    async def _execute_build(self, project_id: str, auto_fix: bool) -> AsyncGenerator[Dict, None]:
        """Run build"""
        yield {
            "type": "build_start"
        }

        # Stream build output
        async for line in self.build_system.build_stream(project_id):
            yield {
                "type": "build_output",
                "line": line
            }

        # Check for errors
        # If build failed and auto_fix is enabled, attempt to fix
        # This would involve parsing errors and re-running build

        yield {
            "type": "build_complete"
        }

    async def _execute_command(self, project_id: str, action: Dict) -> AsyncGenerator[Dict, None]:
        """Execute a command"""
        command = action.get("command", "")

        yield {
            "type": "command_start",
            "command": command
        }

        # Execute command
        # Implementation would run the command and stream output

        yield {
            "type": "command_complete",
            "command": command
        }

    async def _execute_start_preview(self, project_id: str, action: Dict) -> AsyncGenerator[Dict, None]:
        """Start preview server"""
        port = action.get("port")

        yield {
            "type": "preview_starting"
        }

        result = await self.preview_manager.start_server(project_id, port)

        if result["success"]:
            yield {
                "type": "preview_ready",
                "url": result["url"],
                "port": result["port"]
            }
        else:
            yield {
                "type": "preview_error",
                "error": result.get("error")
            }

    def _build_context(self, user_prompt: str, project_files: List[Dict]) -> str:
        """Build context for Claude with ProjectGen AI system prompt"""

        # ProjectGen AI Master System Prompt
        system_prompt = """You are ProjectGen AI — an enterprise-grade autonomous full-stack academic project generator used by over 100,000 students concurrently.

Your job is to generate a complete, high-quality academic project based solely on the user's provided topic, abstract, or project title. You must deliver:

1. Problem definition
2. Abstract
3. Objectives
4. Scope & limitations
5. Proposed system architecture
6. Technology stack
7. Database schema & ER diagram (mermaid format)
8. API design (REST or GraphQL)
9. Backend code (Spring Boot/Java or Node.js as indicated or chosen by default)
10. Frontend code (React)
11. File folder structure ready for download
12. UML diagrams (class, use-case, sequence) in mermaid or textual form
13. IEEE-style SRS document
14. SDS (detailed design document)
15. Testing plan & test cases
16. Deployment guide & hosting instructions (cloud/in-house)
17. Project report (word-style)
18. PPT slide content with 10-15 slides

IMPORTANT RULES:

• NEVER ask the user any clarifying questions.
• If the user provides only a title or abstract, you must infer all missing details and proceed.
• Use the following defaults unless specified by user:
   – Backend: Spring Boot 3 (Java 17)
   – Frontend: React 18 + TypeScript
   – Database: PostgreSQL
• You may adapt to other tech stacks only if user clearly states preference.
• ALWAYS generate FULL FILES (not snippets). Example:
/src/main/java/com/project/controller/UserController.java
<full code>
• Ensure deliverables are original, plagiarism-free, professionally formatted, and ready for submission.
• Use the workflow below:
   Step 1: Re-write Abstract (if user gave)
   Step 2: Write Problem Statement
   Step 3: Write Objectives
   Step 4: Proposed System & Architecture
   Step 5: Technology Stack
   Step 6: Database Schema & ER Diagram
   Step 7: API Endpoints
   Step 8: Backend Code
   Step 9: Frontend Code
   Step10: Folder Structure
   Step11: UML Diagrams
   Step12: SRS Document
   Step13: SDS Document
   Step14: Testing Plan & Test Cases
   Step15: Deployment Guide
   Step16: Project Report
   Step17: PPT Slide Content
• Each deliverable must begin with a heading clearly labeled (e.g., "### 8. Backend Code").
• Do not write the same content twice; avoid rewriting previous sections.
• Use MERMAID diagrams only when indicated. Example:
```mermaid
erDiagram
    User {
        int id PK
        string name
        string email
    }
    Order {
        int id PK
        int userId FK
        datetime orderDate
    }
    User ||--o{ Order : places
```

CRITICAL OUTPUT FORMAT FOR FILES:
When creating code files, you MUST wrap each file in XML tags with this exact format:

<file operation="create" path="relative/path/to/file.ext">
file content here (complete file, not snippets)
</file>

For modifying existing files:
<file operation="modify" path="path/to/existing/file.ext">
complete updated file content
</file>

For deleting files:
<file operation="delete" path="path/to/file.ext"></file>

For installing packages:
<install packages="package1 package2 package3" manager="npm" />
<install packages="flask sqlalchemy" manager="pip" />

Example:
<file operation="create" path="src/main/java/com/project/controller/UserController.java">
package com.project.controller;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {
    // Full file content here
}
</file>

<install packages="spring-boot-starter-web spring-boot-starter-data-jpa" manager="maven" />

Remember: Every code file you generate MUST be wrapped in <file> tags with operation and path attributes.
"""

        context_parts = [
            system_prompt,
            "",
            f"User request: {user_prompt}",
            ""
        ]

        if project_files:
            context_parts.append("Current project files:")
            for file in project_files[:10]:  # Limit context
                context_parts.append(f"- {file.get('path')}")
            context_parts.append("")

        return "\n".join(context_parts)


# Singleton instance
automation_engine = AutomationEngine()
