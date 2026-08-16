"""
AGENT 1 - Planner Agent
Understands user requests and creates detailed project plans
"""

from typing import Dict, List, Optional, Any
import json
from datetime import datetime
from pathlib import Path

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext


class PlannerAgent(BaseAgent):
    """
    Planner / Understanding Agent with Dynamic Prompt Loading

    Responsibilities:
    - Understand vague or abstract user requests
    - Identify project requirements
    - Determine appropriate technology stack
    - Create detailed feature lists
    - Plan implementation steps
    - Consider learning goals for students

    Optimization:
    - Detects technology from user request
    - Loads only relevant prompt sections (~300 lines vs 2000+ lines)
    - Reduces API costs and improves response quality
    """

    # Prompt directory
    PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"

    # Technology detection keywords (specific terms only — avoid generic words like 'ui', 'dashboard')
    TECH_KEYWORDS = {
        "react": ["react", "vite", "tsx", "jsx", "next.js", "nextjs", "tailwind css", "shadcn", "redux", "zustand", "react hook form"],
        "python": ["fastapi", "django", "flask", "python", "uvicorn", "sqlalchemy", "celery", "pydantic"],
        "java": ["spring", "java", "maven", "gradle", "spring boot", "springboot", "hibernate"],
        "node": ["express", "node.js", "nodejs", "nestjs", "prisma", "npm", "yarn"],
        "mobile": ["flutter", "react native", "android app", "ios app", "kotlin", "swift", "mobile app"],
        "ai_ml": ["machine learning", "deep learning", "tensorflow", "pytorch", "neural network", "scikit-learn", "huggingface", "llm", "transformer"],
        "cli": ["command line", "cli tool", "terminal", "argparse", "click", "typer", "shell script", "bash script"],
        "3d": ["three.js", "threejs", "3d", "webgl", "react three fiber", "r3f", "3d animation", "3d website", "3d model", "3d portfolio", "3d landing", "3d configurator", "3d viewer", "3d scene", "gsap scroll", "scroll animation", "interactive 3d", "product viewer 3d"],
    }

    # Keywords that indicate a backend-only or non-frontend project
    BACKEND_ONLY_INDICATORS = [
        "api only", "rest api", "microservice", "backend service", "server",
        "data pipeline", "etl", "cron job", "worker", "queue", "batch processing",
        "scraper", "web scraping", "crawler",
    ]

    # Keywords that indicate a frontend is needed
    FRONTEND_INDICATORS = [
        "website", "web app", "webapp", "landing page", "single page",
        "frontend", "user interface", "responsive design", "spa",
        "admin panel", "dashboard app", "portal", "e-commerce site",
    ]

    @classmethod
    def _load_prompt_file(cls, filename: str) -> str:
        """Load a prompt file from the prompts directory"""
        filepath = cls.PROMPTS_DIR / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        logger.warning(f"[PlannerAgent] Prompt file not found: {filepath}")
        return ""

    @classmethod
    def _detect_technologies(cls, user_request: str) -> List[str]:
        """
        Detect technologies mentioned in user request.

        Uses specific keyword matching and context-aware fallback logic
        to avoid biasing toward React for non-frontend projects.
        """
        request_lower = user_request.lower()
        detected = []

        for tech, keywords in cls.TECH_KEYWORDS.items():
            if any(kw in request_lower for kw in keywords):
                detected.append(tech)

        # If explicit technologies were detected, return them directly
        if detected:
            logger.info(f"[PlannerAgent] Detected technologies (explicit match): {detected}")
            return detected

        # --- Smart fallback when no explicit tech keywords matched ---

        # Check if this is a CLI / script / backend-only project
        is_cli = any(term in request_lower for term in ["cli", "command line", "script", "automation script"])
        is_backend_only = any(term in request_lower for term in cls.BACKEND_ONLY_INDICATORS)
        is_mobile = any(term in request_lower for term in ["mobile", "android", "ios", "app store", "play store"])
        wants_frontend = any(term in request_lower for term in cls.FRONTEND_INDICATORS)

        if is_cli:
            detected = ["python"]
        elif is_mobile:
            detected = ["mobile"]
        elif is_backend_only and not wants_frontend:
            detected = ["python"]
        elif wants_frontend and not is_backend_only:
            # Explicitly wants a web UI but didn't name a framework
            detected = ["react", "python"]
        else:
            # Truly ambiguous (e.g., "build a todo app", "project management system")
            # Default to fullstack so both frontend and backend prompts are loaded
            detected = ["react", "python"]

        logger.info(f"[PlannerAgent] Detected technologies (fallback logic): {detected}")
        return detected

    @classmethod
    def _build_dynamic_prompt(cls, user_request: str) -> str:
        """Build prompt dynamically based on detected technologies - REDUCES PROMPT FROM 50k TO ~8k TOKENS"""
        # Always load core prompt
        core_prompt = cls._load_prompt_file("planner_core.txt")

        if not core_prompt:
            logger.warning("[PlannerAgent] Core prompt not found! Using SYSTEM_PROMPT fallback.")
            return cls.SYSTEM_PROMPT  # Fall back to the hardcoded prompt

        # Detect technologies and load relevant prompts
        detected_techs = cls._detect_technologies(user_request)

        tech_prompts = []
        prompt_mapping = {
            "react": "planner_react.txt",
            "python": "planner_python.txt",
            "java": "planner_java.txt",
            "3d": "planner_3d.txt",
        }

        for tech in detected_techs:
            if tech in prompt_mapping:
                tech_prompt = cls._load_prompt_file(prompt_mapping[tech])
                if tech_prompt:
                    tech_prompts.append(f"\n{'='*60}\n{tech.upper()} SPECIFIC RULES:\n{'='*60}\n{tech_prompt}")

        # Combine prompts
        full_prompt = core_prompt
        if tech_prompts:
            full_prompt += "\n" + "\n".join(tech_prompts)

        # Add fullstack integration prompt when frontend + backend detected
        is_fullstack = ("react" in detected_techs and ("java" in detected_techs or "python" in detected_techs))
        if is_fullstack:
            fullstack_prompt = cls._load_prompt_file("planner_fullstack.txt")
            if fullstack_prompt:
                full_prompt += f"\n{'='*60}\nFULLSTACK INTEGRATION RULES:\n{'='*60}\n{fullstack_prompt}"
                logger.info("[PlannerAgent] Added fullstack integration rules")

        # Log prompt size for debugging
        token_estimate = len(full_prompt) // 4
        logger.info(f"[PlannerAgent] Dynamic prompt size: ~{token_estimate} tokens (vs ~50k with old prompt)")

        return full_prompt

    # FALLBACK: Lean system prompt used only when prompt files are missing
    SYSTEM_PROMPT = """You are the PLANNER AGENT for a multi-purpose project generator.

YOUR JOB:
1. Understand the user's request (web app, mobile, AI/ML, CLI, academic project, or MVP)
2. Detect project type: Commercial | Academic | Research | Prototype | AI Workflow
3. Select optimal tech stack dynamically based on requirements
4. Generate a COMPLETE plan the Writer Agent can execute automatically

RULES:
- NEVER output actual code (that's the Writer Agent's job)
- NEVER ask questions - make intelligent decisions
- Include Docker/docker-compose for all backend/fullstack projects
- For academic projects, include required documents (SRS, Report, PPT, UML)
- Choose simple, stable, modern technology unless user requests otherwise

OUTPUT FORMAT (MANDATORY - use XML tags):
<plan>
  <project_name>Professional descriptive name</project_name>
  <project_description>1-2 sentence description</project_description>
  <project_type>academic|commercial|research|prototype</project_type>
  <design_theme>
    <domain>detect from context</domain>
    <primary_color>appropriate tailwind color</primary_color>
  </design_theme>
  <tech_stack>Frontend: X, Backend: Y, Database: Z</tech_stack>
  <entity_specs>
    ENTITY: EntityName
    TABLE: table_name
    FIELDS:
      - id: type (primary key)
      - field: type
    API_PATH: /api/entities
  </entity_specs>
  <project_structure>directory tree</project_structure>
  <files>
    <file path="path/to/file" priority="1" depends_on="">
      <description>What this file does</description>
      <exports>ExportedNames</exports>
    </file>
  </files>
  <tasks>
    Step 1: ...
    Step 2: ...
  </tasks>
  <notes>Important notes for Writer Agent</notes>
</plan>
"""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="PlannerAgent",
            role="Project Planner and Architect",
            capabilities=["planning", "architecture", "tech_stack_selection", "task_breakdown"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Create project plan from user request

        Args:
            context: AgentContext with user request

        Returns:
            Structured project plan
        """
        # Validate context
        if context is None:
            logger.error("[PlannerAgent] Received None context")
            return {
                "success": False,
                "error": "Invalid context: context is None",
                "plan": None,
                "raw_response": ""
            }

        # Ensure metadata is never None
        metadata = context.metadata if context.metadata is not None else {}
        
        prompt = f"""
User Request: {context.user_request}

Additional Context: {metadata}

Create a complete, executable project plan following the output format specified in your system prompt.
Remember to:
1. Detect the project type (Academic/Commercial/Research/Prototype/AI Workflow)
2. Make intelligent architecture decisions
3. Select the optimal tech stack dynamically
4. Create a detailed folder structure
5. Break down into executable implementation tasks
6. Include academic documents only if it's an academic project

Be thorough, specific, and ensure all tasks are actionable by automation agents.
"""

        # BUILD DYNAMIC PROMPT - loads only relevant tech rules (~8k tokens vs 50k)
        dynamic_system_prompt = self._build_dynamic_prompt(context.user_request)

        response = await self._call_claude(
            system_prompt=dynamic_system_prompt,
            user_prompt=prompt,
            max_tokens=16384,  # Increased for complex plans with many files
            temperature=0.3
        )

        # Parse the plan from the response
        plan = self._parse_plan(response)

        # Validate and complete the files list
        if plan and not plan.get("error"):
            plan = self.validate_and_complete_files(plan)
            logger.info(f"[PlannerAgent] Final plan has {len(plan.get('files', []))} files")

        return {
            "success": True,
            "plan": plan,
            "raw_response": response
        }

    def _parse_plan(self, response: str) -> Dict[str, Any]:
        """
        Parse the Bolt.new XML format plan

        Args:
            response: Raw XML response from Claude

        Returns:
            Parsed plan dictionary
        """
        import re

        plan = {}

        # Extract <plan> content
        plan_match = re.search(r'<plan>(.*?)</plan>', response, re.DOTALL)
        if not plan_match:
            logger.warning("No <plan> tag found in response")
            return {"error": "Invalid plan format", "raw": response}

        plan_content = plan_match.group(1)

        # Extract project_type
        project_type_match = re.search(r'<project_type>(.*?)</project_type>', plan_content, re.DOTALL)
        if project_type_match:
            plan["project_type"] = project_type_match.group(1).strip()

        # Extract project_info
        project_info_match = re.search(r'<project_info>(.*?)</project_info>', plan_content, re.DOTALL)
        if project_info_match:
            plan["project_info"] = project_info_match.group(1).strip()

        # Extract design_theme (NEW - for domain-specific colors)
        design_theme_match = re.search(r'<design_theme>(.*?)</design_theme>', plan_content, re.DOTALL)
        if design_theme_match:
            theme_content = design_theme_match.group(1)
            plan["design_theme"] = {
                "domain": self._extract_tag(theme_content, "domain") or "default",
                "primary_color": self._extract_tag(theme_content, "primary_color") or "purple",
                "secondary_color": self._extract_tag(theme_content, "secondary_color") or "pink",
                "background": self._extract_tag(theme_content, "background") or "from-gray-900 to-slate-900",
                "accent": self._extract_tag(theme_content, "accent") or "orange"
            }
            logger.info(f"[PlannerAgent] Design theme: {plan['design_theme']['domain']} - primary: {plan['design_theme']['primary_color']}")
        else:
            # Default theme if not specified
            plan["design_theme"] = {
                "domain": "default",
                "primary_color": "purple",
                "secondary_color": "pink",
                "background": "from-gray-900 to-slate-900",
                "accent": "orange"
            }

        # Extract tech_stack
        tech_stack_match = re.search(r'<tech_stack>(.*?)</tech_stack>', plan_content, re.DOTALL)
        if tech_stack_match:
            plan["tech_stack"] = tech_stack_match.group(1).strip()

        # Extract project_structure
        structure_match = re.search(r'<project_structure>(.*?)</project_structure>', plan_content, re.DOTALL)
        if structure_match:
            plan["project_structure"] = structure_match.group(1).strip()

        # ✅ FIX: Extract files list (CRITICAL for Writer Agent)
        files_match = re.search(r'<files>(.*?)</files>', plan_content, re.DOTALL)
        if files_match:
            files_content = files_match.group(1)
            plan["files"] = self._parse_files_list(files_content)
            plan["files_raw"] = files_content.strip()
        else:
            # Fallback: Try to extract files from project_structure
            logger.warning("No <files> tag found - attempting to extract from project_structure")
            if plan.get("project_structure"):
                plan["files"] = self._extract_files_from_structure(plan["project_structure"])

        # Extract tasks
        tasks_match = re.search(r'<tasks>(.*?)</tasks>', plan_content, re.DOTALL)
        if tasks_match:
            plan["tasks"] = tasks_match.group(1).strip()

        # Extract notes
        notes_match = re.search(r'<notes>(.*?)</notes>', plan_content, re.DOTALL)
        if notes_match:
            plan["notes"] = notes_match.group(1).strip()

        # Extract package_structure (CRITICAL for Java projects - ensures consistent packages)
        package_structure_match = re.search(r'<package_structure>(.*?)</package_structure>', plan_content, re.DOTALL)
        if package_structure_match:
            plan["package_structure"] = package_structure_match.group(1).strip()
            logger.info(f"[PlannerAgent] Extracted package_structure document for Writer context")
        else:
            # For Java projects, this is important - log a warning
            if plan.get("tech_stack") and "java" in plan.get("tech_stack", "").lower():
                logger.warning("[PlannerAgent] No <package_structure> found for Java project - Writer may have package inconsistencies!")

        # Extract entity_specs (CRITICAL for field name consistency across Entity/DTO/Service/Frontend)
        entity_specs_match = re.search(r'<entity_specs>(.*?)</entity_specs>', plan_content, re.DOTALL)
        if entity_specs_match:
            plan["entity_specs"] = entity_specs_match.group(1).strip()
            logger.info(f"[PlannerAgent] Extracted entity_specs for cross-file field consistency")
        else:
            # For fullstack projects, this is important
            if plan.get("tech_stack") and ("java" in plan.get("tech_stack", "").lower() or "spring" in plan.get("tech_stack", "").lower()):
                logger.warning("[PlannerAgent] No <entity_specs> found - Writer may generate inconsistent field names!")

        # Log file count for debugging
        files_count = len(plan.get("files", []))
        logger.info(f"[PlannerAgent] Parsed plan with {files_count} files")

        return plan

    def _extract_tag(self, content: str, tag_name: str) -> Optional[str]:
        """Extract content from a simple XML tag"""
        import re
        match = re.search(rf'<{tag_name}>(.*?)</{tag_name}>', content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _parse_files_list(self, files_content: str) -> List[Dict[str, Any]]:
        """
        Parse the <files> XML section into a list of file dictionaries.

        Args:
            files_content: Raw content inside <files> tag

        Returns:
            List of file dictionaries with path, priority, description, exports
        """
        import re

        files = []

        # Match each <file>...</file> block and extract all nested tags
        file_block_pattern = r'<file\s+([^>]+)>(.*?)</file>'

        for match in re.finditer(file_block_pattern, files_content, re.DOTALL):
            attrs = match.group(1)
            content = match.group(2)

            # Extract path attribute
            path_match = re.search(r'path=["\']([^"\']+)["\']', attrs)
            path = path_match.group(1).strip() if path_match else ""

            # Extract priority attribute (with safe conversion)
            priority_match = re.search(r'priority=["\'](\d+)["\']', attrs)
            try:
                priority = int(priority_match.group(1)) if priority_match else len(files) + 1
            except (ValueError, AttributeError):
                priority = len(files) + 1

            # Extract description
            desc_match = re.search(r'<description>(.*?)</description>', content, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""

            # Extract exports (CRITICAL for cross-file imports)
            exports_match = re.search(r'<exports>(.*?)</exports>', content, re.DOTALL)
            exports = exports_match.group(1).strip() if exports_match else ""

            # Extract depends_on
            depends_match = re.search(r'<depends_on>(.*?)</depends_on>', content, re.DOTALL)
            depends_on = depends_match.group(1).strip() if depends_match else ""

            if path:
                files.append({
                    "path": path,
                    "priority": priority,
                    "description": description,
                    "exports": exports,
                    "depends_on": depends_on
                })

        # Sort by priority
        files.sort(key=lambda x: x["priority"])

        return files

    def _extract_files_from_structure(self, structure: str) -> List[Dict[str, Any]]:
        """
        Fallback: Extract file paths from project_structure tree.

        ENHANCED: More robust parsing that handles various tree formats and
        extracts ALL files from the structure properly.

        Args:
            structure: Project structure tree string (ASCII tree format)

        Returns:
            List of file dictionaries with FULL paths extracted from structure
        """
        import re

        files = []
        priority = 1

        # Expanded file extensions to detect (including common ones that were missing)
        file_extensions = r'\.(tsx?|jsx?|py|json|ya?ml|md|css|scss|less|html|sql|sh|dockerfile|env|txt|toml|cfg|ini|xml|gradle|properties|java|kt|swift|go|rs|c|cpp|h|hpp|rb|php|vue|svelte|astro|mjs|cjs|mts|cts|prisma|graphql|gql)$'

        # Also match files without extensions that are commonly needed
        special_files = ['Dockerfile', 'Makefile', 'Procfile', '.env', '.env.example', '.env.local', '.gitignore', '.dockerignore', '.eslintrc', '.prettierrc']

        # Track directory stack for full path reconstruction
        dir_stack = []

        # Split into lines and process
        lines = structure.split('\n')

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            # Remove tree drawing characters more robustly
            # Handle both Unicode box-drawing chars and ASCII variants
            # │ (U+2502), ├ (U+251C), └ (U+2514), ─ (U+2500), | (pipe), ` (backtick)
            tree_chars = r'[│├└─┬┴┼|`\-]'

            # Count indent level by looking at leading whitespace + tree chars
            # Each "level" in a tree is typically represented by 2-4 chars
            stripped = line.lstrip()
            leading = line[:len(line) - len(stripped)]

            # Count indent more robustly
            # Remove tree characters and count remaining spaces
            leading_without_tree = re.sub(tree_chars, ' ', leading)
            indent_level = len(leading_without_tree.replace(' ', '')) + len(leading_without_tree) // 4

            # Better approach: count actual indentation by finding position of content
            content_start = 0
            for j, char in enumerate(line):
                if char not in ' │├└─┬┴┼|\t-`':
                    content_start = j
                    break

            # Each level is roughly 4 characters in tree view
            indent_level = content_start // 4

            # Extract the actual name (remove all tree characters)
            clean_name = re.sub(r'^[\s│├└─┬┴┼|\-`]+', '', line).strip()

            # Also handle lines like "├── filename.ext" or "|-- filename.ext"
            clean_name = re.sub(r'^[─\-]+\s*', '', clean_name).strip()

            if not clean_name:
                continue

            # Skip comments in structure (lines starting with #)
            if clean_name.startswith('#'):
                continue

            # Check if this is a directory (ends with /)
            is_directory = clean_name.endswith('/')

            if is_directory:
                # It's a directory - update the directory stack
                dir_name = clean_name.rstrip('/')

                # Pop directories from stack until we're at the right level
                while len(dir_stack) > indent_level:
                    dir_stack.pop()

                # Push this directory onto the stack
                dir_stack.append(dir_name)

                logger.debug(f"[PlannerAgent] Dir at level {indent_level}: {dir_name}, stack: {dir_stack}")

            else:
                # Check if it's a file (has extension or is a special file)
                is_file = (
                    re.search(file_extensions, clean_name, re.IGNORECASE) or
                    clean_name in special_files or
                    clean_name.startswith('.env')
                )

                if is_file:
                    # Pop directories from stack until we're at the right level
                    while len(dir_stack) > indent_level:
                        dir_stack.pop()

                    # Build full path
                    if dir_stack:
                        full_path = '/'.join(dir_stack) + '/' + clean_name
                    else:
                        full_path = clean_name

                    # Normalize path (remove double slashes, etc.)
                    full_path = re.sub(r'/+', '/', full_path)

                    files.append({
                        "path": full_path,
                        "priority": priority,
                        "description": f"Auto-extracted from project structure"
                    })
                    priority += 1

                    logger.debug(f"[PlannerAgent] File extracted: {full_path} (level={indent_level})")

        logger.info(f"[PlannerAgent] Extracted {len(files)} files from project_structure")

        # Also try simple regex extraction as additional fallback
        # This catches file paths written inline like "src/App.tsx" without tree formatting
        simple_paths = re.findall(r'\b([a-zA-Z_][\w\-]*(?:/[\w\-\.]+)+\.[a-zA-Z0-9]+)\b', structure)
        for path in simple_paths:
            # Check if this path is already extracted
            if not any(f['path'] == path for f in files):
                files.append({
                    "path": path,
                    "priority": priority,
                    "description": "Auto-extracted from inline path"
                })
                priority += 1
                logger.debug(f"[PlannerAgent] Inline path extracted: {path}")

        # Log summary
        if files:
            logger.info(f"[PlannerAgent] Total files extracted: {len(files)}")
            for f in files[:10]:  # Log first 10
                logger.debug(f"[PlannerAgent]   - {f['path']}")
            if len(files) > 10:
                logger.debug(f"[PlannerAgent]   ... and {len(files) - 10} more")
        else:
            logger.warning("[PlannerAgent] No files extracted from project_structure!")

        return files


    def validate_and_complete_files(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that the files list is complete and add any missing essential files.

        This ensures that:
        1. All referenced components/pages have corresponding files
        2. Essential config files are always present
        3. The folder structure matches the tech stack

        Args:
            plan: Parsed plan dictionary

        Returns:
            Updated plan with validated/completed files list
        """
        files = plan.get("files", [])
        tech_stack = plan.get("tech_stack", "").lower()
        structure = plan.get("project_structure", "")

        # Essential files by tech stack
        essential_files = {
            "react": [
                "package.json",
                "vite.config.ts",
                "tailwind.config.js",
                "postcss.config.js",
                "tsconfig.json",
                "tsconfig.node.json",
                "index.html",
                "src/main.tsx",
                "src/App.tsx",
                "src/index.css"
            ],
            "next": [
                "package.json",
                "next.config.js",
                "tailwind.config.ts",
                "postcss.config.js",
                "tsconfig.json"
            ],
            "fastapi": [
                "requirements.txt",
                "main.py",
                "Dockerfile"
            ],
            "django": [
                "requirements.txt",
                "manage.py",
                "Dockerfile"
            ],
            "spring": [
                "pom.xml",
                "Dockerfile"
            ]
        }

        # Determine which essential files to check
        essentials = []
        
        # Check for monorepo structure FIRST (affects path detection)
        is_monorepo = "frontend/" in structure or "backend/" in structure
        
        # IMPROVED: Detect React/Vite from multiple signals
        has_react = any(x in tech_stack for x in ["react", "vite", "tsx", "typescript"]) or "frontend/" in structure
        has_next = "next" in tech_stack
        
        # Add React/Vite essentials if frontend detected
        if has_react and not has_next:
            essentials.extend(essential_files["react"])
        elif has_next:
            essentials.extend(essential_files["next"])

        # Backend detection
        if "fastapi" in tech_stack or "fastapi" in structure.lower():
            essentials.extend(essential_files["fastapi"])
        elif "django" in tech_stack:
            essentials.extend(essential_files["django"])
        elif "spring" in tech_stack or "pom.xml" in structure.lower() or "spring-boot" in structure.lower():
            essentials.extend(essential_files["spring"])

        # Get existing file paths
        existing_paths = {f["path"] for f in files}

        # Add missing essential files
        missing_added = []
        for essential in essentials:
            # Handle monorepo paths
            if is_monorepo:
                # Check both root and frontend/ paths
                paths_to_check = [essential]
                if essential.startswith("src/") or essential in ["package.json", "vite.config.ts", "tailwind.config.js", "index.html"]:
                    paths_to_check.append(f"frontend/{essential}")

                found = any(p in existing_paths for p in paths_to_check)
            else:
                found = essential in existing_paths

            if not found:
                # Determine correct path
                if is_monorepo and (essential.startswith("src/") or essential in ["package.json", "vite.config.ts", "tailwind.config.js", "index.html", "postcss.config.js", "tsconfig.json", "tsconfig.node.json"]):
                    path = f"frontend/{essential}"
                else:
                    path = essential

                files.append({
                    "path": path,
                    "priority": len(files) + 1,
                    "description": f"Essential file (auto-added for completeness)"
                })
                missing_added.append(path)

        if missing_added:
            logger.info(f"[PlannerAgent] Added {len(missing_added)} missing essential files: {missing_added[:5]}...")

        # Re-sort by priority
        files.sort(key=lambda x: x["priority"])

        plan["files"] = files
        plan["files_validated"] = True

        return plan


# Singleton instance
planner_agent = PlannerAgent()
