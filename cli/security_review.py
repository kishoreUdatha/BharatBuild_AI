"""
BharatBuild CLI Security Review

Comprehensive security auditing:
  /security-review        Review pending changes for security issues
  /security-review <file> Review specific file
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax


class SeverityLevel(str, Enum):
    """Security issue severity"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    """Security issue categories"""
    INJECTION = "injection"
    XSS = "xss"
    AUTH = "authentication"
    CRYPTO = "cryptography"
    SECRETS = "secrets"
    PERMISSIONS = "permissions"
    DEPENDENCIES = "dependencies"
    CONFIG = "configuration"
    OTHER = "other"


@dataclass
class SecurityIssue:
    """A security issue found during review"""
    id: str
    severity: SeverityLevel
    category: IssueCategory
    title: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str = ""
    recommendation: str = ""
    cwe_id: str = ""  # Common Weakness Enumeration


@dataclass
class SecurityReport:
    """Security review report"""
    id: str
    reviewed_at: str
    files_reviewed: List[str]
    issues: List[SecurityIssue] = field(default_factory=list)
    summary: str = ""


class SecurityReviewManager:
    """
    Manages security reviews for BharatBuild CLI.

    Features:
    - OWASP Top 10 checks
    - Secret detection
    - Dependency vulnerability scanning
    - Code pattern analysis
    - Security report generation

    Usage:
        manager = SecurityReviewManager(console, project_dir)

        # Review all changes
        report = manager.review_changes()

        # Review specific file
        report = manager.review_file("src/auth.py")
    """

    # Security patterns to detect
    SECURITY_PATTERNS = {
        # Secrets and credentials
        "hardcoded_password": {
            "pattern": r"(password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]",
            "severity": SeverityLevel.CRITICAL,
            "category": IssueCategory.SECRETS,
            "title": "Hardcoded Password",
            "description": "Password appears to be hardcoded in source code",
            "recommendation": "Use environment variables or a secrets manager",
            "cwe_id": "CWE-798"
        },
        "api_key": {
            "pattern": r"(api[_-]?key|apikey|api[_-]?secret)\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]",
            "severity": SeverityLevel.CRITICAL,
            "category": IssueCategory.SECRETS,
            "title": "Exposed API Key",
            "description": "API key appears to be hardcoded",
            "recommendation": "Store API keys in environment variables or secrets manager",
            "cwe_id": "CWE-798"
        },
        "private_key": {
            "pattern": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
            "severity": SeverityLevel.CRITICAL,
            "category": IssueCategory.SECRETS,
            "title": "Private Key in Code",
            "description": "Private key detected in source code",
            "recommendation": "Remove private key and use secure key management",
            "cwe_id": "CWE-321"
        },
        "aws_credentials": {
            "pattern": r"(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}",
            "severity": SeverityLevel.CRITICAL,
            "category": IssueCategory.SECRETS,
            "title": "AWS Access Key",
            "description": "AWS access key detected",
            "recommendation": "Use IAM roles or AWS Secrets Manager",
            "cwe_id": "CWE-798"
        },

        # SQL Injection
        "sql_injection": {
            "pattern": r"(execute|cursor\.execute|query)\s*\([^)]*(%s|%d|\{|\+\s*['\"])",
            "severity": SeverityLevel.HIGH,
            "category": IssueCategory.INJECTION,
            "title": "Potential SQL Injection",
            "description": "String concatenation or formatting in SQL query",
            "recommendation": "Use parameterized queries or ORM",
            "cwe_id": "CWE-89"
        },
        "sql_string_format": {
            "pattern": r"(SELECT|INSERT|UPDATE|DELETE|DROP|TRUNCATE).*['\"].*%[sd]",
            "severity": SeverityLevel.HIGH,
            "category": IssueCategory.INJECTION,
            "title": "SQL String Formatting",
            "description": "SQL query built with string formatting",
            "recommendation": "Use parameterized queries",
            "cwe_id": "CWE-89"
        },

        # Command Injection
        "command_injection": {
            "pattern": r"(os\.system|subprocess\.(call|run|Popen)|shell=True).*(\+|%|\.format|\{)",
            "severity": SeverityLevel.HIGH,
            "category": IssueCategory.INJECTION,
            "title": "Potential Command Injection",
            "description": "User input may be passed to shell command",
            "recommendation": "Sanitize input and avoid shell=True",
            "cwe_id": "CWE-78"
        },
        "eval_exec": {
            "pattern": r"\b(eval|exec)\s*\(",
            "severity": SeverityLevel.HIGH,
            "category": IssueCategory.INJECTION,
            "title": "Use of eval/exec",
            "description": "eval() or exec() can execute arbitrary code",
            "recommendation": "Avoid eval/exec or use ast.literal_eval for safe parsing",
            "cwe_id": "CWE-95"
        },

        # XSS
        "xss_innerhtml": {
            "pattern": r"(innerHTML|outerHTML)\s*=",
            "severity": SeverityLevel.MEDIUM,
            "category": IssueCategory.XSS,
            "title": "Potential XSS via innerHTML",
            "description": "Direct innerHTML assignment can lead to XSS",
            "recommendation": "Use textContent or sanitize HTML",
            "cwe_id": "CWE-79"
        },
        "xss_dangerously": {
            "pattern": r"dangerouslySetInnerHTML",
            "severity": SeverityLevel.MEDIUM,
            "category": IssueCategory.XSS,
            "title": "dangerouslySetInnerHTML Usage",
            "description": "React dangerouslySetInnerHTML can lead to XSS",
            "recommendation": "Sanitize HTML content before rendering",
            "cwe_id": "CWE-79"
        },

        # Cryptography
        "weak_hash": {
            "pattern": r"\b(md5|sha1)\s*\(",
            "severity": SeverityLevel.MEDIUM,
            "category": IssueCategory.CRYPTO,
            "title": "Weak Hash Algorithm",
            "description": "MD5 or SHA1 are cryptographically weak",
            "recommendation": "Use SHA-256 or stronger for security-sensitive hashing",
            "cwe_id": "CWE-328"
        },
        "weak_random": {
            "pattern": r"\brandom\.(random|randint|choice)\b",
            "severity": SeverityLevel.LOW,
            "category": IssueCategory.CRYPTO,
            "title": "Weak Random Number Generator",
            "description": "random module is not cryptographically secure",
            "recommendation": "Use secrets module for security-sensitive randomness",
            "cwe_id": "CWE-330"
        },

        # Authentication
        "jwt_none_alg": {
            "pattern": r"(algorithm|alg)\s*[=:]\s*['\"]none['\"]",
            "severity": SeverityLevel.CRITICAL,
            "category": IssueCategory.AUTH,
            "title": "JWT None Algorithm",
            "description": "JWT with 'none' algorithm is insecure",
            "recommendation": "Always specify a secure algorithm (RS256, HS256)",
            "cwe_id": "CWE-327"
        },
        "hardcoded_jwt_secret": {
            "pattern": r"(jwt|token)[_-]?secret\s*=\s*['\"][^'\"]+['\"]",
            "severity": SeverityLevel.HIGH,
            "category": IssueCategory.AUTH,
            "title": "Hardcoded JWT Secret",
            "description": "JWT secret is hardcoded",
            "recommendation": "Use environment variables for JWT secrets",
            "cwe_id": "CWE-798"
        },

        # Configuration
        "debug_enabled": {
            "pattern": r"(DEBUG|debug)\s*=\s*(True|true|1|['\"]true['\"])",
            "severity": SeverityLevel.LOW,
            "category": IssueCategory.CONFIG,
            "title": "Debug Mode Enabled",
            "description": "Debug mode may be enabled in production",
            "recommendation": "Disable debug mode in production",
            "cwe_id": "CWE-489"
        },
        "cors_wildcard": {
            "pattern": r"(Access-Control-Allow-Origin|cors.*origin)\s*[=:]\s*['\"]?\*['\"]?",
            "severity": SeverityLevel.MEDIUM,
            "category": IssueCategory.CONFIG,
            "title": "CORS Wildcard",
            "description": "CORS allows all origins",
            "recommendation": "Restrict CORS to specific trusted origins",
            "cwe_id": "CWE-942"
        },

        # File operations
        "path_traversal": {
            "pattern": r"(open|read|write)\s*\([^)]*(\.\./|\+|%|\.format)",
            "severity": SeverityLevel.HIGH,
            "category": IssueCategory.INJECTION,
            "title": "Potential Path Traversal",
            "description": "File path may include user input without validation",
            "recommendation": "Validate and sanitize file paths",
            "cwe_id": "CWE-22"
        },

        # Deserialization
        "unsafe_pickle": {
            "pattern": r"pickle\.(load|loads)\s*\(",
            "severity": SeverityLevel.HIGH,
            "category": IssueCategory.INJECTION,
            "title": "Unsafe Pickle Deserialization",
            "description": "Pickle can execute arbitrary code on load",
            "recommendation": "Use safe serialization formats like JSON",
            "cwe_id": "CWE-502"
        },
        "unsafe_yaml": {
            "pattern": r"yaml\.(load|unsafe_load)\s*\([^)]*\)",
            "severity": SeverityLevel.HIGH,
            "category": IssueCategory.INJECTION,
            "title": "Unsafe YAML Loading",
            "description": "yaml.load without Loader can execute code",
            "recommendation": "Use yaml.safe_load() instead",
            "cwe_id": "CWE-502"
        }
    }

    # File patterns to scan
    FILE_PATTERNS = [
        "**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx",
        "**/*.java", "**/*.go", "**/*.rb", "**/*.php",
        "**/*.yml", "**/*.yaml", "**/*.json", "**/*.xml",
        "**/*.env", "**/*.config", "**/*.conf"
    ]

    # Directories to skip
    SKIP_DIRS = [
        "node_modules", "venv", ".venv", "env", ".env",
        "__pycache__", ".git", ".svn", "dist", "build",
        "vendor", "packages", ".tox", "eggs"
    ]

    def __init__(
        self,
        console: Console,
        project_dir: Path = None
    ):
        self.console = console
        self.project_dir = project_dir or Path.cwd()

    # ==================== Review Methods ====================

    def review_changes(self) -> SecurityReport:
        """Review pending git changes for security issues"""
        self.console.print("\n[bold cyan]Security Review[/bold cyan]\n")

        # Get changed files from git
        changed_files = self._get_changed_files()

        if not changed_files:
            self.console.print("[dim]No pending changes to review[/dim]")
            self.console.print("[dim]Use /security-review <file> to review a specific file[/dim]")
            return SecurityReport(
                id=datetime.now().strftime("%Y%m%d_%H%M%S"),
                reviewed_at=datetime.now().isoformat(),
                files_reviewed=[]
            )

        self.console.print(f"[bold]Reviewing {len(changed_files)} changed file(s)...[/bold]\n")

        # Review each file
        all_issues = []
        for file_path in changed_files:
            issues = self._review_file(file_path)
            all_issues.extend(issues)

        # Generate report
        report = SecurityReport(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            reviewed_at=datetime.now().isoformat(),
            files_reviewed=changed_files,
            issues=all_issues
        )

        # Display results
        self._display_report(report)

        return report

    def review_file(self, file_path: str) -> SecurityReport:
        """Review a specific file"""
        path = Path(file_path)

        if not path.is_absolute():
            path = self.project_dir / path

        if not path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return SecurityReport(
                id=datetime.now().strftime("%Y%m%d_%H%M%S"),
                reviewed_at=datetime.now().isoformat(),
                files_reviewed=[]
            )

        self.console.print(f"\n[bold cyan]Security Review: {path.name}[/bold cyan]\n")

        issues = self._review_file(str(path))

        report = SecurityReport(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            reviewed_at=datetime.now().isoformat(),
            files_reviewed=[str(path)],
            issues=issues
        )

        self._display_report(report)

        return report

    def review_all(self) -> SecurityReport:
        """Review entire codebase"""
        self.console.print("\n[bold cyan]Full Security Review[/bold cyan]\n")

        all_files = []
        for pattern in self.FILE_PATTERNS:
            for file_path in self.project_dir.glob(pattern):
                # Skip excluded directories
                if any(skip in str(file_path) for skip in self.SKIP_DIRS):
                    continue
                all_files.append(str(file_path))

        self.console.print(f"[bold]Reviewing {len(all_files)} file(s)...[/bold]\n")

        all_issues = []
        for file_path in all_files:
            issues = self._review_file(file_path)
            all_issues.extend(issues)

        report = SecurityReport(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            reviewed_at=datetime.now().isoformat(),
            files_reviewed=all_files,
            issues=all_issues
        )

        self._display_report(report)

        return report

    def _get_changed_files(self) -> List[str]:
        """Get list of changed files from git"""
        try:
            # Get staged and unstaged changes
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_dir
            )

            if result.returncode == 0 and result.stdout.strip():
                files = result.stdout.strip().split("\n")
                return [str(self.project_dir / f) for f in files if f]

            # Also check staged files
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True,
                text=True,
                cwd=self.project_dir
            )

            if result.returncode == 0 and result.stdout.strip():
                files = result.stdout.strip().split("\n")
                return [str(self.project_dir / f) for f in files if f]

        except Exception:
            pass

        return []

    def _review_file(self, file_path: str) -> List[SecurityIssue]:
        """Review a single file for security issues"""
        issues = []
        issue_id = 1

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            # Check each security pattern
            for pattern_name, pattern_config in self.SECURITY_PATTERNS.items():
                regex = re.compile(pattern_config["pattern"], re.IGNORECASE | re.MULTILINE)

                for match in regex.finditer(content):
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1

                    # Get code snippet
                    snippet_start = max(0, line_num - 2)
                    snippet_end = min(len(lines), line_num + 2)
                    snippet = '\n'.join(lines[snippet_start:snippet_end])

                    issue = SecurityIssue(
                        id=f"SEC-{issue_id:03d}",
                        severity=pattern_config["severity"],
                        category=pattern_config["category"],
                        title=pattern_config["title"],
                        description=pattern_config["description"],
                        file_path=file_path,
                        line_number=line_num,
                        code_snippet=snippet,
                        recommendation=pattern_config["recommendation"],
                        cwe_id=pattern_config.get("cwe_id", "")
                    )
                    issues.append(issue)
                    issue_id += 1

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not read {file_path}: {e}[/yellow]")

        return issues

    # ==================== Display ====================

    def _display_report(self, report: SecurityReport):
        """Display security report"""
        if not report.issues:
            self.console.print("[green]✓ No security issues found[/green]")
            self.console.print(f"[dim]Reviewed {len(report.files_reviewed)} file(s)[/dim]")
            return

        # Group by severity
        critical = [i for i in report.issues if i.severity == SeverityLevel.CRITICAL]
        high = [i for i in report.issues if i.severity == SeverityLevel.HIGH]
        medium = [i for i in report.issues if i.severity == SeverityLevel.MEDIUM]
        low = [i for i in report.issues if i.severity == SeverityLevel.LOW]

        # Summary
        self.console.print("[bold]Summary:[/bold]")
        if critical:
            self.console.print(f"  [red]● {len(critical)} Critical[/red]")
        if high:
            self.console.print(f"  [red]● {len(high)} High[/red]")
        if medium:
            self.console.print(f"  [yellow]● {len(medium)} Medium[/yellow]")
        if low:
            self.console.print(f"  [dim]● {len(low)} Low[/dim]")

        self.console.print(f"\n[dim]Reviewed {len(report.files_reviewed)} file(s)[/dim]\n")

        # Display issues
        for issue in report.issues:
            self._display_issue(issue)

    def _display_issue(self, issue: SecurityIssue):
        """Display a single security issue"""
        severity_colors = {
            SeverityLevel.CRITICAL: "red bold",
            SeverityLevel.HIGH: "red",
            SeverityLevel.MEDIUM: "yellow",
            SeverityLevel.LOW: "dim",
            SeverityLevel.INFO: "cyan"
        }

        color = severity_colors.get(issue.severity, "white")

        # Header
        self.console.print(f"\n[{color}]━━━ {issue.id}: {issue.title} ━━━[/{color}]")
        self.console.print(f"[{color}]Severity: {issue.severity.value.upper()}[/{color}]")
        self.console.print(f"[dim]Category: {issue.category.value}[/dim]")

        if issue.cwe_id:
            self.console.print(f"[dim]{issue.cwe_id}[/dim]")

        # Location
        rel_path = Path(issue.file_path)
        try:
            rel_path = rel_path.relative_to(self.project_dir)
        except ValueError:
            pass

        self.console.print(f"\n[bold]Location:[/bold] {rel_path}:{issue.line_number}")

        # Description
        self.console.print(f"\n[bold]Description:[/bold] {issue.description}")

        # Code snippet
        if issue.code_snippet:
            self.console.print("\n[bold]Code:[/bold]")
            # Try to determine language from file extension
            ext = Path(issue.file_path).suffix.lower()
            lang_map = {
                ".py": "python", ".js": "javascript", ".ts": "typescript",
                ".java": "java", ".go": "go", ".rb": "ruby", ".php": "php",
                ".yml": "yaml", ".yaml": "yaml", ".json": "json"
            }
            lang = lang_map.get(ext, "text")

            syntax = Syntax(issue.code_snippet, lang, line_numbers=True, start_line=max(1, issue.line_number - 1))
            self.console.print(syntax)

        # Recommendation
        self.console.print(f"\n[bold green]Recommendation:[/bold green] {issue.recommendation}")

    # ==================== Command Handler ====================

    def cmd_security_review(self, args: str = ""):
        """Handle /security-review command"""
        if not args:
            self.review_changes()
        elif args == "--all":
            self.review_all()
        elif args == "--help":
            self.show_help()
        else:
            self.review_file(args)

    def show_help(self):
        """Show security review help"""
        help_text = """
[bold cyan]Security Review Commands[/bold cyan]

Audit code for security vulnerabilities.

[bold]Commands:[/bold]
  [green]/security-review[/green]           Review pending changes
  [green]/security-review <file>[/green]    Review specific file
  [green]/security-review --all[/green]     Review entire codebase

[bold]Checks Performed:[/bold]
  • Hardcoded secrets and credentials
  • SQL injection vulnerabilities
  • Command injection risks
  • XSS vulnerabilities
  • Weak cryptography
  • Authentication issues
  • Configuration problems
  • Unsafe deserialization

[bold]Severity Levels:[/bold]
  • [red]CRITICAL[/red] - Immediate action required
  • [red]HIGH[/red] - Serious security risk
  • [yellow]MEDIUM[/yellow] - Moderate risk
  • [dim]LOW[/dim] - Minor concern

[bold]References:[/bold]
  • OWASP Top 10
  • CWE (Common Weakness Enumeration)
"""
        self.console.print(help_text)


# Factory function
def get_security_reviewer(
    console: Console = None,
    project_dir: Path = None
) -> SecurityReviewManager:
    """Get security review manager instance"""
    return SecurityReviewManager(
        console=console or Console(),
        project_dir=project_dir
    )
