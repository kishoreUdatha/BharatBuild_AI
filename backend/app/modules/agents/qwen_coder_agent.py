"""
Qwen Coder Agent - Drop-in replacement for Claude-based code agent
Uses fine-tuned Qwen2.5-Coder model for code generation
"""
import os
import re
import json
import logging
import httpx
from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class QwenCoderConfig:
    """Configuration for Qwen Coder Agent"""
    # Model serving endpoint
    api_url: str = os.environ.get("QWEN_CODER_API_URL", "http://localhost:8001")

    # Generation parameters
    max_new_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50

    # Fallback to Claude
    fallback_enabled: bool = True
    fallback_on_error: bool = True

    # Timeout
    timeout: float = 120.0


class QwenCoderAgent(BaseAgent):
    """
    Code generation agent using fine-tuned Qwen2.5-Coder
    Drop-in replacement for Claude-based coder agent
    """

    def __init__(self, config: Optional[QwenCoderConfig] = None):
        super().__init__()
        self.config = config or QwenCoderConfig()
        self.name = "QwenCoderAgent"
        self.client = httpx.AsyncClient(timeout=self.config.timeout)
        self._fallback_agent = None

    @property
    def fallback_agent(self):
        """Lazy load fallback Claude agent"""
        if self._fallback_agent is None and self.config.fallback_enabled:
            from .coder_agent import CoderAgent
            self._fallback_agent = CoderAgent()
        return self._fallback_agent

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        project_context: Optional[Dict] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate code from prompt

        Args:
            prompt: User's code generation request
            system_prompt: Optional system prompt override
            project_context: Project context (tech_stack, requirements, etc.)
            stream: Enable streaming response

        Returns:
            Dict with 'code', 'files', 'tokens_used' keys
        """
        # Build enhanced prompt with project context
        full_prompt = self._build_prompt(prompt, project_context)

        try:
            if stream:
                return await self._stream_generate(full_prompt, system_prompt)
            else:
                return await self._generate(full_prompt, system_prompt)

        except Exception as e:
            logger.error(f"Qwen generation failed: {e}")

            if self.config.fallback_on_error and self.fallback_agent:
                logger.info("Falling back to Claude agent")
                return await self.fallback_agent.generate(prompt, project_context)

            raise

    async def _generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Non-streaming generation"""
        response = await self.client.post(
            f"{self.config.api_url}/generate",
            json={
                "prompt": prompt,
                "system_prompt": system_prompt,
                "max_new_tokens": self.config.max_new_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
                "stream": False,
            }
        )
        response.raise_for_status()
        data = response.json()

        # Parse response into files
        code = data.get("generated_code", "")
        files = self._parse_files(code)

        return {
            "code": code,
            "files": files,
            "tokens_used": data.get("tokens_generated", 0),
            "model": "qwen2.5-coder-finetuned",
        }

    async def _stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Streaming generation"""
        async with self.client.stream(
            "POST",
            f"{self.config.api_url}/generate",
            json={
                "prompt": prompt,
                "system_prompt": system_prompt,
                "max_new_tokens": self.config.max_new_tokens,
                "temperature": self.config.temperature,
                "stream": True,
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    token = line[6:]
                    if token != "[DONE]":
                        yield token

    def _build_prompt(
        self,
        prompt: str,
        project_context: Optional[Dict] = None,
    ) -> str:
        """Build enhanced prompt with project context"""
        parts = []

        if project_context:
            if project_context.get("tech_stack"):
                parts.append(f"Tech Stack: {project_context['tech_stack']}")
            if project_context.get("requirements"):
                parts.append(f"Requirements: {project_context['requirements']}")
            if project_context.get("existing_files"):
                parts.append(f"Existing files: {', '.join(project_context['existing_files'][:10])}")

        parts.append(prompt)

        return "\n\n".join(parts)

    def _parse_files(self, response: str) -> List[Dict]:
        """Parse generated response into file objects"""
        files = []

        # Match ### filename followed by code block
        pattern = r'###\s*([^\n]+)\n```(\w+)?\n(.*?)```'
        for match in re.finditer(pattern, response, re.DOTALL):
            filename = match.group(1).strip()
            language = match.group(2) or self._detect_language(filename)
            content = match.group(3).strip()

            files.append({
                "path": filename,
                "content": content,
                "language": language,
            })

        # Also match standalone code blocks without filenames
        if not files:
            pattern = r'```(\w+)?\n(.*?)```'
            for i, match in enumerate(re.finditer(pattern, response, re.DOTALL)):
                language = match.group(1) or "text"
                content = match.group(2).strip()

                ext = self._get_extension(language)
                files.append({
                    "path": f"generated_{i}{ext}",
                    "content": content,
                    "language": language,
                })

        return files

    def _detect_language(self, filename: str) -> str:
        """Detect language from filename"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.css': 'css',
            '.html': 'html',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.sql': 'sql',
            '.sh': 'bash',
        }
        for ext, lang in ext_map.items():
            if filename.endswith(ext):
                return lang
        return "text"

    def _get_extension(self, language: str) -> str:
        """Get file extension from language"""
        lang_map = {
            'python': '.py',
            'javascript': '.js',
            'typescript': '.ts',
            'tsx': '.tsx',
            'jsx': '.jsx',
            'css': '.css',
            'html': '.html',
            'json': '.json',
            'yaml': '.yaml',
            'sql': '.sql',
            'bash': '.sh',
        }
        return lang_map.get(language, '.txt')

    # High-level generation methods

    async def generate_component(
        self,
        component_name: str,
        component_type: str = "functional",
        props: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a React component"""
        response = await self.client.post(
            f"{self.config.api_url}/generate/component",
            json={
                "component_name": component_name,
                "component_type": component_type,
                "props": props,
                "features": features,
            }
        )
        response.raise_for_status()
        return response.json()

    async def generate_endpoint(
        self,
        resource: str,
        methods: List[str] = None,
        auth_required: bool = True,
    ) -> Dict[str, Any]:
        """Generate a FastAPI endpoint"""
        response = await self.client.post(
            f"{self.config.api_url}/generate/endpoint",
            json={
                "resource": resource,
                "methods": methods or ["GET", "POST", "PUT", "DELETE"],
                "auth_required": auth_required,
            }
        )
        response.raise_for_status()
        return response.json()

    async def generate_full_project(
        self,
        description: str,
        tech_stack: str,
        requirements: str,
    ) -> Dict[str, Any]:
        """Generate a complete project structure"""
        prompt = f"""Create a complete project with the following specifications:

Description: {description}
Tech Stack: {tech_stack}
Requirements: {requirements}

Generate all necessary files including:
1. Project configuration (package.json, requirements.txt, etc.)
2. Main application files
3. Components/modules
4. Database models/schemas
5. API routes
6. Basic styling

Provide the complete file structure with full code for each file."""

        return await self.generate(prompt)

    # Cleanup

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


# Factory function for easy instantiation
def create_qwen_coder_agent(
    api_url: str = None,
    fallback_enabled: bool = True,
) -> QwenCoderAgent:
    """Create a Qwen Coder Agent instance"""
    config = QwenCoderConfig(
        api_url=api_url or os.environ.get("QWEN_CODER_API_URL", "http://localhost:8001"),
        fallback_enabled=fallback_enabled,
    )
    return QwenCoderAgent(config)


# Hybrid agent that intelligently routes between Qwen and Claude
class HybridCoderAgent(BaseAgent):
    """
    Hybrid agent that routes between fine-tuned Qwen and Claude
    Uses Qwen for standard tasks, Claude for complex reasoning
    """

    def __init__(
        self,
        qwen_api_url: str = None,
        complexity_threshold: float = 0.7,
    ):
        super().__init__()
        self.qwen_agent = create_qwen_coder_agent(qwen_api_url)
        self.complexity_threshold = complexity_threshold
        self._claude_agent = None

    @property
    def claude_agent(self):
        """Lazy load Claude agent"""
        if self._claude_agent is None:
            from .coder_agent import CoderAgent
            self._claude_agent = CoderAgent()
        return self._claude_agent

    def _estimate_complexity(self, prompt: str) -> float:
        """Estimate task complexity (0-1)"""
        complexity_markers = [
            # High complexity
            ("architecture", 0.3),
            ("design pattern", 0.3),
            ("optimization", 0.2),
            ("security", 0.2),
            ("authentication flow", 0.2),
            ("database migration", 0.2),
            ("microservice", 0.3),
            ("distributed", 0.3),
            ("real-time", 0.2),
            ("websocket", 0.2),
            # Low complexity
            ("button", -0.1),
            ("form", -0.1),
            ("simple", -0.2),
            ("basic", -0.2),
        ]

        score = 0.5  # Base complexity
        prompt_lower = prompt.lower()

        for marker, weight in complexity_markers:
            if marker in prompt_lower:
                score += weight

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    async def generate(
        self,
        prompt: str,
        project_context: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Route to appropriate agent based on complexity"""
        complexity = self._estimate_complexity(prompt)

        if complexity > self.complexity_threshold:
            logger.info(f"Routing to Claude (complexity: {complexity:.2f})")
            return await self.claude_agent.generate(prompt, project_context, **kwargs)
        else:
            logger.info(f"Routing to Qwen (complexity: {complexity:.2f})")
            return await self.qwen_agent.generate(prompt, project_context=project_context, **kwargs)

    async def close(self):
        """Close both agents"""
        await self.qwen_agent.close()
