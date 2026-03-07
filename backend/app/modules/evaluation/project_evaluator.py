"""
Automated Project Evaluation System
Evaluates code quality, architecture, and provides rubric-based grading
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class EvaluationCriteria(str, Enum):
    CODE_QUALITY = "code_quality"
    ARCHITECTURE = "architecture"
    FUNCTIONALITY = "functionality"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    SECURITY = "security"
    PERFORMANCE = "performance"
    UI_UX = "ui_ux"
    BEST_PRACTICES = "best_practices"
    INNOVATION = "innovation"


class GradeLevel(str, Enum):
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 70-89%
    SATISFACTORY = "satisfactory"  # 50-69%
    NEEDS_IMPROVEMENT = "needs_improvement"  # Below 50%


@dataclass
class RubricCriterion:
    """Single rubric criterion with levels"""
    name: str
    description: str
    max_points: int
    levels: Dict[str, str]  # Level name -> description
    co_mapped: List[str] = field(default_factory=list)
    po_mapped: List[str] = field(default_factory=list)


@dataclass
class EvaluationRubric:
    """Complete evaluation rubric"""
    name: str
    total_points: int
    criteria: List[RubricCriterion]
    passing_percentage: float = 50.0


@dataclass
class EvaluationResult:
    """Result of project evaluation"""
    project_id: str
    total_score: float
    max_score: float
    percentage: float
    grade: GradeLevel
    criteria_scores: Dict[str, Dict[str, Any]]
    strengths: List[str]
    improvements: List[str]
    co_attainment: Dict[str, float]
    po_attainment: Dict[str, float]
    detailed_feedback: str
    evaluated_at: str


class ProjectEvaluator:
    """
    Automated project evaluation system.
    Analyzes code quality, architecture, and provides rubric-based grading.
    """

    def __init__(self):
        self.default_rubric = self._create_default_rubric()

    def _create_default_rubric(self) -> EvaluationRubric:
        """Create default evaluation rubric for software projects."""
        criteria = [
            RubricCriterion(
                name="Code Quality",
                description="Code readability, organization, naming conventions, comments",
                max_points=20,
                levels={
                    "Excellent (18-20)": "Code is exceptionally clean, well-organized, follows best practices consistently, meaningful names, appropriate comments",
                    "Good (14-17)": "Code is clean and readable, follows most best practices, good naming, some comments",
                    "Satisfactory (10-13)": "Code is functional but could be cleaner, inconsistent style, minimal comments",
                    "Needs Improvement (0-9)": "Code is hard to read, poor organization, unclear naming, no comments"
                },
                co_mapped=["CO1", "CO2"],
                po_mapped=["PO1", "PO5"]
            ),
            RubricCriterion(
                name="Architecture & Design",
                description="System design, modularity, separation of concerns, patterns used",
                max_points=20,
                levels={
                    "Excellent (18-20)": "Excellent architecture with clear separation, appropriate patterns, highly modular and scalable",
                    "Good (14-17)": "Good architecture with reasonable separation, some patterns used, modular design",
                    "Satisfactory (10-13)": "Basic architecture, some modularity, could benefit from better patterns",
                    "Needs Improvement (0-9)": "Poor architecture, monolithic, no clear separation of concerns"
                },
                co_mapped=["CO2", "CO3"],
                po_mapped=["PO2", "PO3"]
            ),
            RubricCriterion(
                name="Functionality",
                description="Features implemented, requirements met, error handling",
                max_points=25,
                levels={
                    "Excellent (22-25)": "All features fully implemented, exceeds requirements, robust error handling",
                    "Good (17-21)": "Most features implemented correctly, meets requirements, good error handling",
                    "Satisfactory (12-16)": "Core features work, some requirements met, basic error handling",
                    "Needs Improvement (0-11)": "Many features missing or broken, requirements not met, poor error handling"
                },
                co_mapped=["CO1", "CO2", "CO3"],
                po_mapped=["PO1", "PO2", "PO3"]
            ),
            RubricCriterion(
                name="Documentation",
                description="README, API docs, code comments, user guide",
                max_points=10,
                levels={
                    "Excellent (9-10)": "Comprehensive documentation, clear README, API docs, setup instructions",
                    "Good (7-8)": "Good documentation, clear README, some API docs",
                    "Satisfactory (5-6)": "Basic README, minimal documentation",
                    "Needs Improvement (0-4)": "Little or no documentation"
                },
                co_mapped=["CO4"],
                po_mapped=["PO10"]
            ),
            RubricCriterion(
                name="Testing",
                description="Test coverage, test quality, testing practices",
                max_points=10,
                levels={
                    "Excellent (9-10)": "Comprehensive test coverage (>80%), unit + integration tests, CI/CD",
                    "Good (7-8)": "Good test coverage (60-80%), unit tests, some integration tests",
                    "Satisfactory (5-6)": "Some tests (40-60% coverage), basic unit tests",
                    "Needs Improvement (0-4)": "Minimal or no tests (<40% coverage)"
                },
                co_mapped=["CO3", "CO4"],
                po_mapped=["PO4", "PO5"]
            ),
            RubricCriterion(
                name="Security",
                description="Security practices, input validation, authentication, data protection",
                max_points=10,
                levels={
                    "Excellent (9-10)": "Excellent security practices, proper auth, input validation, secure data handling",
                    "Good (7-8)": "Good security practices, authentication implemented, basic validation",
                    "Satisfactory (5-6)": "Some security measures, basic authentication",
                    "Needs Improvement (0-4)": "Security vulnerabilities, no authentication, poor validation"
                },
                co_mapped=["CO2", "CO3"],
                po_mapped=["PO6", "PO8"]
            ),
            RubricCriterion(
                name="UI/UX Design",
                description="User interface design, user experience, responsiveness, accessibility",
                max_points=10,
                levels={
                    "Excellent (9-10)": "Excellent UI/UX, intuitive, responsive, accessible, consistent design",
                    "Good (7-8)": "Good UI/UX, user-friendly, responsive design",
                    "Satisfactory (5-6)": "Functional UI, basic responsiveness",
                    "Needs Improvement (0-4)": "Poor UI/UX, not responsive, hard to use"
                },
                co_mapped=["CO2"],
                po_mapped=["PO3", "PO6"]
            ),
            RubricCriterion(
                name="Innovation & Creativity",
                description="Novel approaches, creative solutions, going beyond requirements",
                max_points=5,
                levels={
                    "Excellent (5)": "Highly innovative, creative solutions, exceeds expectations",
                    "Good (4)": "Some innovation, creative problem-solving",
                    "Satisfactory (2-3)": "Standard implementation, minimal creativity",
                    "Needs Improvement (0-1)": "No innovation, basic copy-paste approach"
                },
                co_mapped=["CO3", "CO4"],
                po_mapped=["PO4", "PO12"]
            )
        ]

        total_points = sum(c.max_points for c in criteria)

        return EvaluationRubric(
            name="Software Project Evaluation Rubric",
            total_points=total_points,
            criteria=criteria,
            passing_percentage=50.0
        )

    def evaluate_project(
        self,
        project_id: str,
        files: Dict[str, str],
        rubric: Optional[EvaluationRubric] = None,
        additional_context: Optional[str] = None
    ) -> EvaluationResult:
        """
        Evaluate a project based on its files and rubric.

        Args:
            project_id: Project identifier
            files: Dictionary of {filename: content}
            rubric: Evaluation rubric (uses default if not provided)
            additional_context: Additional context about the project

        Returns:
            EvaluationResult with scores and feedback
        """
        rubric = rubric or self.default_rubric

        # Analyze code
        code_analysis = self._analyze_code(files)

        # Score each criterion
        criteria_scores = {}
        total_score = 0

        for criterion in rubric.criteria:
            score, feedback = self._score_criterion(criterion, code_analysis, files)
            criteria_scores[criterion.name] = {
                "score": score,
                "max_score": criterion.max_points,
                "percentage": (score / criterion.max_points) * 100,
                "feedback": feedback,
                "co_mapped": criterion.co_mapped,
                "po_mapped": criterion.po_mapped
            }
            total_score += score

        # Calculate overall
        percentage = (total_score / rubric.total_points) * 100
        grade = self._determine_grade(percentage)

        # Calculate CO and PO attainment
        co_attainment = self._calculate_co_attainment(criteria_scores)
        po_attainment = self._calculate_po_attainment(criteria_scores)

        # Generate feedback
        strengths, improvements = self._generate_feedback(criteria_scores)
        detailed_feedback = self._generate_detailed_feedback(
            criteria_scores, code_analysis, grade
        )

        return EvaluationResult(
            project_id=project_id,
            total_score=total_score,
            max_score=rubric.total_points,
            percentage=percentage,
            grade=grade,
            criteria_scores=criteria_scores,
            strengths=strengths,
            improvements=improvements,
            co_attainment=co_attainment,
            po_attainment=po_attainment,
            detailed_feedback=detailed_feedback,
            evaluated_at=datetime.now().isoformat()
        )

    def _analyze_code(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Analyze code files and extract metrics."""
        analysis = {
            "total_files": len(files),
            "total_lines": 0,
            "languages": {},
            "has_readme": False,
            "has_tests": False,
            "has_docs": False,
            "has_config": False,
            "has_dockerfile": False,
            "has_ci_cd": False,
            "code_patterns": {
                "comments_ratio": 0,
                "function_count": 0,
                "class_count": 0,
                "import_count": 0
            },
            "security_checks": {
                "has_env_file": False,
                "hardcoded_secrets": False,
                "input_validation": False
            },
            "file_structure": {
                "has_src_folder": False,
                "has_components": False,
                "has_services": False,
                "has_utils": False
            }
        }

        comment_lines = 0
        code_lines = 0

        for filename, content in files.items():
            lines = len(content.split('\n'))
            analysis["total_lines"] += lines

            # Detect language
            ext = filename.split('.')[-1].lower() if '.' in filename else ''
            if ext:
                analysis["languages"][ext] = analysis["languages"].get(ext, 0) + 1

            # Check for special files
            filename_lower = filename.lower()
            if 'readme' in filename_lower:
                analysis["has_readme"] = True
            if 'test' in filename_lower or 'spec' in filename_lower:
                analysis["has_tests"] = True
            if 'docs' in filename_lower or filename_lower.endswith('.md'):
                analysis["has_docs"] = True
            if filename_lower in ['package.json', 'requirements.txt', 'pom.xml', 'build.gradle']:
                analysis["has_config"] = True
            if 'dockerfile' in filename_lower:
                analysis["has_dockerfile"] = True
            if '.github' in filename or '.gitlab-ci' in filename_lower or 'jenkinsfile' in filename_lower:
                analysis["has_ci_cd"] = True
            if '.env' in filename_lower:
                analysis["security_checks"]["has_env_file"] = True

            # Check file structure
            if '/src/' in filename or filename.startswith('src/'):
                analysis["file_structure"]["has_src_folder"] = True
            if '/components/' in filename or '/component/' in filename:
                analysis["file_structure"]["has_components"] = True
            if '/services/' in filename or '/service/' in filename:
                analysis["file_structure"]["has_services"] = True
            if '/utils/' in filename or '/util/' in filename or '/helpers/' in filename:
                analysis["file_structure"]["has_utils"] = True

            # Analyze code content
            if ext in ['py', 'js', 'ts', 'tsx', 'jsx', 'java', 'go', 'rs']:
                # Count comments
                comment_lines += len(re.findall(r'^\s*(#|//|/\*|\*)', content, re.MULTILINE))

                # Count functions/methods
                analysis["code_patterns"]["function_count"] += len(
                    re.findall(r'\b(def|function|func|fn)\s+\w+', content)
                )

                # Count classes
                analysis["code_patterns"]["class_count"] += len(
                    re.findall(r'\bclass\s+\w+', content)
                )

                # Count imports
                analysis["code_patterns"]["import_count"] += len(
                    re.findall(r'\b(import|from|require|use)\s+', content)
                )

                # Check for input validation
                if re.search(r'(validate|sanitize|escape|filter)', content, re.IGNORECASE):
                    analysis["security_checks"]["input_validation"] = True

                # Check for hardcoded secrets (simplified)
                if re.search(r'(password|secret|api_key|apikey)\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
                    analysis["security_checks"]["hardcoded_secrets"] = True

                code_lines += lines - comment_lines

        # Calculate comments ratio
        if code_lines > 0:
            analysis["code_patterns"]["comments_ratio"] = comment_lines / code_lines

        return analysis

    def _score_criterion(
        self,
        criterion: RubricCriterion,
        analysis: Dict[str, Any],
        files: Dict[str, str]
    ) -> tuple:
        """Score a single criterion based on code analysis."""
        max_points = criterion.max_points

        if criterion.name == "Code Quality":
            score = self._score_code_quality(analysis, max_points)
            feedback = self._get_code_quality_feedback(analysis, score, max_points)

        elif criterion.name == "Architecture & Design":
            score = self._score_architecture(analysis, max_points)
            feedback = self._get_architecture_feedback(analysis, score, max_points)

        elif criterion.name == "Functionality":
            score = self._score_functionality(analysis, files, max_points)
            feedback = self._get_functionality_feedback(analysis, score, max_points)

        elif criterion.name == "Documentation":
            score = self._score_documentation(analysis, max_points)
            feedback = self._get_documentation_feedback(analysis, score, max_points)

        elif criterion.name == "Testing":
            score = self._score_testing(analysis, max_points)
            feedback = self._get_testing_feedback(analysis, score, max_points)

        elif criterion.name == "Security":
            score = self._score_security(analysis, max_points)
            feedback = self._get_security_feedback(analysis, score, max_points)

        elif criterion.name == "UI/UX Design":
            score = self._score_ui_ux(analysis, files, max_points)
            feedback = self._get_ui_ux_feedback(analysis, score, max_points)

        elif criterion.name == "Innovation & Creativity":
            score = self._score_innovation(analysis, files, max_points)
            feedback = self._get_innovation_feedback(analysis, score, max_points)

        else:
            score = max_points * 0.6  # Default score
            feedback = "Standard implementation"

        return score, feedback

    def _score_code_quality(self, analysis: Dict[str, Any], max_points: int) -> float:
        """Score code quality based on analysis."""
        score = max_points * 0.5  # Base score

        # Comments ratio
        if analysis["code_patterns"]["comments_ratio"] > 0.15:
            score += max_points * 0.15
        elif analysis["code_patterns"]["comments_ratio"] > 0.08:
            score += max_points * 0.08

        # File structure
        structure = analysis["file_structure"]
        if structure["has_src_folder"]:
            score += max_points * 0.1
        if structure["has_components"] or structure["has_services"]:
            score += max_points * 0.1
        if structure["has_utils"]:
            score += max_points * 0.05

        # Functions and classes indicate modular code
        if analysis["code_patterns"]["function_count"] > 10:
            score += max_points * 0.1

        return min(score, max_points)

    def _score_architecture(self, analysis: Dict[str, Any], max_points: int) -> float:
        """Score architecture and design."""
        score = max_points * 0.4  # Base score

        structure = analysis["file_structure"]

        if structure["has_src_folder"]:
            score += max_points * 0.15
        if structure["has_components"]:
            score += max_points * 0.15
        if structure["has_services"]:
            score += max_points * 0.15
        if structure["has_utils"]:
            score += max_points * 0.1

        # Multiple languages might indicate microservices
        if len(analysis["languages"]) > 2:
            score += max_points * 0.05

        return min(score, max_points)

    def _score_functionality(self, analysis: Dict[str, Any], files: Dict[str, str], max_points: int) -> float:
        """Score functionality."""
        score = max_points * 0.5  # Base score

        # More files typically means more features
        if analysis["total_files"] > 20:
            score += max_points * 0.15
        elif analysis["total_files"] > 10:
            score += max_points * 0.1

        # More functions means more functionality
        if analysis["code_patterns"]["function_count"] > 30:
            score += max_points * 0.15
        elif analysis["code_patterns"]["function_count"] > 15:
            score += max_points * 0.1

        # Has config files
        if analysis["has_config"]:
            score += max_points * 0.1

        return min(score, max_points)

    def _score_documentation(self, analysis: Dict[str, Any], max_points: int) -> float:
        """Score documentation."""
        score = max_points * 0.3  # Base score

        if analysis["has_readme"]:
            score += max_points * 0.3
        if analysis["has_docs"]:
            score += max_points * 0.2
        if analysis["code_patterns"]["comments_ratio"] > 0.1:
            score += max_points * 0.2

        return min(score, max_points)

    def _score_testing(self, analysis: Dict[str, Any], max_points: int) -> float:
        """Score testing."""
        score = max_points * 0.2  # Base score

        if analysis["has_tests"]:
            score += max_points * 0.5
        if analysis["has_ci_cd"]:
            score += max_points * 0.3

        return min(score, max_points)

    def _score_security(self, analysis: Dict[str, Any], max_points: int) -> float:
        """Score security."""
        score = max_points * 0.5  # Base score

        security = analysis["security_checks"]

        if security["has_env_file"]:
            score += max_points * 0.2
        if security["input_validation"]:
            score += max_points * 0.2
        if not security["hardcoded_secrets"]:
            score += max_points * 0.2
        else:
            score -= max_points * 0.3  # Penalty for hardcoded secrets

        return max(0, min(score, max_points))

    def _score_ui_ux(self, analysis: Dict[str, Any], files: Dict[str, str], max_points: int) -> float:
        """Score UI/UX design."""
        score = max_points * 0.4  # Base score

        # Check for CSS/styling
        has_css = any(f.endswith(('.css', '.scss', '.sass', '.less')) for f in files.keys())
        has_tailwind = any('tailwind' in f.lower() for f in files.keys())

        if has_css or has_tailwind:
            score += max_points * 0.2

        # Check for components
        if analysis["file_structure"]["has_components"]:
            score += max_points * 0.2

        # Check for responsive design indicators
        for content in files.values():
            if 'media' in content and 'screen' in content:
                score += max_points * 0.2
                break

        return min(score, max_points)

    def _score_innovation(self, analysis: Dict[str, Any], files: Dict[str, str], max_points: int) -> float:
        """Score innovation and creativity."""
        score = max_points * 0.4  # Base score

        # Docker indicates modern practices
        if analysis["has_dockerfile"]:
            score += max_points * 0.2

        # CI/CD indicates advanced practices
        if analysis["has_ci_cd"]:
            score += max_points * 0.2

        # Multiple languages might indicate polyglot approach
        if len(analysis["languages"]) > 3:
            score += max_points * 0.2

        return min(score, max_points)

    def _get_code_quality_feedback(self, analysis: Dict[str, Any], score: float, max_points: int) -> str:
        """Generate feedback for code quality."""
        percentage = (score / max_points) * 100
        if percentage >= 90:
            return "Excellent code quality with clean organization and good documentation."
        elif percentage >= 70:
            return "Good code quality. Consider adding more comments and improving organization."
        elif percentage >= 50:
            return "Satisfactory code quality. Needs better organization and documentation."
        else:
            return "Code quality needs improvement. Focus on readability, comments, and structure."

    def _get_architecture_feedback(self, analysis: Dict[str, Any], score: float, max_points: int) -> str:
        percentage = (score / max_points) * 100
        if percentage >= 90:
            return "Excellent architecture with clear separation of concerns and modular design."
        elif percentage >= 70:
            return "Good architecture. Consider further modularization."
        elif percentage >= 50:
            return "Basic architecture. Would benefit from better separation of concerns."
        else:
            return "Architecture needs improvement. Consider using proper design patterns."

    def _get_functionality_feedback(self, analysis: Dict[str, Any], score: float, max_points: int) -> str:
        percentage = (score / max_points) * 100
        if percentage >= 90:
            return "All features implemented effectively with robust functionality."
        elif percentage >= 70:
            return "Good functionality. Most features working correctly."
        elif percentage >= 50:
            return "Core features implemented. Some enhancements needed."
        else:
            return "Functionality incomplete. Several features missing or not working."

    def _get_documentation_feedback(self, analysis: Dict[str, Any], score: float, max_points: int) -> str:
        percentage = (score / max_points) * 100
        if percentage >= 90:
            return "Comprehensive documentation with clear README and API docs."
        elif percentage >= 70:
            return "Good documentation. Consider adding more details."
        elif percentage >= 50:
            return "Basic documentation present. Needs more details."
        else:
            return "Documentation lacking. Add README and code comments."

    def _get_testing_feedback(self, analysis: Dict[str, Any], score: float, max_points: int) -> str:
        percentage = (score / max_points) * 100
        if percentage >= 90:
            return "Excellent test coverage with CI/CD integration."
        elif percentage >= 70:
            return "Good testing practices. Consider adding more tests."
        elif percentage >= 50:
            return "Some tests present. Increase coverage."
        else:
            return "Testing minimal. Add unit and integration tests."

    def _get_security_feedback(self, analysis: Dict[str, Any], score: float, max_points: int) -> str:
        percentage = (score / max_points) * 100
        if analysis["security_checks"]["hardcoded_secrets"]:
            return "CRITICAL: Remove hardcoded secrets and use environment variables."
        if percentage >= 90:
            return "Good security practices implemented."
        elif percentage >= 70:
            return "Reasonable security. Review for potential vulnerabilities."
        elif percentage >= 50:
            return "Security needs attention. Add input validation and secure practices."
        else:
            return "Security concerns present. Address authentication and validation."

    def _get_ui_ux_feedback(self, analysis: Dict[str, Any], score: float, max_points: int) -> str:
        percentage = (score / max_points) * 100
        if percentage >= 90:
            return "Excellent UI/UX with responsive and accessible design."
        elif percentage >= 70:
            return "Good UI/UX. Consider accessibility improvements."
        elif percentage >= 50:
            return "Functional UI. Improve responsiveness and user experience."
        else:
            return "UI/UX needs work. Focus on design consistency and responsiveness."

    def _get_innovation_feedback(self, analysis: Dict[str, Any], score: float, max_points: int) -> str:
        percentage = (score / max_points) * 100
        if percentage >= 90:
            return "Innovative approach with modern tools and practices."
        elif percentage >= 70:
            return "Shows creativity and modern development practices."
        elif percentage >= 50:
            return "Standard implementation. Consider innovative enhancements."
        else:
            return "Basic implementation. Explore creative solutions."

    def _determine_grade(self, percentage: float) -> GradeLevel:
        """Determine grade based on percentage."""
        if percentage >= 90:
            return GradeLevel.EXCELLENT
        elif percentage >= 70:
            return GradeLevel.GOOD
        elif percentage >= 50:
            return GradeLevel.SATISFACTORY
        else:
            return GradeLevel.NEEDS_IMPROVEMENT

    def _calculate_co_attainment(self, criteria_scores: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate Course Outcome attainment levels."""
        co_scores = {}
        co_counts = {}

        for criterion_name, data in criteria_scores.items():
            for co in data.get("co_mapped", []):
                if co not in co_scores:
                    co_scores[co] = 0
                    co_counts[co] = 0
                co_scores[co] += data["percentage"]
                co_counts[co] += 1

        co_attainment = {}
        for co, total_score in co_scores.items():
            co_attainment[co] = round(total_score / co_counts[co], 2)

        return co_attainment

    def _calculate_po_attainment(self, criteria_scores: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate Program Outcome attainment levels."""
        po_scores = {}
        po_counts = {}

        for criterion_name, data in criteria_scores.items():
            for po in data.get("po_mapped", []):
                if po not in po_scores:
                    po_scores[po] = 0
                    po_counts[po] = 0
                po_scores[po] += data["percentage"]
                po_counts[po] += 1

        po_attainment = {}
        for po, total_score in po_scores.items():
            po_attainment[po] = round(total_score / po_counts[po], 2)

        return po_attainment

    def _generate_feedback(self, criteria_scores: Dict[str, Dict[str, Any]]) -> tuple:
        """Generate strengths and improvement suggestions."""
        strengths = []
        improvements = []

        for criterion_name, data in criteria_scores.items():
            if data["percentage"] >= 80:
                strengths.append(f"{criterion_name}: {data['feedback']}")
            elif data["percentage"] < 60:
                improvements.append(f"{criterion_name}: {data['feedback']}")

        return strengths, improvements

    def _generate_detailed_feedback(
        self,
        criteria_scores: Dict[str, Dict[str, Any]],
        analysis: Dict[str, Any],
        grade: GradeLevel
    ) -> str:
        """Generate detailed evaluation feedback."""
        feedback = f"""
## Project Evaluation Report

### Overall Grade: {grade.value.upper()}

### Summary
- Total Files: {analysis['total_files']}
- Total Lines: {analysis['total_lines']}
- Languages Used: {', '.join(analysis['languages'].keys())}

### Criteria Breakdown
"""
        for criterion_name, data in criteria_scores.items():
            feedback += f"""
**{criterion_name}**
- Score: {data['score']:.1f}/{data['max_score']} ({data['percentage']:.1f}%)
- Feedback: {data['feedback']}
"""

        feedback += """
### Recommendations
"""
        for criterion_name, data in criteria_scores.items():
            if data["percentage"] < 70:
                feedback += f"- Improve {criterion_name}: {data['feedback']}\n"

        return feedback

    def create_custom_rubric(
        self,
        name: str,
        criteria_config: List[Dict[str, Any]]
    ) -> EvaluationRubric:
        """Create a custom evaluation rubric."""
        criteria = []
        for config in criteria_config:
            criterion = RubricCriterion(
                name=config["name"],
                description=config.get("description", ""),
                max_points=config.get("max_points", 10),
                levels=config.get("levels", {}),
                co_mapped=config.get("co_mapped", []),
                po_mapped=config.get("po_mapped", [])
            )
            criteria.append(criterion)

        total_points = sum(c.max_points for c in criteria)

        return EvaluationRubric(
            name=name,
            total_points=total_points,
            criteria=criteria,
            passing_percentage=50.0
        )

    def calculate_attainment(
        self,
        evaluation_scores: Dict[str, float],
        course_outcomes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate CO-PO attainment from evaluation scores.

        Args:
            evaluation_scores: Dictionary of criterion name to score
            course_outcomes: List of course outcomes with PO mappings

        Returns:
            Dictionary with CO attainment, PO contribution, and overall attainment
        """
        # Calculate CO attainment from evaluation scores
        co_attainment = {}
        for i, co in enumerate(course_outcomes):
            co_id = co.get("id", f"CO{i+1}")
            co_name = co.get("name", co_id)

            # Get target level (default 3.0 on 1-3 scale)
            target = co.get("target", 3.0)

            # Calculate achieved level based on relevant scores
            relevant_criteria = co.get("criteria", list(evaluation_scores.keys()))
            if relevant_criteria:
                scores = [evaluation_scores.get(c, 0) for c in relevant_criteria if c in evaluation_scores]
                if scores:
                    avg_score = sum(scores) / len(scores)
                    # Convert percentage to 1-3 scale
                    achieved = (avg_score / 100) * 3.0
                else:
                    achieved = 0.0
            else:
                # Use average of all scores
                if evaluation_scores:
                    avg_score = sum(evaluation_scores.values()) / len(evaluation_scores)
                    achieved = (avg_score / 100) * 3.0
                else:
                    achieved = 0.0

            # Calculate attainment percentage
            attainment_pct = (achieved / target) * 100 if target > 0 else 0

            co_attainment[co_id] = {
                "name": co_name,
                "target": target,
                "achieved": round(achieved, 2),
                "percentage": round(min(attainment_pct, 100), 2)
            }

        # Calculate PO contribution from CO attainment
        po_contribution = {}
        po_counts = {}

        for co in course_outcomes:
            co_id = co.get("id", "CO1")
            po_mapping = co.get("po_mapping", {})

            if co_id in co_attainment:
                co_achieved = co_attainment[co_id]["achieved"]

                for po_id, weight in po_mapping.items():
                    if po_id not in po_contribution:
                        po_contribution[po_id] = 0
                        po_counts[po_id] = 0

                    po_contribution[po_id] += co_achieved * weight
                    po_counts[po_id] += weight

        # Normalize PO contributions
        for po_id in po_contribution:
            if po_counts[po_id] > 0:
                po_contribution[po_id] = round(
                    (po_contribution[po_id] / po_counts[po_id] / 3.0) * 100,
                    2
                )

        # Calculate overall attainment
        if co_attainment:
            overall = sum(co["percentage"] for co in co_attainment.values()) / len(co_attainment)
        else:
            overall = 0.0

        return {
            "co_attainment": co_attainment,
            "po_contribution": po_contribution,
            "overall_attainment": round(overall, 2)
        }


# Singleton instance
project_evaluator = ProjectEvaluator()
