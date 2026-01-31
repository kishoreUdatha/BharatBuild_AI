"""
Verification Agent - Validates and verifies generated project files

This agent runs AFTER the Writer Agent to ensure:
1. All expected files from the plan were generated
2. Files have sufficient/complete code (not truncated)
3. Critical files exist (entry points, configs)
4. Code structure is valid (imports, syntax)

If issues are found, it can:
- Report missing files
- Regenerate incomplete files
- Fix common issues automatically
"""

from typing import Dict, List, Optional, Any, AsyncGenerator, Tuple
from datetime import datetime
import re
import json

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.utils.claude_client import ClaudeClient


class VerificationAgent(BaseAgent):
    """
    Verification Agent - Ensures project files are complete and correct

    Runs after Writer Agent to validate:
    - File count matches plan expectations
    - Files have meaningful content (not empty/truncated)
    - Critical files exist
    - Code syntax is valid
    """

    SYSTEM_PROMPT = """You are the VERIFICATION AGENT.

YOUR JOB:
1. Analyze the plan and compare against generated files
2. Identify missing or incomplete files
3. Check if code is complete (not truncated mid-function)
4. Verify imports, exports, and dependencies are correct

OUTPUT FORMAT:
You MUST output a JSON object with this exact structure:
```json
{
    "status": "pass" | "fail" | "partial",
    "summary": "Brief summary of verification results",
    "files_verified": [
        {
            "path": "file/path.ts",
            "status": "complete" | "incomplete" | "missing" | "empty",
            "issues": ["list of issues found"],
            "suggestions": ["list of fix suggestions"]
        }
    ],
    "missing_files": ["list of files that should exist but don't"],
    "incomplete_files": ["list of files that appear truncated"],
    "critical_issues": ["list of blocking issues"],
    "regenerate_files": ["list of files that need to be regenerated"]
}
```

VERIFICATION RULES:
1. Entry point files (index.html, main.tsx, App.tsx) MUST exist
2. Config files (package.json, tsconfig.json) MUST have valid JSON/content
3. Component files MUST have proper React exports
4. CSS files MUST have meaningful styles (not just comments)
5. Files should NOT end mid-function or mid-statement
6. Import statements should reference files that exist
7. Export statements should export defined items

COMPLETENESS CHECKS:
- Functions should have opening AND closing braces
- JSX components should have return statements
- CSS should have style rules, not just empty selectors
- JSON should be valid and complete
- HTML should have closing tags

BE STRICT: If a file looks incomplete, mark it as incomplete.
"""

    # Minimum content lengths for different file types
    MIN_CONTENT_LENGTH = {
        # JavaScript/TypeScript
        '.tsx': 100,    # React components need substantial code
        '.jsx': 100,
        '.ts': 50,      # TypeScript files
        '.js': 50,      # JavaScript files
        '.vue': 100,    # Vue components
        '.svelte': 80,  # Svelte components
        # Web
        '.css': 30,     # CSS needs some rules
        '.scss': 30,    # SASS
        '.html': 50,    # HTML needs basic structure
        '.json': 10,    # JSON needs at least {}
        # Python
        '.py': 30,      # Python files
        '.ipynb': 50,   # Jupyter notebooks
        # Mobile
        '.dart': 80,    # Flutter/Dart
        '.swift': 50,   # iOS Swift
        '.kt': 50,      # Kotlin
        '.java': 50,    # Java
        # Systems
        '.go': 50,      # Go
        '.rs': 50,      # Rust
        '.cpp': 50,     # C++
        '.c': 30,       # C
        '.h': 20,       # Headers
        '.hpp': 20,     # C++ headers
        # Config
        '.yaml': 10,    # YAML config
        '.yml': 10,     # YAML config
        '.toml': 10,    # Rust/Python config
        '.xml': 20,     # XML config
        '.gradle': 20,  # Gradle build
        # Other
        '.md': 20,      # Markdown needs some content
        '.sql': 20,     # SQL files
        '.sh': 10,      # Shell scripts
        '.dockerfile': 10,  # Docker
        'default': 20
    }

    # Critical files that MUST exist for different project types
    # NOTE: These are enforced in bolt_instant mode too!
    CRITICAL_FILES = {
        # JavaScript/TypeScript Frontend - VITE + TAILWIND (Most common setup)
        'react': [
            'package.json',
            'index.html',
            'src/main.tsx',
            'src/App.tsx',
            'vite.config.ts',  # CRITICAL: Build fails without this
            'tsconfig.json',
            'tsconfig.node.json',  # CRITICAL: Most commonly missed!
            'tailwind.config.js',
            'postcss.config.js',
        ],
        'react-vite': [  # Explicit Vite variant
            'package.json',
            'index.html',
            'src/main.tsx',
            'src/App.tsx',
            'vite.config.ts',
            'tsconfig.json',
            'tsconfig.node.json',
            'tailwind.config.js',
            'postcss.config.js',
        ],
        'react-js': ['package.json', 'index.html', 'src/main.jsx', 'src/App.jsx', 'vite.config.js'],
        'nextjs': ['package.json', 'app/layout.tsx', 'app/page.tsx', 'tailwind.config.ts', 'next.config.js'],
        'vue': ['package.json', 'index.html', 'src/main.ts', 'src/App.vue', 'vite.config.ts'],
        'angular': ['package.json', 'angular.json', 'src/main.ts', 'src/app/app.component.ts'],
        'svelte': ['package.json', 'svelte.config.js', 'src/routes/+page.svelte', 'vite.config.ts'],
        # Backend
        'node': ['package.json', 'src/index.js'],
        'express': ['package.json', 'src/index.js', 'src/app.js'],
        'nestjs': ['package.json', 'src/main.ts', 'src/app.module.ts'],
        # Python
        'python': ['requirements.txt', 'main.py'],
        'fastapi': ['requirements.txt', 'main.py'],
        'django': ['requirements.txt', 'manage.py'],
        'flask': ['requirements.txt', 'app.py'],
        'streamlit': ['requirements.txt', 'app.py'],
        'ml-python': ['requirements.txt', 'main.py', 'src/model.py'],
        # Mobile
        'flutter': ['pubspec.yaml', 'lib/main.dart'],
        'react-native': ['package.json', 'App.tsx'],
        'android': ['build.gradle', 'app/src/main/java'],
        'ios': ['Package.swift'],
        # Java
        'spring-boot': ['pom.xml', 'src/main/java'],
        'java-gradle': ['build.gradle', 'src/main/java'],
        # Go
        'go': ['go.mod', 'main.go'],
        # Rust
        'rust': ['Cargo.toml', 'src/main.rs'],
        # IoT/Embedded
        'arduino': ['platformio.ini'],
        'esp32': ['platformio.ini', 'src/main.cpp'],
        # Static
        'html': ['index.html'],
        'default': ['README.md']
    }

    def __init__(self, model: str = "haiku"):
        super().__init__(
            name="Verification Agent",
            role="file_verification",
            capabilities=[
                "file_completeness_check",
                "syntax_validation",
                "missing_file_detection",
                "code_structure_verification"
            ],
            model=model
        )
        self.claude_client = ClaudeClient()

    async def verify_project(
        self,
        project_id: str,
        plan: Dict[str, Any],
        files_created: List[Dict[str, Any]],
        tech_stack: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verify all generated files against the plan

        Args:
            project_id: Project identifier
            plan: The execution plan from Planner Agent
            files_created: List of files created by Writer Agent
            tech_stack: Detected tech stack

        Returns:
            Verification result with status, issues, and files to regenerate
        """
        logger.info(f"[Verification Agent] Starting verification for project {project_id}")
        logger.info(f"[Verification Agent] Files to verify: {len(files_created)}")

        result = {
            "status": "pass",
            "summary": "",
            "files_verified": [],
            "missing_files": [],
            "incomplete_files": [],
            "empty_files": [],
            "critical_issues": [],
            "regenerate_files": [],
            "statistics": {
                "total_files": len(files_created),
                "complete_files": 0,
                "incomplete_files": 0,
                "empty_files": 0,
                "missing_files": 0
            }
        }

        # Step 1: Basic file verification (no LLM needed)
        basic_issues = self._verify_files_basic(files_created)

        result["empty_files"] = basic_issues["empty_files"]
        result["incomplete_files"] = basic_issues["incomplete_files"]
        result["files_verified"] = basic_issues["file_details"]
        result["statistics"]["empty_files"] = len(basic_issues["empty_files"])
        result["statistics"]["incomplete_files"] = len(basic_issues["incomplete_files"])

        # Step 2: Check for critical missing files
        project_type = self._detect_project_type(files_created, tech_stack)
        missing_critical = self._check_critical_files(files_created, project_type)

        if missing_critical:
            result["missing_files"].extend(missing_critical)
            result["critical_issues"].append(f"Missing critical files: {', '.join(missing_critical)}")
            result["statistics"]["missing_files"] = len(missing_critical)

        # Step 2.5: IMPORT VALIDATION (PRODUCTION FIX)
        # Check if all local imports in source files resolve to actual files
        import_issues = self._validate_imports(files_created)
        if import_issues["missing_imports"]:
            logger.warning(f"[Verification Agent] Found {len(import_issues['missing_imports'])} missing import targets!")
            for mi in import_issues["missing_imports"]:
                logger.warning(f"  - {mi['source_file']} imports '{mi['import_path']}' which doesn't exist")
                if mi["suggested_path"] not in result["missing_files"]:
                    result["missing_files"].append(mi["suggested_path"])
            result["critical_issues"].append(
                f"Missing {len(import_issues['missing_imports'])} imported files - will cause build errors"
            )
            result["statistics"]["missing_files"] = len(result["missing_files"])

        # Step 3: Use LLM for deeper verification if there are issues
        if basic_issues["empty_files"] or basic_issues["incomplete_files"] or missing_critical:
            llm_result = await self._verify_with_llm(
                plan=plan,
                files_created=files_created,
                basic_issues=basic_issues
            )

            # Merge LLM findings
            if llm_result.get("regenerate_files"):
                result["regenerate_files"].extend(llm_result["regenerate_files"])
            if llm_result.get("critical_issues"):
                result["critical_issues"].extend(llm_result["critical_issues"])
            if llm_result.get("missing_files"):
                for mf in llm_result["missing_files"]:
                    if mf not in result["missing_files"]:
                        result["missing_files"].append(mf)

        # Step 4: Determine overall status
        result["statistics"]["complete_files"] = (
            result["statistics"]["total_files"] -
            result["statistics"]["empty_files"] -
            result["statistics"]["incomplete_files"]
        )

        if result["critical_issues"] or result["empty_files"]:
            result["status"] = "fail"
            result["summary"] = f"Verification failed: {len(result['empty_files'])} empty files, {len(result['incomplete_files'])} incomplete files, {len(result['missing_files'])} missing files"
        elif result["incomplete_files"] or result["missing_files"]:
            result["status"] = "partial"
            result["summary"] = f"Partial verification: {len(result['incomplete_files'])} files may be incomplete"
        else:
            result["status"] = "pass"
            result["summary"] = f"All {len(files_created)} files verified successfully"

        # Add files to regenerate
        result["regenerate_files"] = list(set(
            result["empty_files"] +
            result["incomplete_files"] +
            result["missing_files"]
        ))

        logger.info(f"[Verification Agent] Result: {result['status']} - {result['summary']}")

        return result

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Required abstract method implementation from BaseAgent.
        Delegates to verify_project for actual verification logic.
        """
        return await self.verify_project(
            project_id=context.project_id,
            plan=context.metadata.get("plan", {}),
            files_created=context.metadata.get("files_created", []),
            tech_stack=context.metadata.get("tech_stack")
        )

    def _verify_files_basic(self, files_created: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Basic file verification without LLM

        Checks:
        - File is not empty
        - File meets minimum length requirements
        - File doesn't end mid-statement
        - Basic syntax patterns
        """
        issues = {
            "empty_files": [],
            "incomplete_files": [],
            "file_details": []
        }

        for file_info in files_created:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            file_detail = {
                "path": file_path,
                "status": "complete",
                "issues": [],
                "content_length": len(content),
                "line_count": content.count('\n') + 1 if content else 0
            }

            # Check 1: Empty file
            if not content or not content.strip():
                file_detail["status"] = "empty"
                file_detail["issues"].append("File is empty")
                issues["empty_files"].append(file_path)
                issues["file_details"].append(file_detail)
                continue

            # Check 2: Minimum length
            ext = self._get_extension(file_path)
            min_length = self.MIN_CONTENT_LENGTH.get(ext, self.MIN_CONTENT_LENGTH['default'])

            if len(content.strip()) < min_length:
                file_detail["status"] = "incomplete"
                file_detail["issues"].append(f"File too short ({len(content)} chars, minimum {min_length})")
                issues["incomplete_files"].append(file_path)

            # Check 3: Truncation indicators
            truncation_issues = self._check_truncation(content, ext)
            if truncation_issues:
                file_detail["status"] = "incomplete"
                file_detail["issues"].extend(truncation_issues)
                if file_path not in issues["incomplete_files"]:
                    issues["incomplete_files"].append(file_path)

            # Check 4: Basic syntax validation
            syntax_issues = self._check_basic_syntax(content, ext)
            if syntax_issues:
                file_detail["issues"].extend(syntax_issues)
                # Syntax issues are warnings, not necessarily incomplete

            issues["file_details"].append(file_detail)

        return issues

    def _check_truncation(self, content: str, ext: str) -> List[str]:
        """Check for signs of truncated code"""
        issues = []

        # Strip trailing whitespace for analysis
        content = content.rstrip()

        # Check for unbalanced braces (common truncation sign)
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces > close_braces:
            issues.append(f"Unbalanced braces: {open_braces} open, {close_braces} close - possible truncation")

        # Check for unbalanced parentheses
        open_parens = content.count('(')
        close_parens = content.count(')')
        if open_parens > close_parens + 1:  # Allow 1 difference for edge cases
            issues.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")

        # Check for common truncation patterns
        truncation_patterns = [
            (r'[^;}\s]\s*$', "File ends without proper termination"),
            (r'=\s*$', "File ends with incomplete assignment"),
            (r'{\s*$', "File ends with open brace"),
            (r'\(\s*$', "File ends with open parenthesis"),
            (r',\s*$', "File ends with trailing comma (possible truncation)"),
            (r'//.*$', None),  # Ends with comment - OK
        ]

        last_line = content.split('\n')[-1].strip()

        # For TSX/JSX files, check for incomplete JSX
        if ext in ['.tsx', '.jsx']:
            jsx_opens = content.count('<')
            jsx_closes = content.count('>')
            # Account for comparisons and arrows
            if jsx_opens > jsx_closes + 5:
                issues.append("Possible unclosed JSX tags")

            # Check for incomplete return statement
            if 'return' in content and 'return (' in content:
                # Count return opens and closes
                return_count = content.count('return (')
                # Check if last return is closed
                last_return_idx = content.rfind('return (')
                if last_return_idx != -1:
                    after_return = content[last_return_idx:]
                    parens_after = after_return.count('(') - after_return.count(')')
                    if parens_after > 0:
                        issues.append("Return statement may be incomplete")

        # For JSON files, check valid JSON
        if ext == '.json':
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON: {str(e)}")

        return issues

    def _check_basic_syntax(self, content: str, ext: str) -> List[str]:
        """Check basic syntax patterns"""
        issues = []

        # TypeScript/JavaScript checks
        if ext in ['.ts', '.tsx', '.js', '.jsx']:
            # Check for common issues
            if 'import ' in content and 'from' not in content and 'require' not in content:
                # Could be incomplete import
                if content.count('import ') > content.count('from '):
                    issues.append("Possible incomplete import statement")

            # Check for export statements
            if 'export ' in content:
                # Verify export has content
                export_count = content.count('export ')
                # Simple heuristic: exports should have definitions
                function_count = content.count('function ') + content.count('=>')
                const_count = content.count('const ') + content.count('let ') + content.count('var ')
                if export_count > function_count + const_count:
                    issues.append("Some exports may not have definitions")

        # CSS checks
        if ext == '.css':
            # Check for empty selectors
            if '{}' in content.replace(' ', ''):
                issues.append("Contains empty CSS selectors")

            # Check for unclosed comments
            if '/*' in content and content.count('/*') > content.count('*/'):
                issues.append("Unclosed CSS comment")

        # HTML checks
        if ext == '.html':
            # Check for basic structure
            has_doctype = '<!DOCTYPE' in content.upper() or '<!doctype' in content
            has_html = '<html' in content.lower()
            has_body = '<body' in content.lower()

            if not has_doctype:
                issues.append("Missing DOCTYPE declaration")
            if not has_html:
                issues.append("Missing <html> tag")
            if not has_body:
                issues.append("Missing <body> tag")

        return issues

    def _detect_project_type(
        self,
        files_created: List[Dict[str, Any]],
        tech_stack: Optional[Dict[str, Any]]
    ) -> str:
        """Detect project type from files and tech stack"""
        file_paths = [f.get("path", "").lower() for f in files_created]
        file_paths_str = " ".join(file_paths)

        # Mobile - Flutter
        if any('pubspec.yaml' in p for p in file_paths) or any('.dart' in p for p in file_paths):
            return 'flutter'

        # Mobile - React Native
        if any('app.tsx' in p or 'app.jsx' in p for p in file_paths) and 'react-native' in file_paths_str:
            return 'react-native'

        # Next.js
        if any('next.config' in p for p in file_paths) or any('app/layout' in p for p in file_paths):
            return 'nextjs'

        # Vue
        if any('.vue' in p for p in file_paths):
            return 'vue'

        # Angular
        if any('angular.json' in p for p in file_paths):
            return 'angular'

        # Svelte
        if any('.svelte' in p for p in file_paths) or any('svelte.config' in p for p in file_paths):
            return 'svelte'

        # React TypeScript
        if any('.tsx' in p for p in file_paths) and any('package.json' in p for p in file_paths):
            return 'react'

        # React JavaScript
        if any('.jsx' in p for p in file_paths) and any('package.json' in p for p in file_paths):
            return 'react-js'

        # NestJS
        if any('nest-cli.json' in p or 'app.module.ts' in p for p in file_paths):
            return 'nestjs'

        # Express
        if any('express' in p for p in file_paths) or ('package.json' in file_paths_str and 'app.js' in file_paths_str):
            return 'express'

        # Spring Boot
        if any('pom.xml' in p for p in file_paths) or any('application.yml' in p or 'application.properties' in p for p in file_paths):
            return 'spring-boot'

        # Java Gradle
        if any('build.gradle' in p for p in file_paths) and any('.java' in p for p in file_paths):
            return 'java-gradle'

        # Go
        if any('go.mod' in p for p in file_paths) or any('.go' in p for p in file_paths):
            return 'go'

        # Rust
        if any('cargo.toml' in p for p in file_paths) or any('.rs' in p for p in file_paths):
            return 'rust'

        # FastAPI/Django/Flask/Streamlit
        if any('requirements.txt' in p for p in file_paths) or any('.py' in p for p in file_paths):
            if any('manage.py' in p for p in file_paths):
                return 'django'
            if any('streamlit' in p or 'app.py' in p for p in file_paths):
                return 'streamlit'
            if any('model.py' in p or 'training.py' in p or '.ipynb' in p for p in file_paths):
                return 'ml-python'
            return 'fastapi'

        # Arduino/IoT
        if any('platformio.ini' in p for p in file_paths) or any('.ino' in p for p in file_paths):
            if any('esp32' in p or 'esp8266' in p for p in file_paths):
                return 'esp32'
            return 'arduino'

        # Node.js
        if any('package.json' in p for p in file_paths) and any('.js' in p for p in file_paths):
            return 'node'

        # Plain HTML
        if any('.html' in p for p in file_paths):
            return 'html'

        # Use tech stack if available
        if tech_stack:
            stack_str = str(tech_stack).lower()
            if 'flutter' in stack_str:
                return 'flutter'
            if 'react native' in stack_str:
                return 'react-native'
            if 'next' in stack_str:
                return 'nextjs'
            if 'vue' in stack_str:
                return 'vue'
            if 'angular' in stack_str:
                return 'angular'
            if 'react' in stack_str:
                return 'react' if 'typescript' in stack_str else 'react-js'
            if 'django' in stack_str:
                return 'django'
            if 'flask' in stack_str:
                return 'flask'
            if 'fastapi' in stack_str:
                return 'fastapi'
            if 'spring' in stack_str:
                return 'spring-boot'
            if 'go' in stack_str or 'golang' in stack_str:
                return 'go'
            if 'rust' in stack_str:
                return 'rust'
            if 'python' in stack_str:
                return 'python'

        return 'default'

    def _check_critical_files(
        self,
        files_created: List[Dict[str, Any]],
        project_type: str
    ) -> List[str]:
        """Check if critical files exist"""
        file_paths = [f.get("path", "").lower() for f in files_created]

        critical = self.CRITICAL_FILES.get(project_type, self.CRITICAL_FILES['default'])
        missing = []

        for critical_file in critical:
            # Check with flexible matching (case insensitive, path variations)
            found = False
            for file_path in file_paths:
                if critical_file.lower() in file_path or file_path.endswith(critical_file.lower()):
                    found = True
                    break

            if not found:
                missing.append(critical_file)

        return missing

    async def _verify_with_llm(
        self,
        plan: Dict[str, Any],
        files_created: List[Dict[str, Any]],
        basic_issues: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM for deeper verification"""

        # Build context for LLM
        files_summary = []
        for f in files_created:
            content = f.get("content", "")
            files_summary.append({
                "path": f.get("path"),
                "length": len(content),
                "lines": content.count('\n') + 1,
                "preview": content[:200] + "..." if len(content) > 200 else content
            })

        prompt = f"""Verify these generated project files against the plan.

PLAN:
{json.dumps(plan, indent=2) if isinstance(plan, dict) else str(plan)}

FILES GENERATED:
{json.dumps(files_summary, indent=2)}

KNOWN ISSUES FROM BASIC CHECK:
- Empty files: {basic_issues['empty_files']}
- Incomplete files: {basic_issues['incomplete_files']}

Analyze and provide verification results in the JSON format specified in your instructions.
Focus on:
1. Are all files from the plan generated?
2. Do the file previews look complete or truncated?
3. What critical files might be missing?
4. Which files need to be regenerated?
"""

        try:
            response = await self.claude_client.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                model=self.model,
                max_tokens=2048,
                temperature=0.3
            )

            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try parsing raw response as JSON
            return json.loads(response)

        except Exception as e:
            logger.error(f"[Verification Agent] LLM verification failed: {e}")
            return {
                "regenerate_files": basic_issues["empty_files"] + basic_issues["incomplete_files"],
                "critical_issues": [],
                "missing_files": []
            }

    def _validate_imports(self, files_created: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        PRODUCTION FIX: Validate that all local imports resolve to actual files.

        This catches "Failed to resolve import" errors BEFORE running the build.

        Args:
            files_created: List of file dictionaries with 'path' and 'content'

        Returns:
            Dictionary with 'missing_imports' list
        """
        result = {
            "missing_imports": [],
            "valid_imports": []
        }

        # Build set of existing file paths (normalized)
        existing_paths = set()
        for file_info in files_created:
            path = file_info.get("path", "")
            # Add the path as-is
            existing_paths.add(path)
            # Also add normalized versions
            existing_paths.add(path.replace("\\", "/"))
            # Add without extension for import resolution
            for ext in ['.tsx', '.ts', '.jsx', '.js']:
                if path.endswith(ext):
                    existing_paths.add(path[:-len(ext)])

        logger.info(f"[Verification Agent] Validating imports across {len(files_created)} files")
        logger.debug(f"[Verification Agent] Existing paths: {existing_paths}")

        # Import patterns for different languages
        import_patterns = {
            'typescript': [
                # import X from './path' or './path/file'
                r"import\s+(?:[\w*{},\s]+)\s+from\s+['\"](\./[^'\"]+|\.\.\/[^'\"]+)['\"]",
                # import './path'
                r"import\s+['\"](\./[^'\"]+|\.\.\/[^'\"]+)['\"]",
            ],
            'python': [
                # from .module import X
                r"from\s+(\.[.\w]+)\s+import",
                # import .module
                r"import\s+(\.[.\w]+)",
            ]
        }

        for file_info in files_created:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            if not content:
                continue

            # Determine file type
            ext = self._get_extension(file_path)
            if ext in ['.tsx', '.ts', '.jsx', '.js']:
                patterns = import_patterns['typescript']
            elif ext == '.py':
                patterns = import_patterns['python']
            else:
                continue  # Skip non-source files

            # Get directory of current file for relative path resolution
            file_dir = '/'.join(file_path.split('/')[:-1]) if '/' in file_path else ''

            for pattern in patterns:
                matches = re.findall(pattern, content)
                for import_path in matches:
                    # Skip package imports (react, axios, etc.)
                    if not import_path.startswith('.'):
                        continue

                    # Resolve relative path
                    if import_path.startswith('./'):
                        resolved = file_dir + '/' + import_path[2:] if file_dir else import_path[2:]
                    elif import_path.startswith('../'):
                        # Handle parent directory imports
                        parts = file_dir.split('/')
                        import_parts = import_path.split('/')
                        up_count = 0
                        for p in import_parts:
                            if p == '..':
                                up_count += 1
                            else:
                                break
                        remaining = import_parts[up_count:]
                        parent_parts = parts[:-up_count] if up_count <= len(parts) else []
                        resolved = '/'.join(parent_parts + remaining)
                    else:
                        resolved = import_path

                    # Normalize path
                    resolved = re.sub(r'/+', '/', resolved).strip('/')

                    # Check if import target exists (try various extensions)
                    found = False
                    possible_paths = [resolved]

                    # Add possible extensions if not already present
                    if not any(resolved.endswith(e) for e in ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.py']):
                        for try_ext in ['.tsx', '.ts', '.jsx', '.js', '/index.tsx', '/index.ts', '/index.jsx', '/index.js']:
                            possible_paths.append(resolved + try_ext)

                    for try_path in possible_paths:
                        if try_path in existing_paths:
                            found = True
                            result["valid_imports"].append({
                                "source_file": file_path,
                                "import_path": import_path,
                                "resolved_to": try_path
                            })
                            break

                    if not found:
                        # Suggest the most likely path
                        suggested = resolved + '.tsx' if ext in ['.tsx', '.ts'] else resolved + '.js'

                        result["missing_imports"].append({
                            "source_file": file_path,
                            "import_path": import_path,
                            "resolved_path": resolved,
                            "suggested_path": suggested,
                            "tried_paths": possible_paths[:3]  # First 3 attempts
                        })

                        logger.warning(f"[Verification Agent] Missing import: {file_path} -> {import_path} (resolved: {resolved})")

        logger.info(f"[Verification Agent] Import validation complete: {len(result['valid_imports'])} valid, {len(result['missing_imports'])} missing")

        return result

    def _get_extension(self, file_path: str) -> str:
        """Get file extension"""
        if '.' in file_path:
            return '.' + file_path.split('.')[-1].lower()
        return ''

    async def generate_missing_files_prompt(
        self,
        missing_files: List[str],
        plan: Dict[str, Any],
        existing_files: List[Dict[str, Any]]
    ) -> str:
        """Generate a prompt for the Writer Agent to create missing files"""

        existing_paths = [f.get("path") for f in existing_files]

        prompt = f"""CRITICAL: The following files are MISSING and need to be generated:

MISSING FILES:
{chr(10).join(f'- {f}' for f in missing_files)}

EXISTING FILES (for context):
{chr(10).join(f'- {f}' for f in existing_paths)}

ORIGINAL PLAN:
{plan.get('raw', 'No plan available') if isinstance(plan, dict) else str(plan)}

Generate ONLY the missing files listed above.
Use <file path="...">CONTENT</file> tags.
Ensure each file is COMPLETE with all necessary code.
"""
        return prompt

    async def generate_regenerate_prompt(
        self,
        files_to_regenerate: List[str],
        plan: Dict[str, Any],
        existing_files: List[Dict[str, Any]],
        issues: Dict[str, Any]
    ) -> str:
        """Generate a prompt for the Writer Agent to regenerate incomplete files"""

        # Get the original content of files to regenerate for context
        file_contexts = []
        for file_path in files_to_regenerate:
            for f in existing_files:
                if f.get("path") == file_path:
                    content = f.get("content", "")
                    file_contexts.append({
                        "path": file_path,
                        "original_content": content[:500] if len(content) > 500 else content,
                        "issues": next(
                            (d.get("issues", []) for d in issues.get("file_details", []) if d.get("path") == file_path),
                            []
                        )
                    })
                    break

        prompt = f"""CRITICAL: The following files are INCOMPLETE and need to be REGENERATED with COMPLETE code:

FILES TO REGENERATE:
{json.dumps(file_contexts, indent=2)}

ORIGINAL PLAN:
{plan.get('raw', 'No plan available') if isinstance(plan, dict) else str(plan)}

REQUIREMENTS:
1. Generate COMPLETE files - no truncation
2. Include ALL necessary imports
3. Include ALL function implementations
4. Include ALL closing braces and tags
5. Test your code mentally before outputting

Use <file path="...">COMPLETE_CONTENT</file> tags.
Generate ONLY the files listed above, with FULL implementations.
"""
        return prompt

    def quick_validate_bolt_instant(
        self,
        files_created: List[Dict[str, Any]],
        tech_stack: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        FAST validation for bolt_instant mode - no LLM calls.

        Checks critical files and imports synchronously.
        Used AFTER bolt_instant generation to catch common issues.

        Args:
            files_created: List of files created by bolt_instant
            tech_stack: Detected tech stack

        Returns:
            Dict with status, missing_files, issues
        """
        logger.info(f"[Verification] Quick validating {len(files_created)} files...")

        result = {
            "status": "pass",
            "missing_files": [],
            "empty_files": [],
            "incomplete_files": [],
            "import_issues": [],
            "needs_regeneration": False
        }

        # 1. Check for critical files
        project_type = self._detect_project_type(files_created, tech_stack)
        missing = self._check_critical_files(files_created, project_type)

        if missing:
            result["missing_files"] = missing
            result["status"] = "fail"
            result["needs_regeneration"] = True
            logger.warning(f"[Verification] Missing critical files: {missing}")

        # 2. Basic file verification
        basic = self._verify_files_basic(files_created)
        result["empty_files"] = basic["empty_files"]
        result["incomplete_files"] = basic["incomplete_files"]

        if basic["empty_files"]:
            result["status"] = "fail"
            result["needs_regeneration"] = True
            logger.warning(f"[Verification] Empty files: {basic['empty_files']}")

        if basic["incomplete_files"]:
            if result["status"] == "pass":
                result["status"] = "partial"
            logger.warning(f"[Verification] Incomplete files: {basic['incomplete_files']}")

        # 3. Import validation
        import_issues = self._validate_imports(files_created)
        if import_issues["missing_imports"]:
            result["import_issues"] = import_issues["missing_imports"]
            result["status"] = "fail"
            result["needs_regeneration"] = True
            for mi in import_issues["missing_imports"]:
                if mi["suggested_path"] not in result["missing_files"]:
                    result["missing_files"].append(mi["suggested_path"])

        # 4. Package.json consistency check
        pkg_issues = self.validate_package_consistency(files_created)
        if pkg_issues["missing_deps"]:
            result["package_issues"] = pkg_issues["missing_deps"]
            # This is a warning, not a regeneration trigger
            logger.warning(f"[Verification] Package.json missing deps: {pkg_issues['missing_deps']}")

        # 5. Build regeneration list
        result["files_to_regenerate"] = list(set(
            result["empty_files"] +
            result["incomplete_files"] +
            result["missing_files"]
        ))

        logger.info(f"[Verification] Quick validation: {result['status']} - {len(result['files_to_regenerate'])} files need work")

        return result

    def validate_package_consistency(
        self,
        files_created: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate that package.json dependencies match config files.

        Catches issues like:
        - tailwind.config.js using @tailwindcss/forms but not in package.json
        - vite.config.ts using plugins not installed

        Args:
            files_created: List of files with path and content

        Returns:
            Dict with missing_deps list
        """
        result = {
            "missing_deps": [],
            "warnings": []
        }

        # Find package.json
        package_json = None
        tailwind_config = None
        vite_config = None

        for file_info in files_created:
            path = file_info.get("path", "").lower()
            content = file_info.get("content", "")

            if path.endswith("package.json"):
                try:
                    package_json = json.loads(content)
                except:
                    pass
            elif "tailwind.config" in path:
                tailwind_config = content
            elif "vite.config" in path:
                vite_config = content

        if not package_json:
            return result

        # Get all dependencies
        all_deps = set()
        for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
            all_deps.update(package_json.get(dep_type, {}).keys())

        # Check tailwind plugins
        if tailwind_config:
            # Extract plugins from tailwind config
            plugin_patterns = [
                r"require\(['\"](@tailwindcss/[^'\"]+)['\"]",
                r"require\(['\"](@headlessui/[^'\"]+)['\"]",
                r"import\s+\w+\s+from\s+['\"](@tailwindcss/[^'\"]+)['\"]",
            ]

            for pattern in plugin_patterns:
                matches = re.findall(pattern, tailwind_config)
                for plugin in matches:
                    if plugin not in all_deps:
                        result["missing_deps"].append({
                            "package": plugin,
                            "required_by": "tailwind.config.js",
                            "add_to": "devDependencies"
                        })

        # Check vite plugins
        if vite_config:
            plugin_patterns = [
                r"import\s+\w+\s+from\s+['\"](@vitejs/[^'\"]+)['\"]",
                r"import\s+\w+\s+from\s+['\"]vite-plugin-[^'\"]+['\"]",
            ]

            for pattern in plugin_patterns:
                matches = re.findall(pattern, vite_config)
                for plugin in matches:
                    if plugin not in all_deps:
                        result["missing_deps"].append({
                            "package": plugin,
                            "required_by": "vite.config.ts",
                            "add_to": "devDependencies"
                        })

        if result["missing_deps"]:
            logger.warning(f"[Verification] Package consistency issues: {result['missing_deps']}")

        return result


# Create instance on demand in dynamic_orchestrator.py
# verification_agent = VerificationAgent()
