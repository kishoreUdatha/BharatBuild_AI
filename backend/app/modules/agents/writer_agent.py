"""
Writer Agent - Step-by-Step File Writing Agent (Bolt.new Architecture)

This agent processes ONE step at a time from the plan, writes files incrementally,
executes terminal commands, and provides real-time progress updates.

⚠️ ARCHITECTURE NOTE:
This class is currently NOT used by the Dynamic Orchestrator in production.
The Dynamic Orchestrator implements its own writer logic in:
  - DynamicOrchestrator._execute_writer() (loops through tasks)
  - DynamicOrchestrator._execute_writer_for_task() (executes single task)

This WriterAgent class is maintained for:
  1. Direct usage via Bolt Orchestrator (legacy workflow)
  2. Testing writer logic in isolation
  3. Future refactoring to consolidate writer implementations

For production bolt.new-style workflows, the Dynamic Orchestrator's embedded
writer logic is used as it supports real-time SSE streaming to the frontend.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import subprocess
import os

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.utils.response_parser import PlainTextParser
from app.modules.automation import file_manager


class WriterAgent(BaseAgent):
    """
    Writer Agent - Bolt.new Style Step-by-Step Execution

    Responsibilities:
    - Execute ONE step from the plan at a time
    - Parse <file> tags and write files to disk
    - Parse <terminal> tags and execute commands
    - Parse <explain> tags for UI updates
    - Mark steps as complete in real-time
    - Provide incremental progress updates
    """

    SYSTEM_PROMPT = """You are the WRITER AGENT - Elite Code Generator for BharatBuild AI.

═══════════════════════════════════════════════════════════════════════════════
                         🎯 YOUR MISSION
═══════════════════════════════════════════════════════════════════════════════

Generate PRODUCTION-READY, BEAUTIFUL, EXECUTABLE code that rivals top tech companies.
Every file you create must be complete, working, and visually stunning.

═══════════════════════════════════════════════════════════════════════════════
                         📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

OUTPUT EXACTLY ONE FILE using this format:
<file path="exact/path/from/request.ext">import or code starts HERE on this line - NO empty first line
...rest of file content...
</file>

CRITICAL OUTPUT RULES:
⚠️ NEVER add an empty line after <file path="..."> - code must start IMMEDIATELY
⚠️ First line of content must be actual code (import, class, function, etc) - NOT blank
1. Generate ONLY the ONE file requested - nothing else
2. File must be 100% COMPLETE - no "// TODO", "# TODO", "// ..." or placeholders
3. Include ALL necessary imports at the top
4. Include ALL functions, classes, components needed
5. NO text or explanations outside <file> tags

═══════════════════════════════════════════════════════════════════════════════
                    🎨 BEAUTIFUL UI DESIGN STANDARDS
═══════════════════════════════════════════════════════════════════════════════

MODERN DARK THEME (Default - Premium Look):
- Background: Dark gradient (from-gray-900 via-slate-900 to-black)
- Cards: bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl
- Gradients: from-purple-500 via-pink-500 to-orange-500
- Glass effects: backdrop-blur-xl bg-white/5
- Shadows: shadow-2xl shadow-purple-500/20

STUNNING VISUAL EFFECTS:
- Gradient text: bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent
- Hover animations: hover:scale-105 transition-all duration-300
- Glow effects: shadow-lg shadow-purple-500/50
- Smooth transitions: transition-all duration-300 ease-out
- Micro-interactions on every interactive element

LANDING PAGE ESSENTIALS:
- Hero section with animated gradient background
- Floating shapes/orbs with CSS animations
- Feature cards with hover lift effects
- Testimonial sections with glassmorphism
- CTA buttons with gradient + glow
- Responsive grid layouts
- Animated statistics/counters

DASHBOARD ESSENTIALS:
- Sidebar navigation with active states
- Stats cards with icons and trends
- Data visualization (charts, graphs)
- Tables with sorting/filtering
- Action buttons with loading states
- Breadcrumb navigation
- User avatar dropdown

COMPONENT PATTERNS:
```tsx
// Button with gradient + glow
<button className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600
  rounded-xl text-white font-semibold hover:scale-105
  transition-all duration-300 shadow-lg shadow-purple-500/30">

// Card with glassmorphism
<div className="p-6 bg-white/5 backdrop-blur-xl rounded-2xl
  border border-white/10 hover:border-purple-500/50
  transition-all duration-300">

// Input with dark theme
<input className="w-full px-4 py-3 bg-white/5 border border-white/10
  rounded-xl text-white placeholder-gray-500
  focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20
  transition-all outline-none" />

// Animated gradient background
<div className="absolute inset-0 bg-gradient-to-br from-purple-900/20
  via-transparent to-pink-900/20 animate-pulse" />
```

ICONS: Use Lucide React - import { IconName } from 'lucide-react'

═══════════════════════════════════════════════════════════════════════════════
                    🐍 PYTHON BEST PRACTICES
═══════════════════════════════════════════════════════════════════════════════

FASTAPI (Production-Ready):
- Use Pydantic v2 models with Field validation
- Implement proper exception handlers
- Add CORS middleware for frontend
- Use async/await for all I/O operations
- Include OpenAPI documentation
- Add proper type hints everywhere

DJANGO:
- Use class-based views
- Implement proper serializers
- Add pagination for list views
- Use select_related/prefetch_related for optimization

AI/ML (TensorFlow, PyTorch, Scikit-learn):
- Include model architecture in docstring
- Add training/inference functions
- Implement data preprocessing
- Include model saving/loading

═══════════════════════════════════════════════════════════════════════════════
                    ⚛️ JAVASCRIPT/TYPESCRIPT BEST PRACTICES
═══════════════════════════════════════════════════════════════════════════════

REACT + TYPESCRIPT:
- Use functional components with hooks
- Implement proper TypeScript interfaces
- Add loading and error states
- Use React.memo for performance
- Implement proper event handlers

NEXT.JS (App Router):
- Use server components by default
- Implement proper metadata
- Add loading.tsx and error.tsx
- Use Next.js Image component

STATE MANAGEMENT:
- Zustand for simple state
- React Query for server state
- Context for theme/auth

═══════════════════════════════════════════════════════════════════════════════
                    📱 MOBILE DEVELOPMENT
═══════════════════════════════════════════════════════════════════════════════

FLUTTER:
- Use StatelessWidget when possible
- Implement BLoC/Provider pattern
- Add proper null safety
- Use const constructors

REACT NATIVE:
- Use TypeScript
- Implement proper navigation
- Add platform-specific code when needed
- Use StyleSheet.create

═══════════════════════════════════════════════════════════════════════════════
                    🗄️ DATABASE & SEED DATA (CRITICAL!)
═══════════════════════════════════════════════════════════════════════════════

FOR EVERY FULL-STACK PROJECT, GENERATE:

1. DATABASE MODELS/SCHEMA:
   - Define all tables with proper relationships
   - Include indexes, constraints, foreign keys
   - Add timestamps (created_at, updated_at)

2. MIGRATIONS:
   - Alembic for FastAPI/SQLAlchemy
   - Django migrations for Django
   - Prisma migrations for Node.js

3. SEED DATA FILE (REQUIRED!):
   Generate realistic sample data based on schema:

   FASTAPI (backend/app/db/seed.py):
   ```python
   from app.models import User, Product, Order
   from app.db.session import SessionLocal

   async def seed_database():
       db = SessionLocal()

       # Sample users
       users = [
           User(name="John Doe", email="john@example.com", role="admin"),
           User(name="Jane Smith", email="jane@example.com", role="user"),
           User(name="Bob Wilson", email="bob@example.com", role="user"),
       ]
       db.add_all(users)

       # Sample products (10-20 items with realistic data)
       products = [
           Product(name="iPhone 15 Pro", price=999.99, category="Electronics", stock=50),
           Product(name="MacBook Air M3", price=1299.00, category="Electronics", stock=30),
           # ... more realistic products
       ]
       db.add_all(products)

       await db.commit()
   ```

   SPRING BOOT (src/main/resources/data.sql):
   ```sql
   INSERT INTO users (name, email, role) VALUES
   ('John Doe', 'john@example.com', 'admin'),
   ('Jane Smith', 'jane@example.com', 'user');

   INSERT INTO products (name, price, category, stock) VALUES
   ('iPhone 15 Pro', 999.99, 'Electronics', 50),
   ('MacBook Air M3', 1299.00, 'Electronics', 30);
   ```

   DJANGO (app/management/commands/seed.py):
   ```python
   from django.core.management.base import BaseCommand
   from app.models import User, Product

   class Command(BaseCommand):
       def handle(self, *args, **options):
           # Create sample data
           User.objects.create(name="John Doe", email="john@example.com")
   ```

   NODE.JS/PRISMA (prisma/seed.ts):
   ```typescript
   import { PrismaClient } from '@prisma/client'
   const prisma = new PrismaClient()

   async function main() {
     await prisma.user.createMany({
       data: [
         { name: 'John Doe', email: 'john@example.com' },
         { name: 'Jane Smith', email: 'jane@example.com' },
       ]
     })
   }
   ```

4. AUTO-RUN SEED ON STARTUP:
   - Include seed command in docker-compose or startup script
   - Check if data exists before seeding (prevent duplicates)

5. SEED DATA GUIDELINES:
   - Generate 10-20 realistic records per table
   - Use proper names, emails, addresses (not "test1", "test2")
   - Include relationships (user has orders, orders have products)
   - Add variety (different categories, prices, dates)
   - Make data visually appealing for demos

═══════════════════════════════════════════════════════════════════════════════
                    🐳 DOCKER REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

ALL PROJECTS MUST RUN IN DOCKER:
- Include multi-stage builds for optimization
- Add .dockerignore for faster builds
- Use Alpine images for smaller size
- Include health checks

═══════════════════════════════════════════════════════════════════════════════
                    ✅ QUALITY CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

Before outputting, verify:
[ ] File path matches EXACTLY what was requested
[ ] ALL imports are included at the top
[ ] NO placeholder comments (// TODO, # TODO, // ...)
[ ] NO incomplete sections ("add more here", "implement this")
[ ] Types/interfaces are properly defined
[ ] Error handling is included
[ ] Code follows best practices
[ ] UI is beautiful with animations and effects
[ ] All functions have complete implementations

═══════════════════════════════════════════════════════════════════════════════
                    🎯 FINAL REMINDER
═══════════════════════════════════════════════════════════════════════════════

Generate ONE file. Make it COMPLETE. Make it BEAUTIFUL. Make it PRODUCTION-READY.

The file should:
1. Work immediately when added to the project
2. Have stunning UI with modern design patterns
3. Follow best practices for that language/framework
4. Include all necessary imports and dependencies
5. Have proper error handling

Think: Premium, Beautiful, Production-Ready - like code from Apple, Stripe, or Vercel.
"""

    def __init__(self):
        super().__init__(
            name="Writer Agent",
            role="step_by_step_file_writer",
            capabilities=[
                "incremental_file_writing",
                "terminal_command_execution",
                "real_time_progress",
                "step_by_step_execution",
                "bolt_new_architecture"
            ],
            model="haiku"  # Fast model for quick iterations
        )

    async def process(
        self,
        context: AgentContext,
        step_number: int,
        step_data: Dict[str, Any],
        previous_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a single step from the plan

        Args:
            context: Agent context with project info
            step_number: Current step number (1-indexed)
            step_data: Step information from plan
            previous_context: Context from previous steps

        Returns:
            Dict with execution results
        """
        try:
            logger.info(f"[Writer Agent] Executing Step {step_number}: {step_data.get('name', 'Unnamed Step')}")

            # Build prompt for this specific step
            step_prompt = self._build_step_prompt(
                step_number=step_number,
                step_data=step_data,
                previous_context=previous_context,
                context=context
            )

            # Call Claude with Bolt.new format
            response = await self._call_claude(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=step_prompt,
                max_tokens=4096,
                temperature=0.3  # Lower temperature for consistent code
            )

            # Parse Bolt.new response
            parsed = PlainTextParser.parse_bolt_response(response)

            # Execute the parsed actions
            execution_result = await self._execute_actions(
                parsed=parsed,
                project_id=context.project_id,
                step_number=step_number
            )

            logger.info(f"[Writer Agent] Step {step_number} completed successfully")

            return {
                "success": True,
                "agent": self.name,
                "step_number": step_number,
                "step_name": step_data.get("name"),
                "thinking": parsed.get("thinking"),
                "explanation": parsed.get("explain"),
                "files_created": execution_result["files_created"],
                "commands_executed": execution_result["commands_executed"],
                "errors": execution_result.get("errors", []),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Writer Agent] Step {step_number} failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.name,
                "step_number": step_number,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_step_prompt(
        self,
        step_number: int,
        step_data: Dict[str, Any],
        previous_context: Optional[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for the current step"""

        prompt_parts = [
            f"CURRENT STEP: Step {step_number}",
            f"STEP NAME: {step_data.get('name', 'Unnamed Step')}",
            f"STEP DESCRIPTION: {step_data.get('description', 'No description')}",
            ""
        ]

        # Add tasks if available
        if "tasks" in step_data and step_data["tasks"]:
            prompt_parts.append("TASKS TO COMPLETE:")
            for i, task in enumerate(step_data["tasks"], 1):
                prompt_parts.append(f"{i}. {task}")
            prompt_parts.append("")

        # Add deliverables if available
        if "deliverables" in step_data and step_data["deliverables"]:
            prompt_parts.append("DELIVERABLES:")
            for deliverable in step_data["deliverables"]:
                prompt_parts.append(f"- {deliverable}")
            prompt_parts.append("")

        # Add context from previous steps
        if previous_context:
            prompt_parts.append("CONTEXT FROM PREVIOUS STEPS:")
            if "files_created" in previous_context:
                prompt_parts.append(f"Files created so far: {len(previous_context['files_created'])} files")
            if "last_explanation" in previous_context:
                prompt_parts.append(f"Previous step: {previous_context['last_explanation']}")
            prompt_parts.append("")

        # Add project metadata
        metadata = context.metadata or {}
        if "tech_stack" in metadata:
            prompt_parts.append(f"TECH STACK: {metadata['tech_stack']}")
        if "features" in metadata:
            prompt_parts.append(f"FEATURES: {', '.join(metadata.get('features', []))}")

        prompt_parts.append("")
        prompt_parts.append("TASK:")
        prompt_parts.append(f"Execute Step {step_number} completely. Generate files, commands, and explanations using Bolt.new XML tags.")
        prompt_parts.append("Focus ONLY on this step. Do not generate files for future steps.")
        prompt_parts.append("")
        prompt_parts.append("Output format: <thinking>, <explain>, <file>, <terminal> tags")

        return "\n".join(prompt_parts)

    async def _execute_actions(
        self,
        parsed: Dict[str, Any],
        project_id: str,
        step_number: int
    ) -> Dict[str, Any]:
        """
        Execute parsed actions from Bolt.new response

        Args:
            parsed: Parsed response with files, commands, etc.
            project_id: Project identifier
            step_number: Current step number

        Returns:
            Dict with execution results
        """
        result = {
            "files_created": [],
            "commands_executed": [],
            "errors": []
        }

        # 1. Write files
        if "files" in parsed and parsed["files"]:
            for file_info in parsed["files"]:
                try:
                    file_path = file_info.get("path")
                    content = file_info.get("content")

                    if not file_path or not content:
                        logger.warning(f"[Writer Agent] Skipping file with missing path or content")
                        continue

                    # Write file using file_manager
                    write_result = await file_manager.create_file(
                        project_id=project_id,
                        file_path=file_path,
                        content=content
                    )

                    if write_result["success"]:
                        result["files_created"].append({
                            "path": file_path,
                            "size": len(content),
                            "step": step_number
                        })
                        logger.info(f"[Writer Agent] Created file: {file_path}")
                    else:
                        result["errors"].append(f"Failed to create {file_path}: {write_result.get('error')}")

                except Exception as e:
                    logger.error(f"[Writer Agent] Error writing file: {e}")
                    result["errors"].append(f"File write error: {str(e)}")

        # 2. Execute terminal commands
        if "terminal" in parsed:
            commands = parsed["terminal"]
            # Handle both single command (string) and multiple commands (list)
            if isinstance(commands, str):
                commands = [commands]

            for command in commands:
                try:
                    # Execute command safely
                    exec_result = await self._execute_terminal_command(
                        command=command,
                        project_id=project_id
                    )

                    result["commands_executed"].append({
                        "command": command,
                        "success": exec_result["success"],
                        "output": exec_result.get("output", ""),
                        "step": step_number
                    })

                    if not exec_result["success"]:
                        result["errors"].append(f"Command failed: {command}")

                except Exception as e:
                    logger.error(f"[Writer Agent] Error executing command: {e}")
                    result["errors"].append(f"Command error: {str(e)}")

        return result

    async def _execute_terminal_command(
        self,
        command: str,
        project_id: str,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Execute a terminal command safely

        Args:
            command: Command to execute
            project_id: Project identifier
            timeout: Command timeout in seconds

        Returns:
            Dict with execution result
        """
        try:
            logger.info(f"[Writer Agent] Executing command: {command}")

            # Get project directory
            project_dir = os.path.join("generated", project_id)

            # Security: Validate command is safe
            dangerous_commands = ["rm -rf", "sudo", "chmod 777", "dd if=", "> /dev/"]
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                logger.warning(f"[Writer Agent] Blocked dangerous command: {command}")
                return {
                    "success": False,
                    "error": "Command blocked for security reasons"
                }

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "output": stdout.decode() if stdout else "",
                    "error": stderr.decode() if stderr else ""
                }

            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout}s"
                }

        except Exception as e:
            logger.error(f"[Writer Agent] Command execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_plan_steps(
        self,
        context: AgentContext,
        plan: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute all steps from a plan sequentially

        Args:
            context: Agent context
            plan: Complete plan with steps
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with all execution results
        """
        results = {
            "steps_completed": [],
            "total_files_created": 0,
            "total_commands_executed": 0,
            "errors": [],
            "started_at": datetime.utcnow().isoformat()
        }

        # Extract steps from plan
        steps = self._extract_steps_from_plan(plan)
        total_steps = len(steps)

        logger.info(f"[Writer Agent] Starting execution of {total_steps} steps")

        previous_context = None

        for i, step_data in enumerate(steps, 1):
            # Update progress
            if progress_callback:
                progress_percent = int((i / total_steps) * 100)
                await progress_callback(
                    progress_percent,
                    f"Step {i}/{total_steps}: {step_data.get('name', 'Processing...')}"
                )

            # Execute step
            step_result = await self.process(
                context=context,
                step_number=i,
                step_data=step_data,
                previous_context=previous_context
            )

            results["steps_completed"].append(step_result)

            if step_result["success"]:
                results["total_files_created"] += len(step_result.get("files_created", []))
                results["total_commands_executed"] += len(step_result.get("commands_executed", []))

                # Update context for next step
                previous_context = {
                    "files_created": step_result.get("files_created", []),
                    "last_explanation": step_result.get("explanation")
                }
            else:
                results["errors"].append(f"Step {i} failed: {step_result.get('error')}")
                # Continue with next step even if current fails
                logger.warning(f"[Writer Agent] Step {i} failed, continuing with next step")

        results["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"[Writer Agent] Completed all steps. Files: {results['total_files_created']}, Commands: {results['total_commands_executed']}")

        return results

    def _extract_steps_from_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract steps from plan structure"""
        steps = []

        # Check for implementation_steps or phases
        if "implementation_steps" in plan:
            for phase_key, phase_data in plan["implementation_steps"].items():
                if isinstance(phase_data, dict):
                    steps.append({
                        "name": phase_data.get("name", phase_key),
                        "description": phase_data.get("description", ""),
                        "tasks": phase_data.get("tasks", []),
                        "deliverables": phase_data.get("deliverables", []),
                        "duration": phase_data.get("duration", "")
                    })

        # Fallback: if no steps found, create a single step
        if not steps:
            steps.append({
                "name": "Project Implementation",
                "description": "Implement the complete project",
                "tasks": ["Generate all required files", "Setup dependencies"],
                "deliverables": ["Complete working application"]
            })

        return steps


# Singleton instance
writer_agent = WriterAgent()
