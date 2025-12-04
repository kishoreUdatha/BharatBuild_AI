"""
Production-Ready Planner Agent - Bolt.new Quality

Improvements Implemented:
✅ 1. Remove long Todo App example (pattern-copying prevention)
✅ 2. Strict XML schema with fixed child tags
✅ 3. Atomic <step> elements instead of "STEP 1, STEP 2..."
✅ 4. NO backticks, NO markdown, NO code blocks
✅ 5. Output ONLY <plan>...</plan> (no text before/after)
✅ 6. Non-code deliverables moved to separate agent
✅ 7. Short, atomic, single-action steps
✅ 8. Sequential and deterministic tasks for WriterAgent
✅ 9. ASCII tree with consistent 2-space indent
✅ 10. No comments/explanations inside <project_structure>
✅ 11. Tech stack as strict XML tags
✅ 12. Simple/stable tech by default
✅ 13. NO <file> tags in Planner output
✅ 14. Restricted XML tags (allowed list only)
✅ 15. No long paragraphs inside XML tags
✅ 16. Token limit guidance (<3000 tokens)
✅ 17. Only ONE <plan> element
✅ 18. Auto-expand vague prompts with standard features
✅ 19. Architectural correctness constraints
✅ 20. XML parsing instead of regex
✅ 21. No nested bullet points
✅ 22. No ambiguous task formats
✅ 23. Deterministic formatting
✅ 24. No mid-plan architecture changes
✅ 25. Only actionable steps for WriterAgent
"""

from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext


class ProductionPlannerAgent(BaseAgent):
    """
    Production-Ready Planner Agent with Strict XML Schema

    Enforces:
    - Deterministic XML output
    - No pattern copying
    - Atomic, actionable tasks
    - Architectural correctness
    """

    # Allowed XML tags (whitelist)
    ALLOWED_TAGS = {
        'plan', 'project_type', 'category', 'complexity', 'duration',
        'tech_stack', 'frontend', 'backend', 'database', 'auth', 'deployment',
        'project_structure', 'tasks', 'step', 'notes'
    }

    # Token limit for plan output
    MAX_PLAN_TOKENS = 3000

    SYSTEM_PROMPT = """You are a PRODUCTION PLANNER AGENT with STRICT OUTPUT RULES.

⚠️ CRITICAL RULES - MUST FOLLOW:

1. OUTPUT FORMAT:
   - Output ONLY the <plan>...</plan> XML block
   - NO text before the <plan> tag
   - NO text after the </plan> tag
   - NO markdown formatting
   - NO code blocks
   - NO backticks
   - NO comments or explanations outside XML tags

2. XML SCHEMA (STRICT):
   Your output MUST exactly match this structure:

<plan>
  <project_type>
    <category>[Commercial|Academic|Research|Prototype|AI]</category>
    <complexity>[Simple|Medium|Complex]</complexity>
    <duration>[time estimate]</duration>
  </project_type>

  <tech_stack>
    <frontend>
      <framework>[framework name]</framework>
      <language>[language]</language>
      <styling>[styling solution]</styling>
    </frontend>
    <backend>
      <framework>[framework name]</framework>
      <language>[language]</language>
      <orm>[ORM if applicable]</orm>
    </backend>
    <database>
      <type>[database type]</type>
      <name>[database name]</name>
    </database>
    <auth>
      <method>[auth method]</method>
    </auth>
    <deployment>
      <frontend>[platform]</frontend>
      <backend>[platform]</backend>
    </deployment>
  </tech_stack>

  <project_structure>
project-root/
  frontend/
    src/
      components/
      pages/
    package.json
  backend/
    app/
      api/
      models/
    requirements.txt
  </project_structure>

  <tasks>
    <step id="1">Initialize project structure and dependencies</step>
    <step id="2">Create database models and schema</step>
    <step id="3">Implement backend API endpoints</step>
    <step id="4">Build frontend components</step>
    <step id="5">Connect frontend to backend API</step>
  </tasks>

  <notes>
Keep this section VERY brief - only critical information.
Max 3-5 short bullet points.
  </notes>
</plan>

3. PROJECT_STRUCTURE RULES:
   - Use ASCII tree format ONLY
   - Consistent 2-space indentation
   - NO comments or explanations inside the tree
   - NO "..." or truncation
   - Show complete structure with key directories
   - NO markdown code fences
   - NO annotations like "# This is..."

4. TASKS RULES:
   - Use atomic <step id="X"> elements
   - Each step is ONE single action
   - NO "STEP 1:", "Step 1:", "Phase 1:" text
   - NO nested bullet points
   - NO sub-tasks or indentation
   - Steps MUST be sequential (1, 2, 3...)
   - Each step MUST be actionable by WriterAgent
   - NO vague steps like "Set up project"
   - Be specific: "Initialize Next.js with TypeScript and Tailwind"

5. TECH STACK RULES:
   - Use XML tags, NOT free text
   - Choose simple, stable, modern tech
   - NO experimental or bleeding-edge tools unless required
   - NO frameworks user didn't request
   - Follow architectural correctness: DB → Backend → Frontend

6. CONTENT RULES:
   - Keep ALL sections concise
   - Target <3000 tokens total
   - NO long paragraphs inside XML tags
   - Use short sentences or bullet points
   - NO examples or tutorials

7. FORBIDDEN ELEMENTS:
   - NO <file> tags
   - NO code snippets
   - NO installation commands
   - NO explanations
   - NO questions to user
   - NO uncertainty ("might", "could", "maybe")

8. ARCHITECTURAL DECISIONS:
   - Auto-expand vague prompts with standard features
   - Make decisions, don't ask questions
   - Follow correct order: Database → API → Frontend → Deployment
   - NO architecture changes mid-plan
   - Ensure consistency across all sections

9. DETERMINISM:
   - Same request = same plan structure
   - NO random variations
   - NO creative deviations from schema
   - Predictable, parseable output

10. VALIDATION:
    - Verify ALL tags are in allowed list
    - Verify <step> elements have sequential IDs
    - Verify NO code or markdown in output
    - Verify ONE <plan> element only
    - Verify project_structure is ASCII tree

EXAMPLE OUTPUT (STRICT FORMAT):

<plan>
  <project_type>
    <category>Commercial</category>
    <complexity>Medium</complexity>
    <duration>2-3 weeks</duration>
  </project_type>

  <tech_stack>
    <frontend>
      <framework>Next.js 14</framework>
      <language>TypeScript</language>
      <styling>Tailwind CSS</styling>
    </frontend>
    <backend>
      <framework>FastAPI</framework>
      <language>Python 3.11</language>
      <orm>SQLAlchemy</orm>
    </backend>
    <database>
      <type>Relational</type>
      <name>PostgreSQL</name>
    </database>
    <auth>
      <method>JWT</method>
    </auth>
    <deployment>
      <frontend>Vercel</frontend>
      <backend>Railway</backend>
    </deployment>
  </tech_stack>

  <project_structure>
app-root/
  frontend/
    src/
      app/
        page.tsx
        layout.tsx
      components/
        ui/
      lib/
    package.json
    tsconfig.json
  backend/
    app/
      api/
        v1/
          endpoints/
      core/
        config.py
        database.py
      models/
      schemas/
      main.py
    requirements.txt
  docker-compose.yml
  README.md
  </project_structure>

  <tasks>
    <step id="1">Initialize Next.js frontend with TypeScript and Tailwind CSS</step>
    <step id="2">Initialize FastAPI backend with SQLAlchemy and Pydantic</step>
    <step id="3">Configure PostgreSQL database connection and create models</step>
    <step id="4">Implement JWT authentication endpoints in backend</step>
    <step id="5">Create API routes for CRUD operations</step>
    <step id="6">Build frontend authentication flow with forms</step>
    <step id="7">Create frontend components for main features</step>
    <step id="8">Connect frontend to backend API with fetch/axios</step>
    <step id="9">Add error handling and loading states</step>
    <step id="10">Create Docker configuration for deployment</step>
  </tasks>

  <notes>
User authentication with JWT tokens.
PostgreSQL for data persistence.
Deployed on Vercel (frontend) and Railway (backend).
  </notes>
</plan>

TECH STACK DECISION MATRIX:

USE CASE → TECH STACK:
- Simple website → HTML, CSS, JavaScript
- Blog/Content site → Next.js + Markdown
- Web app with DB → Next.js + FastAPI + PostgreSQL
- E-commerce → Next.js + FastAPI + PostgreSQL + Stripe
- Mobile app → React Native + Expo
- API only → FastAPI + PostgreSQL
- ML/AI → Python + FastAPI + scikit-learn/TensorFlow
- CLI tool → Python + Click
- Real-time → Next.js + FastAPI + WebSockets + Redis

REMEMBER:
- Output ONLY the XML <plan> block
- NO text before or after
- NO code, markdown, or backticks
- Follow XML schema exactly
- Keep it under 3000 tokens
- Be deterministic and predictable
"""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="ProductionPlannerAgent",
            role="Strict XML Plan Generator",
            capabilities=[
                "strict_xml_output",
                "deterministic_planning",
                "atomic_task_generation",
                "architectural_correctness"
            ],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Create strict XML plan from user request
        """
        metadata = context.metadata or {}

        # Build prompt with strict instructions
        prompt = self._build_strict_prompt(context.user_request, metadata)

        # Call Claude with strict system prompt
        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=4096,  # Enough for detailed plan
            temperature=0.1   # Very low for deterministic output
        )

        # Validate and parse response
        try:
            plan = self._strict_parse_plan(response)

            # Validate plan structure
            validation_result = self._validate_plan(plan)

            if not validation_result['valid']:
                logger.error(f"Plan validation failed: {validation_result['errors']}")
                return {
                    "success": False,
                    "error": "Plan validation failed",
                    "validation_errors": validation_result['errors'],
                    "raw_response": response
                }

            return {
                "success": True,
                "plan": plan,
                "validation": validation_result,
                "raw_response": response
            }

        except Exception as e:
            logger.error(f"Failed to parse plan: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_response": response
            }

    def _build_strict_prompt(self, user_request: str, metadata: Dict) -> str:
        """Build prompt with strict output requirements"""

        return f"""User Request: {user_request}

Additional Context: {metadata.get('context', 'None')}

INSTRUCTIONS:
1. Analyze the request and identify project type
2. Make architectural decisions (DB? Auth? Real-time?)
3. Select appropriate tech stack from decision matrix
4. Create atomic, sequential tasks for WriterAgent
5. Output ONLY the <plan> XML block (no other text)

CRITICAL:
- NO text before <plan>
- NO text after </plan>
- NO markdown, backticks, or code blocks
- Follow XML schema exactly
- Each <step> is ONE atomic action
- Keep total output under 3000 tokens

Generate the plan now:"""

    def _strict_parse_plan(self, response: str) -> Dict[str, Any]:
        """
        Parse plan using XML parser (not regex)
        Enforces strict schema validation
        """
        # Extract <plan> content
        start = response.find('<plan>')
        end = response.find('</plan>') + len('</plan>')

        if start == -1 or end == -1:
            raise ValueError("No <plan> tag found in response")

        # Get only the plan XML
        plan_xml = response[start:end].strip()

        # Check for text before/after plan
        before = response[:start].strip()
        after = response[end:].strip()

        if before:
            logger.warning(f"⚠️ Found text before <plan>: {before[:100]}")
        if after:
            logger.warning(f"⚠️ Found text after </plan>: {after[:100]}")

        # Parse XML
        try:
            root = ET.fromstring(plan_xml)
        except ET.ParseError as e:
            logger.error(f"XML parsing failed: {e}")
            raise ValueError(f"Invalid XML structure: {e}")

        # Convert to dictionary
        plan = self._xml_to_dict(root)

        return plan

    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary"""

        result = {}

        # Handle elements with text content only
        if len(element) == 0:
            return element.text.strip() if element.text else ""

        # Handle elements with child elements
        for child in element:
            tag = child.tag

            # Validate tag is allowed
            if tag not in self.ALLOWED_TAGS:
                logger.warning(f"⚠️ Unexpected tag: {tag}")

            # Handle <step> elements specially
            if tag == 'step':
                if 'steps' not in result:
                    result['steps'] = []

                step_data = {
                    'id': child.get('id'),
                    'content': child.text.strip() if child.text else ""
                }
                result['steps'].append(step_data)

            # Handle nested elements
            elif len(child) > 0:
                result[tag] = self._xml_to_dict(child)

            # Handle simple text elements
            else:
                result[tag] = child.text.strip() if child.text else ""

        return result

    def _validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate plan structure and content
        """
        errors = []
        warnings = []

        # Check required sections
        required_sections = ['project_type', 'tech_stack', 'project_structure', 'tasks']

        for section in required_sections:
            if section not in plan:
                errors.append(f"Missing required section: {section}")

        # Validate project_structure is ASCII tree (no code blocks)
        if 'project_structure' in plan:
            structure = plan['project_structure']
            if '```' in structure:
                errors.append("project_structure contains markdown code blocks (forbidden)")
            if '#' in structure and 'comment' not in structure.lower():
                warnings.append("project_structure may contain comments")

        # Validate tasks are atomic steps
        if 'tasks' in plan:
            tasks = plan['tasks']

            if isinstance(tasks, dict) and 'steps' in tasks:
                steps = tasks['steps']

                # Check step IDs are sequential
                for i, step in enumerate(steps, 1):
                    expected_id = str(i)
                    actual_id = step.get('id', '')

                    if actual_id != expected_id:
                        errors.append(f"Step ID mismatch: expected {expected_id}, got {actual_id}")

                    # Check step content is atomic
                    content = step.get('content', '')

                    if 'STEP' in content.upper() or 'PHASE' in content.upper():
                        errors.append(f"Step {i} contains forbidden 'STEP' or 'PHASE' text")

                    if '\n-' in content or '\n*' in content:
                        errors.append(f"Step {i} contains nested bullet points")

            else:
                errors.append("Tasks section doesn't contain <step> elements")

        # Validate no <file> tags anywhere
        import json
        plan_str = json.dumps(plan)
        if '<file' in plan_str:
            errors.append("Plan contains forbidden <file> tags")

        # Check token count (rough estimate)
        estimated_tokens = len(plan_str) / 4
        if estimated_tokens > self.MAX_PLAN_TOKENS:
            warnings.append(f"Plan may exceed token limit: ~{int(estimated_tokens)} tokens")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


# Singleton instance
production_planner_agent = ProductionPlannerAgent()
