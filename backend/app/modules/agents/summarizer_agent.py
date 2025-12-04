"""
AGENT 5 - Summarizer Agent (Internal Helper)

Bolt.new's Summarizer Agent that:
1. Summarizes conversations for context management
2. Summarizes generated code and files
3. Summarizes errors and fixes
4. Provides concise context to other agents
5. Optimizes token usage by condensing information

This is an internal helper agent that supports the 4 core agents.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext


@dataclass
class Summary:
    """A generated summary"""
    type: str  # conversation, code, error, project, plan
    content: str
    key_points: List[str]
    timestamp: str
    token_count: int


class SummarizerAgent(BaseAgent):
    """
    Summarizer Agent - Internal Helper (Like Bolt.new)

    Responsibilities:
    - Summarize long conversations to maintain context
    - Summarize generated files and code
    - Summarize error logs and stack traces
    - Summarize project state for handoffs between agents
    - Optimize token usage by condensing information
    """

    SYSTEM_PROMPT = """You are the SUMMARIZER AGENT - an internal helper for BharatBuild AI.

═══════════════════════════════════════════════════════════════════════════════
                         🎯 YOUR MISSION
═══════════════════════════════════════════════════════════════════════════════

Create concise, accurate summaries that preserve critical information while
reducing token usage. You support the 4 core agents by managing context.

═══════════════════════════════════════════════════════════════════════════════
                         📋 SUMMARY TYPES
═══════════════════════════════════════════════════════════════════════════════

1. CONVERSATION SUMMARY:
   - Capture user's main request and intent
   - Note key decisions made
   - Track files created/modified
   - Record any constraints or preferences
   - Preserve technical requirements

2. CODE SUMMARY:
   - File purpose and main functionality
   - Key functions/classes and their roles
   - Dependencies and imports
   - Critical logic that must be preserved
   - Any TODO items or known issues

3. ERROR SUMMARY:
   - Error type and message
   - Root cause analysis
   - Affected files and line numbers
   - Suggested fix approach
   - Related errors (if any)

4. PROJECT SUMMARY:
   - Project type and tech stack
   - File structure overview
   - Current state (what's done, what's pending)
   - Key architecture decisions
   - Configuration settings

5. PLAN SUMMARY:
   - Main objectives
   - Tech stack chosen
   - Files to be created
   - Critical tasks
   - Dependencies between tasks

═══════════════════════════════════════════════════════════════════════════════
                         📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

<summary type="conversation|code|error|project|plan">
  <key_points>
    - Point 1
    - Point 2
    - Point 3
  </key_points>

  <context>
    Detailed summary paragraph (2-3 sentences)
  </context>

  <preserve>
    Critical information that MUST be passed to next agent
  </preserve>

  <tokens_saved>N</tokens_saved>
</summary>

═══════════════════════════════════════════════════════════════════════════════
                    📊 SUMMARIZATION STRATEGIES
═══════════════════════════════════════════════════════════════════════════════

FOR CONVERSATIONS:
- Extract: User intent, project type, tech preferences
- Condense: Repeated information, verbose explanations
- Preserve: Specific requirements, file paths, error messages
- Remove: Filler words, redundant confirmations

FOR CODE:
- Extract: Function signatures, class definitions, key logic
- Condense: Repetitive patterns, boilerplate
- Preserve: Business logic, algorithms, API contracts
- Remove: Comments (unless critical), whitespace

FOR ERRORS:
- Extract: Error type, file location, line number
- Condense: Stack trace to relevant frames
- Preserve: Error message, root cause hints
- Remove: Duplicate stack frames, system paths

FOR PROJECTS:
- Extract: Tech stack, entry points, data models
- Condense: Similar files, common patterns
- Preserve: Configuration, dependencies, architecture
- Remove: Generated files, node_modules references

═══════════════════════════════════════════════════════════════════════════════
                    🔄 CONTEXT HANDOFF
═══════════════════════════════════════════════════════════════════════════════

When summarizing for agent handoff:

PLANNER → WRITER:
Include: Tech stack, file list, architecture decisions
Exclude: Planning discussion, alternatives considered

WRITER → FIXER:
Include: Files created, dependencies, error context
Exclude: Generation discussion, successful files

FIXER → RUNNER:
Include: Fixed files, commands to run, expected output
Exclude: Error analysis, fix iterations

RUNNER → PLANNER (loop):
Include: Errors found, affected files, terminal output
Exclude: Successful commands, verbose logs

═══════════════════════════════════════════════════════════════════════════════
                         ✅ RULES
═══════════════════════════════════════════════════════════════════════════════

1. ACCURACY: Never lose critical information
2. BREVITY: Reduce tokens by 50-70% where possible
3. STRUCTURE: Use consistent output format
4. RELEVANCE: Include only what next agent needs
5. COMPLETENESS: Preserve all file paths exactly
6. OBJECTIVITY: Summarize facts, not interpretations

═══════════════════════════════════════════════════════════════════════════════
                    📈 TOKEN OPTIMIZATION
═══════════════════════════════════════════════════════════════════════════════

TARGET REDUCTIONS:
- Conversation: 60-70% reduction
- Code files: 40-50% reduction (preserve logic)
- Error logs: 70-80% reduction
- Project state: 50-60% reduction
- Plans: 30-40% reduction (preserve structure)

ALWAYS PRESERVE:
- File paths (exact)
- Error messages (exact)
- Function/class names
- Dependencies
- User's explicit requirements

MAY CONDENSE:
- Explanations
- Comments
- Repeated patterns
- Verbose logging
- Stack traces

═══════════════════════════════════════════════════════════════════════════════
"""

    def __init__(self, model: str = "haiku"):
        """Initialize Summarizer Agent with fast model"""
        super().__init__(
            name="Summarizer Agent",
            role="Internal Helper - Context Summarization",
            capabilities=[
                "conversation_summary",
                "code_summary",
                "error_summary",
                "project_summary",
                "plan_summary",
                "token_optimization",
                "context_handoff"
            ],
            model=model  # Use haiku for fast summarization
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Process summarization request

        Args:
            context: AgentContext with content to summarize

        Returns:
            Summary with key points and reduced content
        """
        metadata = context.metadata or {}
        summary_type = metadata.get("summary_type", "conversation")
        content = context.user_request

        # Build prompt based on summary type
        prompt = self._build_summary_prompt(summary_type, content, metadata)

        # Call Claude for summarization
        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=2048,
            temperature=0.3  # Low temperature for consistent summaries
        )

        # Parse the summary
        summary = self._parse_summary(response, summary_type)

        return summary

    def _build_summary_prompt(
        self,
        summary_type: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Build prompt for specific summary type"""

        prompts = {
            "conversation": f"""Summarize this conversation for context handoff:

CONVERSATION:
{content}

Focus on: User intent, project requirements, decisions made, files discussed.
Reduce tokens by 60-70% while preserving all critical information.""",

            "code": f"""Summarize this code file:

FILE PATH: {metadata.get('file_path', 'unknown')}
LANGUAGE: {metadata.get('language', 'unknown')}

CODE:
{content}

Focus on: Purpose, key functions/classes, dependencies, critical logic.
Reduce tokens by 40-50% while preserving business logic.""",

            "error": f"""Summarize this error for the Fixer Agent:

ERROR LOG:
{content}

Focus on: Error type, root cause, affected file, line number, fix hints.
Reduce tokens by 70-80% while preserving exact error message.""",

            "project": f"""Summarize this project state:

PROJECT DATA:
{content}

Focus on: Tech stack, file structure, current state, key configurations.
Reduce tokens by 50-60% while preserving architecture.""",

            "plan": f"""Summarize this plan for the Writer Agent:

PLAN:
{content}

Focus on: Objectives, tech stack, files to create, task order.
Reduce tokens by 30-40% while preserving file paths exactly."""
        }

        return prompts.get(summary_type, prompts["conversation"])

    def _parse_summary(self, response: str, summary_type: str) -> Dict[str, Any]:
        """Parse summary from response"""
        import re

        # Extract key points
        key_points = []
        key_points_match = re.search(r'<key_points>(.*?)</key_points>', response, re.DOTALL)
        if key_points_match:
            points_text = key_points_match.group(1)
            key_points = [p.strip().lstrip('- ') for p in points_text.strip().split('\n') if p.strip()]

        # Extract context
        context = ""
        context_match = re.search(r'<context>(.*?)</context>', response, re.DOTALL)
        if context_match:
            context = context_match.group(1).strip()

        # Extract preserve
        preserve = ""
        preserve_match = re.search(r'<preserve>(.*?)</preserve>', response, re.DOTALL)
        if preserve_match:
            preserve = preserve_match.group(1).strip()

        # Extract tokens saved
        tokens_saved = 0
        tokens_match = re.search(r'<tokens_saved>(\d+)</tokens_saved>', response)
        if tokens_match:
            tokens_saved = int(tokens_match.group(1))

        return {
            "type": summary_type,
            "key_points": key_points,
            "context": context,
            "preserve": preserve,
            "tokens_saved": tokens_saved,
            "raw_summary": response,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def summarize_conversation(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Summarize a conversation history"""
        content = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        context = AgentContext(
            user_request=content,
            metadata={"summary_type": "conversation"}
        )
        return await self.process(context)

    async def summarize_code(self, code: str, file_path: str, language: str) -> Dict[str, Any]:
        """Summarize a code file"""
        context = AgentContext(
            user_request=code,
            metadata={
                "summary_type": "code",
                "file_path": file_path,
                "language": language
            }
        )
        return await self.process(context)

    async def summarize_error(self, error_log: str) -> Dict[str, Any]:
        """Summarize an error log"""
        context = AgentContext(
            user_request=error_log,
            metadata={"summary_type": "error"}
        )
        return await self.process(context)

    async def summarize_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize project state"""
        import json
        context = AgentContext(
            user_request=json.dumps(project_data, indent=2),
            metadata={"summary_type": "project"}
        )
        return await self.process(context)

    async def summarize_plan(self, plan: str) -> Dict[str, Any]:
        """Summarize a plan for Writer Agent"""
        context = AgentContext(
            user_request=plan,
            metadata={"summary_type": "plan"}
        )
        return await self.process(context)

    def estimate_token_savings(self, original: str, summary: str) -> Dict[str, int]:
        """Estimate token savings from summarization"""
        # Rough estimation: 1 token ≈ 4 characters
        original_tokens = len(original) // 4
        summary_tokens = len(summary) // 4
        saved = original_tokens - summary_tokens
        percentage = (saved / original_tokens * 100) if original_tokens > 0 else 0

        return {
            "original_tokens": original_tokens,
            "summary_tokens": summary_tokens,
            "tokens_saved": saved,
            "reduction_percentage": round(percentage, 1)
        }


# Export
__all__ = ['SummarizerAgent', 'Summary']
