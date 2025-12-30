"""
AI Context Builder for Bolt.new-style code generation
Builds intelligent context from project files for Claude API
"""

from typing import List, Dict, Optional, Set
import re
from dataclasses import dataclass
from app.core.logging_config import logger


@dataclass
class ContextFile:
    path: str
    content: str
    language: str
    relevance_score: float
    reason: str


@dataclass
class AIContext:
    project_name: str
    project_type: str
    file_tree: str
    selected_files: List[ContextFile]
    tech_stack: List[str]
    dependencies: Optional[Dict[str, str]]
    current_file: Optional[str]
    user_goal: str


class BoltContextBuilder:
    """Build intelligent context for AI requests"""

    # Stop words for keyword extraction
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those'
    }

    def __init__(self):
        pass

    def build_context(
        self,
        user_prompt: str,
        files: List[Dict],
        project_name: str = "Project",
        selected_file_path: Optional[str] = None,
        max_files: int = 10,
        max_tokens: int = 50000
    ) -> AIContext:
        """
        Build intelligent context from project files

        Args:
            user_prompt: User's request
            files: List of file dicts with 'path', 'content', 'language'
            project_name: Project name
            selected_file_path: Currently selected file path
            max_files: Maximum files to include
            max_tokens: Approximate token limit

        Returns:
            AIContext object
        """
        # Detect project type and tech stack
        project_type = self._detect_project_type(files)
        tech_stack = self._detect_tech_stack(files)

        # Build file tree
        file_tree = self._build_file_tree(files)

        # Extract keywords from prompt
        keywords = self._extract_keywords(user_prompt)

        # Score and rank files
        scored_files = []
        for file in files:
            if file.get('type') == 'folder':
                continue

            score = self._calculate_relevance(
                file,
                keywords,
                selected_file_path
            )

            if score > 0:
                scored_files.append({
                    'file': file,
                    'score': score
                })

        # Sort by score and limit
        scored_files.sort(key=lambda x: x['score'], reverse=True)
        scored_files = scored_files[:max_files]

        # Convert to ContextFile objects with token limiting
        selected_files = []
        total_tokens = 0

        for item in scored_files:
            file = item['file']
            content = file.get('content', '')
            file_tokens = self._estimate_tokens(content)

            if total_tokens + file_tokens > max_tokens:
                break

            selected_files.append(ContextFile(
                path=file['path'],
                content=content,
                language=file.get('language', 'plaintext'),
                relevance_score=item['score'],
                reason=self._get_inclusion_reason(
                    file,
                    selected_file_path,
                    keywords
                )
            ))

            total_tokens += file_tokens

        return AIContext(
            project_name=project_name,
            project_type=project_type,
            file_tree=file_tree,
            selected_files=selected_files,
            tech_stack=tech_stack,
            dependencies=self._extract_dependencies(files),
            current_file=selected_file_path,
            user_goal=user_prompt
        )

    def format_for_claude(self, context: AIContext) -> str:
        """Format context for Claude API"""
        prompt = f"# Project: {context.project_name}\n\n"

        prompt += f"## Project Type\n{context.project_type}\n\n"

        if context.tech_stack:
            prompt += f"## Tech Stack\n{', '.join(context.tech_stack)}\n\n"

        prompt += f"## File Structure\n```\n{context.file_tree}```\n\n"

        if context.selected_files:
            prompt += "## Relevant Files\n\n"

            for file in context.selected_files:
                prompt += f"### {file.path}\n"
                if file.reason:
                    prompt += f"*{file.reason}*\n\n"
                prompt += f"```{file.language}\n{file.content}\n```\n\n"

        if context.current_file:
            prompt += f"## Current File\n{context.current_file}\n\n"

        prompt += f"## User Request\n{context.user_goal}\n\n"

        return prompt

    def _detect_project_type(self, files: List[Dict]) -> str:
        """Detect project type from files"""
        file_paths = [f['path'] for f in files]

        has_file = lambda pattern: any(re.search(pattern, path) for path in file_paths)

        if has_file(r'package\.json'):
            if has_file(r'next\.config'):
                return 'nextjs'
            if has_file(r'vite\.config|App\.(tsx|jsx)'):
                return 'react'
            if has_file(r'vue\.config|App\.vue'):
                return 'vue'
            return 'node'

        if has_file(r'requirements\.txt|setup\.py|__init__\.py'):
            return 'python'

        if has_file(r'pom\.xml|build\.gradle|\.java$'):
            return 'java'

        return 'unknown'

    def _detect_tech_stack(self, files: List[Dict]) -> List[str]:
        """Detect tech stack from files"""
        stack = []

        # Find package.json
        package_json = next(
            (f for f in files if f['path'] == 'package.json'),
            None
        )

        if package_json and package_json.get('content'):
            try:
                import json
                pkg = json.loads(package_json['content'])
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

                if 'react' in deps:
                    stack.append('React')
                if 'next' in deps:
                    stack.append('Next.js')
                if 'vue' in deps:
                    stack.append('Vue')
                if 'express' in deps:
                    stack.append('Express')
                if 'typescript' in deps:
                    stack.append('TypeScript')
                if 'tailwindcss' in deps:
                    stack.append('Tailwind CSS')
                if 'vite' in deps:
                    stack.append('Vite')
            except (json.JSONDecodeError, IOError, OSError, KeyError) as e:
                logger.debug(f"Could not parse package.json for tech stack: {e}")

        # Detect from extensions
        has_ext = lambda ext: any(f['path'].endswith(ext) for f in files)

        if has_ext('.ts') or has_ext('.tsx'):
            if 'TypeScript' not in stack:
                stack.append('TypeScript')
        if has_ext('.py'):
            stack.append('Python')
        if has_ext('.java'):
            stack.append('Java')

        return stack

    def _calculate_relevance(
        self,
        file: Dict,
        keywords: Set[str],
        selected_file_path: Optional[str]
    ) -> float:
        """Calculate file relevance score"""
        score = 0.0

        # Current/selected file gets highest priority
        if selected_file_path and file['path'] == selected_file_path:
            score += 100

        # Keyword matching in filename
        file_name = file['path'].lower()
        for keyword in keywords:
            if keyword in file_name:
                score += 30

        # Keyword matching in content
        content = (file.get('content') or '').lower()
        for keyword in keywords:
            if keyword in content:
                score += 20

        # File type bonuses
        if re.search(r'\.(tsx?|jsx?)$', file['path']):
            score += 15  # Source files
        if 'component' in file_name:
            score += 10
        if 'util' in file_name or 'helper' in file_name:
            score += 8
        if 'type' in file_name or 'interface' in file_name:
            score += 5

        # Penalties
        if re.search(r'\.(test|spec)\.', file['path']):
            score -= 50
        if re.search(r'\.(config|rc)\.', file['path']):
            score -= 30
        if 'node_modules' in file['path']:
            score = 0
        if '.git' in file['path']:
            score = 0
        if re.search(r'\.(lock|log)$', file['path']):
            score = 0

        return max(0, score)

    def _extract_keywords(self, prompt: str) -> Set[str]:
        """Extract keywords from user prompt"""
        words = re.sub(r'[^\w\s]', ' ', prompt.lower()).split()
        keywords = {
            word for word in words
            if len(word) > 2 and word not in self.STOP_WORDS
        }
        return keywords

    def _build_file_tree(self, files: List[Dict]) -> str:
        """Build text representation of file tree"""
        tree = {}

        for file in files:
            parts = file['path'].split('/')
            current = tree

            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = file.get('type', 'file')
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        return self._format_tree(tree, 0)

    def _format_tree(self, node: Dict, indent: int) -> str:
        """Format tree structure"""
        result = ""
        entries = sorted(node.items())

        for name, value in entries:
            prefix = "  " * indent
            icon = "📁" if isinstance(value, dict) else "📄"
            result += f"{prefix}{icon} {name}\n"

            if isinstance(value, dict):
                result += self._format_tree(value, indent + 1)

        return result

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 1 token ≈ 4 characters)"""
        return len(text) // 4

    def _get_inclusion_reason(
        self,
        file: Dict,
        selected_file_path: Optional[str],
        keywords: Set[str]
    ) -> str:
        """Get reason for file inclusion"""
        if selected_file_path and file['path'] == selected_file_path:
            return "Currently selected file"

        matched_keywords = [
            k for k in keywords
            if k in file['path'].lower() or k in (file.get('content') or '').lower()
        ]

        if matched_keywords:
            return f"Matches keywords: {', '.join(list(matched_keywords)[:3])}"

        if re.search(r'\.(tsx?|jsx?)$', file['path']):
            return "Main source file"

        return "Related to project"

    def _extract_dependencies(self, files: List[Dict]) -> Optional[Dict[str, str]]:
        """Extract dependencies from package.json"""
        package_json = next(
            (f for f in files if f['path'] == 'package.json'),
            None
        )

        if package_json and package_json.get('content'):
            try:
                import json
                pkg = json.loads(package_json['content'])
                return {
                    **pkg.get('dependencies', {}),
                    **pkg.get('devDependencies', {})
                }
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.debug(f"Could not parse package.json dependencies: {e}")

        return None


# Singleton instance
context_builder = BoltContextBuilder()
