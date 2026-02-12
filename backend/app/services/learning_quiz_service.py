"""
Learning Quiz Service - Generate quiz questions based on generated code
Reuses campus-drive question format for consistency
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import uuid

from app.core.logging_config import logger
# Use hybrid_client for Qwen/Claude routing
from app.utils.hybrid_client import HybridClient as ClaudeClient, hybrid_client


class LearningQuizService:
    """Generate quiz questions about the project code for learning checkpoints"""

    SYSTEM_PROMPT = """You are an expert educator creating quiz questions to test student understanding of code.

Your job is to generate multiple-choice questions that:
1. Test UNDERSTANDING, not just memorization
2. Focus on WHY code is written a certain way, not just WHAT it does
3. Cover design patterns, best practices, and key concepts
4. Are fair but challenging
5. Include questions about how components interact

Question categories to cover:
- Design patterns used (e.g., Singleton, Factory, MVC)
- Why certain approaches were chosen
- How components interact
- Security considerations
- Performance implications
- Best practices implemented
- Common pitfalls avoided

Each question must have:
- Clear, unambiguous question text
- 4 distinct options (A, B, C, D)
- One clearly correct answer
- An explanation of why the correct answer is right

Return questions in valid JSON format."""

    def __init__(self):
        self.claude_client = ClaudeClient()

    async def generate_questions(
        self,
        project_id: str,
        files: List[Dict[str, Any]],
        project_context: Optional[Dict[str, Any]] = None,
        num_questions: int = 5,
        difficulty: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """
        Generate quiz questions based on project code.

        Args:
            project_id: Project ID
            files: List of file dicts with {path, content, language}
            project_context: Optional context about the project
            num_questions: Number of questions to generate (default 5)
            difficulty: easy, medium, hard, or mixed

        Returns:
            List of question dicts in campus-drive format
        """
        try:
            logger.info(f"[LearningQuizService] Generating {num_questions} questions for project {project_id}")

            # Build prompt with code context
            prompt = self._build_quiz_prompt(files, project_context, num_questions, difficulty)

            # Call Claude to generate questions
            response = await self.claude_client.call(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=prompt,
                max_tokens=4096,
                temperature=0.7  # Slight creativity for varied questions
            )

            # Parse questions from response
            questions = self._parse_questions(response, project_id)

            logger.info(f"[LearningQuizService] Generated {len(questions)} questions")
            return questions

        except Exception as e:
            logger.error(f"[LearningQuizService] Error generating questions: {e}", exc_info=True)
            # Return fallback questions if generation fails
            return self._get_fallback_questions(project_id)

    def _build_quiz_prompt(
        self,
        files: List[Dict[str, Any]],
        project_context: Optional[Dict[str, Any]],
        num_questions: int,
        difficulty: str
    ) -> str:
        """Build the prompt for quiz generation"""
        prompt_parts = []

        # Add project context if available
        if project_context:
            prompt_parts.append(f"""PROJECT CONTEXT:
- Title: {project_context.get('title', 'Unknown Project')}
- Domain: {project_context.get('domain', 'Web Application')}
- Tech Stack: {', '.join(project_context.get('tech_stack', ['Full Stack']))}
- Description: {project_context.get('description', '')[:500]}
""")

        # Add code files (limit to most important ones)
        prompt_parts.append("\nCODE FILES TO ANALYZE:")
        important_files = self._select_important_files(files)

        for file in important_files[:10]:  # Limit to 10 files for context
            content = file.get('content', '')
            # Truncate long files
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"

            prompt_parts.append(f"""
--- {file.get('path', 'unknown')} ---
```{file.get('language', '')}
{content}
```
""")

        # Add generation instructions
        difficulty_instruction = {
            "easy": "Focus on basic concepts and straightforward code understanding.",
            "medium": "Include questions about design decisions and how components work together.",
            "hard": "Include advanced questions about optimization, security, and edge cases.",
            "mixed": "Mix easy (2), medium (2), and hard (1) questions for balanced assessment."
        }.get(difficulty, "Mix difficulty levels appropriately.")

        prompt_parts.append(f"""
TASK:
Generate exactly {num_questions} multiple-choice questions about this code.
{difficulty_instruction}

QUESTION GUIDELINES:
1. Test understanding of WHY code is written a certain way
2. Ask about design patterns and their benefits
3. Include questions about how different parts interact
4. Test knowledge of best practices being followed
5. Ask about potential issues if code were changed

OUTPUT FORMAT (valid JSON array):
[
  {{
    "question_text": "Why does the authentication module use JWT tokens instead of sessions?",
    "options": [
      "JWTs are smaller in size",
      "JWTs are stateless and scale better across multiple servers",
      "JWTs are more secure than sessions",
      "JWTs are easier to implement"
    ],
    "correct_option": 1,
    "explanation": "JWTs are stateless tokens that don't require server-side storage, making them ideal for distributed systems where requests might hit different servers.",
    "concept": "JWT Authentication",
    "difficulty": "medium",
    "related_file": "backend/app/core/security.py"
  }},
  ...
]

Generate {num_questions} questions now.
""")

        return "\n".join(prompt_parts)

    def _select_important_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Select the most important files for quiz generation"""
        # Priority patterns (higher priority first)
        priority_patterns = [
            # Auth/Security
            'auth', 'security', 'login', 'jwt',
            # Core logic
            'service', 'controller', 'handler',
            # Data
            'model', 'schema', 'database',
            # API
            'endpoint', 'route', 'api',
            # Frontend core
            'app.tsx', 'app.jsx', 'main.tsx', 'main.jsx',
            # State management
            'store', 'context', 'reducer',
            # Components
            'component',
        ]

        # Exclude patterns
        exclude_patterns = [
            'test', 'spec', '__pycache__', '.git', 'node_modules',
            'package-lock', 'yarn.lock', '.env', 'readme', 'license',
            '.md', '.txt', '.json', '.yml', '.yaml', 'config'
        ]

        def get_priority(file: Dict) -> int:
            path = file.get('path', '').lower()

            # Exclude non-code files
            for pattern in exclude_patterns:
                if pattern in path:
                    return 999

            # Calculate priority based on patterns
            for i, pattern in enumerate(priority_patterns):
                if pattern in path:
                    return i

            return 100  # Default priority for other code files

        # Sort by priority
        sorted_files = sorted(files, key=get_priority)

        # Filter out excluded files
        return [f for f in sorted_files if get_priority(f) < 999]

    def _parse_questions(self, response: str, project_id: str) -> List[Dict[str, Any]]:
        """Parse questions from Claude's response"""
        try:
            # Extract JSON from response
            content = response

            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1].strip()

            # Find JSON array
            start = content.find('[')
            end = content.rfind(']') + 1

            if start == -1 or end == 0:
                raise ValueError("No JSON array found in response")

            json_str = content[start:end]
            questions_data = json.loads(json_str)

            # Format questions to match our model
            questions = []
            for q in questions_data:
                questions.append({
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "question_text": q.get("question_text", ""),
                    "question_type": "multiple_choice",
                    "options": q.get("options", []),
                    "correct_option": q.get("correct_option", 0),
                    "explanation": q.get("explanation", ""),
                    "related_file": q.get("related_file"),
                    "concept": q.get("concept", "General"),
                    "difficulty": q.get("difficulty", "medium"),
                    "created_at": datetime.utcnow().isoformat()
                })

            return questions

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"[LearningQuizService] Failed to parse questions: {e}")
            return self._get_fallback_questions(project_id)

    def _get_fallback_questions(self, project_id: str) -> List[Dict[str, Any]]:
        """Return generic fallback questions if generation fails"""
        return [
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "question_text": "What is the primary purpose of separating frontend and backend code?",
                "question_type": "multiple_choice",
                "options": [
                    "To make the code look organized",
                    "To allow independent scaling and development of each layer",
                    "Because it's required by all frameworks",
                    "To use more programming languages"
                ],
                "correct_option": 1,
                "explanation": "Separating frontend and backend allows teams to work independently, scale each layer based on demand, and choose the best technology for each concern.",
                "concept": "Architecture",
                "difficulty": "easy",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "question_text": "Why is input validation important in web applications?",
                "question_type": "multiple_choice",
                "options": [
                    "To make the code run faster",
                    "To prevent security vulnerabilities like SQL injection and XSS",
                    "To reduce the size of the database",
                    "To make the UI look better"
                ],
                "correct_option": 1,
                "explanation": "Input validation prevents malicious data from being processed, protecting against common attacks like SQL injection, XSS, and command injection.",
                "concept": "Security",
                "difficulty": "medium",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "question_text": "What is the benefit of using environment variables for configuration?",
                "question_type": "multiple_choice",
                "options": [
                    "They make the code run faster",
                    "They keep sensitive data out of the codebase and allow different configs per environment",
                    "They are required by all hosting providers",
                    "They reduce the number of files in the project"
                ],
                "correct_option": 1,
                "explanation": "Environment variables keep sensitive data (API keys, passwords) out of version control and allow the same code to run with different configurations in dev, staging, and production.",
                "concept": "Configuration",
                "difficulty": "easy",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "question_text": "Why should passwords never be stored in plain text?",
                "question_type": "multiple_choice",
                "options": [
                    "Plain text takes more storage space",
                    "If the database is compromised, all user passwords would be exposed",
                    "Plain text passwords are slower to process",
                    "Browsers don't support plain text passwords"
                ],
                "correct_option": 1,
                "explanation": "Storing passwords in plain text means if an attacker gains database access, they immediately have all user passwords. Hashing makes passwords unreadable even if the database is compromised.",
                "concept": "Security",
                "difficulty": "medium",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "question_text": "What is the main advantage of using async/await in web applications?",
                "question_type": "multiple_choice",
                "options": [
                    "It makes the code shorter",
                    "It allows handling multiple requests without blocking, improving performance",
                    "It's required by modern browsers",
                    "It uses less memory"
                ],
                "correct_option": 1,
                "explanation": "Async/await allows non-blocking I/O operations. While waiting for database queries or API calls, the server can handle other requests, significantly improving throughput.",
                "concept": "Performance",
                "difficulty": "medium",
                "created_at": datetime.utcnow().isoformat()
            }
        ]

    async def evaluate_quiz(
        self,
        questions: List[Dict[str, Any]],
        answers: Dict[str, int],
        passing_score: float = 70.0
    ) -> Dict[str, Any]:
        """
        Evaluate quiz answers and return results.

        Args:
            questions: List of question dicts
            answers: Dict of {question_id: selected_option}
            passing_score: Minimum score to pass (default 70%)

        Returns:
            Dict with score, passed status, and feedback
        """
        total_questions = len(questions)
        correct_count = 0
        results = []

        for question in questions:
            q_id = question.get('id')
            selected = answers.get(q_id)
            correct = question.get('correct_option')
            is_correct = selected == correct

            if is_correct:
                correct_count += 1

            results.append({
                "question_id": q_id,
                "question_text": question.get('question_text'),
                "selected_option": selected,
                "correct_option": correct,
                "is_correct": is_correct,
                "explanation": question.get('explanation'),
                "concept": question.get('concept')
            })

        score = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        passed = score >= passing_score

        return {
            "total_questions": total_questions,
            "correct_answers": correct_count,
            "score": round(score, 2),
            "passing_score": passing_score,
            "passed": passed,
            "results": results,
            "feedback": self._generate_feedback(score, results)
        }

    def _generate_feedback(self, score: float, results: List[Dict]) -> str:
        """Generate feedback based on quiz performance"""
        if score >= 90:
            return "Excellent! You have a strong understanding of the code and concepts used in this project."
        elif score >= 70:
            return "Good job! You understand the key concepts. Review the explanations for questions you missed to strengthen your knowledge."
        elif score >= 50:
            return "You're getting there! Review the code explanations and pay attention to the design patterns and best practices used."
        else:
            return "Take some more time to study the code and its explanations. Focus on understanding WHY certain approaches were used, not just WHAT the code does."


# Singleton instance
learning_quiz_service = LearningQuizService()
