"""
Import Analyzer Agent - Token-Optimized version with chunked analysis
"""

import os
import yaml
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple
from pathlib import Path

from app.utils.claude_client import claude_client

logger = logging.getLogger(__name__)

# Token limits (approximate - 1 token ≈ 4 chars)
MAX_CONTEXT_TOKENS = 50000  # ~200KB of code
MAX_FILE_TOKENS = 8000      # ~32KB per file
CHUNK_SIZE_TOKENS = 30000   # Tokens per chunk for large projects
CHARS_PER_TOKEN = 4

# Priority file extensions (most likely to have issues)
PRIORITY_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs'}
CONFIG_EXTENSIONS = {'.json', '.yaml', '.yml', '.env', '.toml'}
LOW_PRIORITY = {'.md', '.txt', '.css', '.scss', '.html'}

# Critical files to always include (entry points, configs)
CRITICAL_FILES = {'main.py', 'app.py', 'index.js', 'index.ts', 'package.json',
                  'requirements.txt', 'pyproject.toml', 'Cargo.toml', 'go.mod'}


class ImportAnalyzerAgent:
    """Token-optimized agent for analyzing imported projects"""

    def __init__(self):
        self.config = self._load_config()
        self.system_prompt = self._load_system_prompt()

    def _load_config(self) -> Dict[str, Any]:
        config_path = Path(__file__).parent.parent.parent / "config" / "agent_config.yml"
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('agents', {}).get('import_analyzer', {
                    'model': 'sonnet',
                    'temperature': 0.5,
                    'max_tokens': 4096
                })
        except Exception as e:
            logger.warning(f"Config load error: {e}")
            return {'model': 'sonnet', 'temperature': 0.5, 'max_tokens': 4096}

    def _load_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "import_analyzer.txt"
        try:
            with open(prompt_path, 'r') as f:
                return f.read()
        except:
            return "Analyze code. Be concise. Report: Location, Severity, Issue, Fix."

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        return len(text) // CHARS_PER_TOKEN

    def _prioritize_files(self, files: List[Dict[str, Any]], analysis_type: str) -> List[Dict[str, Any]]:
        """Sort files by relevance to analysis type"""
        def get_priority(f):
            ext = Path(f.get('path', '')).suffix.lower()

            # Security analysis prioritizes config files
            if analysis_type == 'security':
                if ext in CONFIG_EXTENSIONS or '.env' in f.get('path', ''):
                    return 0
                if ext in PRIORITY_EXTENSIONS:
                    return 1
                return 2

            # Bug/performance analysis prioritizes code
            if ext in PRIORITY_EXTENSIONS:
                return 0
            if ext in CONFIG_EXTENSIONS:
                return 1
            if ext in LOW_PRIORITY:
                return 3
            return 2

        return sorted(files, key=get_priority)

    def _truncate_file(self, content: str, max_tokens: int = MAX_FILE_TOKENS) -> str:
        """Truncate large files, keeping start and end"""
        tokens = self._estimate_tokens(content)
        if tokens <= max_tokens:
            return content

        max_chars = max_tokens * CHARS_PER_TOKEN
        half = max_chars // 2
        return content[:half] + "\n\n... [TRUNCATED] ...\n\n" + content[-half:]

    def _build_optimized_context(self, files: List[Dict[str, Any]], analysis_type: str) -> str:
        """Build context with token budget"""
        sorted_files = self._prioritize_files(files, analysis_type)

        parts = []
        total_tokens = 0
        included = 0
        skipped = 0

        for f in sorted_files:
            content = f.get('content', '')
            path = f.get('path', 'unknown')
            lang = f.get('language', 'plaintext')

            # Skip empty files
            if not content.strip():
                continue

            # Truncate large files
            content = self._truncate_file(content)
            file_tokens = self._estimate_tokens(content)

            # Check budget
            if total_tokens + file_tokens > MAX_CONTEXT_TOKENS:
                skipped += 1
                continue

            parts.append(f"### {path}\n```{lang}\n{content}\n```")
            total_tokens += file_tokens
            included += 1

        if skipped > 0:
            parts.append(f"\n[Note: {skipped} files skipped due to size limit]")

        logger.info(f"Context: {included} files, ~{total_tokens} tokens, {skipped} skipped")
        return "\n\n".join(parts)

    def _chunk_files(self, files: List[Dict[str, Any]], analysis_type: str) -> List[List[Dict[str, Any]]]:
        """Split files into chunks that fit within token budget"""
        sorted_files = self._prioritize_files(files, analysis_type)
        chunks = []
        current_chunk = []
        current_tokens = 0

        # Always include critical files in first chunk
        critical = []
        non_critical = []
        for f in sorted_files:
            filename = Path(f.get('path', '')).name
            if filename in CRITICAL_FILES:
                critical.append(f)
            else:
                non_critical.append(f)

        # Start with critical files
        for f in critical:
            content = self._truncate_file(f.get('content', ''))
            tokens = self._estimate_tokens(content)
            current_chunk.append(f)
            current_tokens += tokens

        # Add non-critical files
        for f in non_critical:
            content = self._truncate_file(f.get('content', ''))
            tokens = self._estimate_tokens(content)

            if current_tokens + tokens > CHUNK_SIZE_TOKENS and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0

            current_chunk.append(f)
            current_tokens += tokens

        if current_chunk:
            chunks.append(current_chunk)

        logger.info(f"Split {len(files)} files into {len(chunks)} chunks")
        return chunks

    def _needs_chunking(self, files: List[Dict[str, Any]]) -> bool:
        """Check if files exceed single-call token budget"""
        total_tokens = sum(
            self._estimate_tokens(f.get('content', ''))
            for f in files
        )
        return total_tokens > MAX_CONTEXT_TOKENS

    def _get_token_stats(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get token statistics for files"""
        total_tokens = 0
        file_count = 0
        for f in files:
            content = f.get('content', '')
            if content.strip():
                total_tokens += self._estimate_tokens(content)
                file_count += 1
        return {
            'total_tokens': total_tokens,
            'file_count': file_count,
            'avg_tokens_per_file': total_tokens // max(file_count, 1),
            'estimated_cost_input': round(total_tokens * 0.003 / 1000, 4)  # Sonnet pricing
        }

    def _get_model_for_task(self, analysis_type: str, file_count: int) -> str:
        """Select model based on task complexity"""
        # Use Haiku for simple/quick tasks
        if analysis_type == 'docs' and file_count < 10:
            return 'haiku'
        if file_count < 5:
            return 'haiku'
        # Use Sonnet for complex analysis
        return self.config.get('model', 'sonnet')

    def _get_max_tokens_for_task(self, analysis_type: str) -> int:
        """Adjust output tokens based on task"""
        if analysis_type in ('bugs', 'security'):
            return 4096  # Detailed findings needed
        if analysis_type == 'docs':
            return 2048  # Shorter assessment
        if analysis_type == 'full':
            return 6000  # Comprehensive
        return 4096

    def _create_compact_prompt(self, analysis_type: str, code_context: str, project_name: str) -> str:
        """Create minimal prompts to save tokens"""

        prompts = {
            'bugs': f"""Project: {project_name}
Find bugs in this code. For each: location, severity, issue, fix.

{code_context}""",

            'security': f"""Project: {project_name}
Security audit. Check: injection, auth, secrets, validation. For each: location, severity, risk, fix.

{code_context}""",

            'performance': f"""Project: {project_name}
Find performance issues: complexity, queries, memory, blocking. For each: location, impact, fix.

{code_context}""",

            'docs': f"""Project: {project_name}
Assess documentation: coverage %, missing docs, recommendations.

{code_context}""",

            'full': f"""Project: {project_name}
Review: bugs, security, performance, quality. Top issues with fixes.

{code_context}"""
        }

        return prompts.get(analysis_type, prompts['full'])

    async def analyze_project(
        self,
        files: List[Dict[str, Any]],
        project_name: str,
        analysis_type: str = "full"
    ) -> AsyncGenerator[str, None]:
        """Analyze with token optimization and chunking for large projects"""

        # Get token stats for logging
        stats = self._get_token_stats(files)
        logger.info(f"Project stats: {stats}")

        # Check if chunking is needed
        if self._needs_chunking(files):
            yield f"\n📊 **Large project detected** ({stats['file_count']} files, ~{stats['total_tokens']} tokens)\n"
            yield f"Using chunked analysis for optimal token usage...\n\n"

            # Use chunked analysis
            async for chunk in self._analyze_chunked(files, project_name, analysis_type):
                yield chunk
        else:
            # Single-call analysis for smaller projects
            code_context = self._build_optimized_context(files, analysis_type)
            prompt = self._create_compact_prompt(analysis_type, code_context, project_name)

            model = self._get_model_for_task(analysis_type, len(files))
            max_tokens = self._get_max_tokens_for_task(analysis_type)

            logger.info(f"Analysis: type={analysis_type}, model={model}, max_out={max_tokens}")

            async for chunk in claude_client.generate_stream(
                prompt=prompt,
                system=self.system_prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=0.3  # Lower for more focused output
            ):
                yield chunk

    async def _analyze_chunked(
        self,
        files: List[Dict[str, Any]],
        project_name: str,
        analysis_type: str
    ) -> AsyncGenerator[str, None]:
        """Analyze large projects in chunks, then consolidate findings"""

        chunks = self._chunk_files(files, analysis_type)
        all_findings = []

        for i, chunk_files in enumerate(chunks):
            yield f"\n---\n### Analyzing chunk {i+1}/{len(chunks)} ({len(chunk_files)} files)...\n\n"

            code_context = self._build_optimized_context(chunk_files, analysis_type)

            # Use compact chunk prompt
            chunk_prompt = f"""Project: {project_name} (Chunk {i+1}/{len(chunks)})
Analysis type: {analysis_type}

{code_context}

Report issues found in this chunk only. Be concise."""

            model = self._get_model_for_task(analysis_type, len(chunk_files))
            chunk_findings = ""

            async for text in claude_client.generate_stream(
                prompt=chunk_prompt,
                system=self.system_prompt,
                model=model,
                max_tokens=2048,  # Smaller for chunks
                temperature=0.3
            ):
                yield text
                chunk_findings += text

            all_findings.append(chunk_findings)

        # Consolidate findings from all chunks
        if len(chunks) > 1:
            yield f"\n\n---\n### 📋 Consolidated Summary\n\n"

            consolidation_prompt = f"""Project: {project_name}
Analysis type: {analysis_type}

Findings from {len(chunks)} chunks:

{chr(10).join(f'--- Chunk {i+1} ---{chr(10)}{f}' for i, f in enumerate(all_findings))}

Create a prioritized summary: critical issues first, then high, medium, low.
Deduplicate similar issues. Max 10 issues."""

            async for text in claude_client.generate_stream(
                prompt=consolidation_prompt,
                system="Consolidate analysis findings. Be concise. Prioritize by severity.",
                model='haiku',  # Use Haiku for consolidation (cheaper)
                max_tokens=2048,
                temperature=0.3
            ):
                yield text

    async def fix_bugs(
        self,
        files: List[Dict[str, Any]],
        bug_description: str
    ) -> AsyncGenerator[str, None]:
        """Generate bug fixes"""

        # Only include relevant files (smaller context)
        context = self._build_optimized_context(files, 'bugs')

        prompt = f"""Bug: {bug_description}

Code:
{context}

Provide: 1) Root cause 2) Fixed code 3) What changed"""

        async for chunk in claude_client.generate_stream(
            prompt=prompt,
            system=self.system_prompt,
            model='sonnet',  # Always use Sonnet for fixes
            max_tokens=4096,
            temperature=0.3
        ):
            yield chunk

    async def generate_documentation(
        self,
        files: List[Dict[str, Any]],
        project_name: str,
        doc_type: str = "readme"
    ) -> AsyncGenerator[str, None]:
        """Generate docs with minimal context"""

        # For docs, we need structure more than full content
        context = self._build_optimized_context(files, 'docs')

        prompts = {
            'readme': f"Generate README.md for {project_name}:\n{context}",
            'srs': f"Generate SRS (IEEE 830) for {project_name}:\n{context}",
            'api': f"Generate API docs for {project_name}:\n{context}",
            'architecture': f"Generate architecture doc for {project_name}:\n{context}",
            'all': f"Generate: README, API docs, architecture for {project_name}:\n{context}"
        }

        prompt = prompts.get(doc_type, prompts['readme'])

        # Use Haiku for simple docs, Sonnet for complex
        model = 'haiku' if doc_type == 'readme' else 'sonnet'
        max_tokens = 8000 if doc_type == 'all' else 4096

        async for chunk in claude_client.generate_stream(
            prompt=prompt,
            system="Generate concise, professional documentation.",
            model=model,
            max_tokens=max_tokens,
            temperature=0.5
        ):
            yield chunk


# Singleton
import_analyzer_agent = ImportAnalyzerAgent()
