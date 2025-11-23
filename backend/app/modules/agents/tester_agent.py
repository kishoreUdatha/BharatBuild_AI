"""
AGENT 4 - Tester Agent
Generates comprehensive tests and runs them to ensure code quality
"""

from typing import Dict, List, Optional, Any
import json
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.modules.automation import file_manager, build_system


class TesterAgent(BaseAgent):
    """
    Tester Agent

    Responsibilities:
    - Generate unit tests for backend code
    - Generate component tests for frontend
    - Generate integration tests for APIs
    - Generate end-to-end tests
    - Run tests and report results
    - Achieve high code coverage
    - Test edge cases and error scenarios
    """

    SYSTEM_PROMPT = """You are an expert Testing Agent for BharatBuild AI, a platform that helps students build high-quality projects.

YOUR ROLE:
- Generate comprehensive test suites for backend and frontend code
- Write unit tests, integration tests, and end-to-end tests
- Ensure high code coverage (aim for 80%+)
- Test edge cases, error scenarios, and happy paths
- Generate test data and fixtures
- Create test configuration files
- Run tests and analyze results
- Help students understand testing best practices

INPUT YOU RECEIVE:
1. Generated code from Coder Agent
2. Project structure and tech stack
3. API endpoints and components to test

YOUR OUTPUT MUST BE VALID JSON:
{
  "test_strategy": {
    "approach": "Unit tests + Integration tests + E2E tests",
    "coverage_goal": "80%",
    "test_frameworks": {
      "backend": "pytest",
      "frontend": "jest + react-testing-library",
      "e2e": "playwright"
    },
    "priority_areas": [
      "Authentication flows",
      "CRUD operations",
      "Error handling",
      "Edge cases"
    ]
  },
  "test_files": [
    {
      "path": "backend/tests/test_auth.py",
      "content": "complete test file content",
      "language": "python",
      "test_type": "unit",
      "tests_count": 8,
      "description": "Tests for authentication endpoints",
      "coverage_areas": ["register", "login", "token validation"],
      "educational_notes": "Shows how to test API endpoints with fixtures"
    }
  ],
  "test_configuration": [
    {
      "path": "backend/pytest.ini",
      "content": "pytest configuration",
      "description": "Configure pytest with coverage"
    },
    {
      "path": "frontend/jest.config.js",
      "content": "jest configuration",
      "description": "Configure Jest for React testing"
    }
  ],
  "test_data": [
    {
      "path": "backend/tests/fixtures/users.json",
      "content": "test user data",
      "description": "Sample user data for testing"
    }
  ],
  "test_execution": {
    "commands": {
      "backend": "pytest --cov=app --cov-report=html",
      "frontend": "npm test -- --coverage",
      "e2e": "npx playwright test"
    },
    "expected_coverage": {
      "backend": "85%",
      "frontend": "80%"
    }
  },
  "test_results": {
    "total_tests": 45,
    "passed": 45,
    "failed": 0,
    "skipped": 0,
    "coverage": "87%",
    "duration": "12.5s"
  }
}

TEST WRITING RULES:

1. **Test Coverage**:
   - Write tests for ALL public functions/endpoints
   - Test happy paths (expected behavior)
   - Test edge cases (empty inputs, max values, special characters)
   - Test error scenarios (invalid inputs, auth failures, network errors)
   - Aim for 80%+ code coverage

2. **Test Structure** (AAA Pattern):
   ```python
   def test_user_registration():
       # ARRANGE - Set up test data
       user_data = {"email": "test@example.com", "password": "Test123!"}

       # ACT - Execute the code being tested
       response = client.post("/api/auth/register", json=user_data)

       # ASSERT - Verify results
       assert response.status_code == 201
       assert "access_token" in response.json()
   ```

3. **Backend Testing (Python/FastAPI)**:
   - Use pytest with fixtures
   - Test database operations with test database
   - Mock external API calls
   - Test authentication and authorization
   - Test input validation
   - Test error handling

   Example:
   ```python
   import pytest
   from fastapi.testclient import TestClient

   @pytest.fixture
   def client():
       return TestClient(app)

   def test_login_success(client):
       response = client.post("/api/auth/login", json={
           "email": "user@example.com",
           "password": "password123"
       })
       assert response.status_code == 200
       assert "access_token" in response.json()
   ```

4. **Frontend Testing (React/Jest)**:
   - Use React Testing Library
   - Test component rendering
   - Test user interactions (clicks, inputs)
   - Test state changes
   - Mock API calls
   - Test error boundaries

   Example:
   ```typescript
   import { render, screen, fireEvent } from '@testing-library/react'
   import LoginForm from '@/components/LoginForm'

   test('renders login form', () => {
       render(<LoginForm />)
       expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
       expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
   })

   test('submits form with valid data', async () => {
       render(<LoginForm />)
       fireEvent.change(screen.getByLabelText(/email/i), {
           target: { value: 'test@example.com' }
       })
       fireEvent.click(screen.getByRole('button', { name: /login/i }))
       // Assert API was called
   })
   ```

5. **Integration Tests**:
   - Test complete workflows (register → login → create todo → logout)
   - Test API endpoints with real database
   - Test authentication flow end-to-end
   - Test error propagation

6. **E2E Tests (Playwright/Cypress)**:
   - Test critical user journeys
   - Test across different browsers
   - Test responsive design
   - Example: User registration → Create 3 todos → Mark as complete → Logout

7. **Test Data and Fixtures**:
   - Create reusable test data
   - Use factories for complex objects
   - Clean up after tests (transactions, test database)
   - Use realistic test data

8. **Educational Value**:
   - Add comments explaining testing concepts
   - Show different assertion types
   - Demonstrate mocking and stubbing
   - Explain why each test is important

9. **Test Organization**:
   ```
   backend/tests/
       __init__.py
       conftest.py          # Pytest fixtures
       test_auth.py         # Authentication tests
       test_todos.py        # Todo CRUD tests
       test_models.py       # Database model tests
       fixtures/
           users.json       # Test data

   frontend/src/__tests__/
       components/
           LoginForm.test.tsx
           TodoList.test.tsx
       hooks/
           useAuth.test.ts
       integration/
           auth-flow.test.tsx
   ```

10. **Test Quality Checklist**:
    - [ ] Tests are independent (can run in any order)
    - [ ] Tests are deterministic (same result every time)
    - [ ] Tests are fast (< 100ms per unit test)
    - [ ] Tests have clear names describing what they test
    - [ ] Tests use proper assertions
    - [ ] Tests clean up after themselves
    - [ ] Tests are easy to understand (good for students)

EXAMPLE OUTPUT:

For a Todo App with authentication:

{
  "test_files": [
    {
      "path": "backend/tests/test_auth.py",
      "content": "import pytest\\nfrom fastapi.testclient import TestClient\\nfrom app.main import app\\n\\nclient = TestClient(app)\\n\\ndef test_register_new_user():\\n    \\\"\\\"\\\"Test successful user registration\\\"\\\"\\\"\\n    # Arrange\\n    user_data = {\\n        \\\"email\\\": \\\"newuser@example.com\\\",\\n        \\\"password\\\": \\\"SecurePass123!\\\"\\n    }\\n    \\n    # Act\\n    response = client.post(\\\"/api/auth/register\\\", json=user_data)\\n    \\n    # Assert\\n    assert response.status_code == 201\\n    assert \\\"access_token\\\" in response.json()\\n    assert response.json()[\\\"token_type\\\"] == \\\"bearer\\\"\\n\\ndef test_register_duplicate_email():\\n    \\\"\\\"\\\"Test that duplicate email registration fails\\\"\\\"\\\"\\n    user_data = {\\\"email\\\": \\\"existing@example.com\\\", \\\"password\\\": \\\"pass\\\"}\\n    \\n    # Register first time\\n    client.post(\\\"/api/auth/register\\\", json=user_data)\\n    \\n    # Try to register again with same email\\n    response = client.post(\\\"/api/auth/register\\\", json=user_data)\\n    \\n    assert response.status_code == 400\\n    assert \\\"already registered\\\" in response.json()[\\\"detail\\\"].lower()...",
      "test_type": "unit",
      "tests_count": 6
    }
  ]
}

REMEMBER:
- Students learn best practices from these tests
- Tests should be readable and educational
- High coverage protects against bugs
- Tests document expected behavior
"""

    def __init__(self):
        super().__init__(
            name="Tester Agent",
            role="test_generator",
            capabilities=[
                "unit_test_generation",
                "integration_test_generation",
                "e2e_test_generation",
                "test_execution",
                "coverage_analysis",
                "test_data_generation"
            ]
        )

    async def process(
        self,
        context: AgentContext,
        code_files: Optional[List[Dict]] = None,
        architecture: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive tests for the project

        Args:
            context: Agent context with user request
            code_files: Generated code from Coder Agent
            architecture: System architecture from Architect Agent

        Returns:
            Dict with test files, configuration, and execution results
        """
        try:
            logger.info(f"[Tester Agent] Generating tests for project {context.project_id}")

            # Build prompt with code context
            enhanced_prompt = self._build_test_generation_prompt(
                context.user_request,
                code_files,
                architecture
            )

            # Call Claude API
            response = await self._call_claude(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=enhanced_prompt,
                temperature=0.3
            )

            # Parse JSON response
            test_output = self._parse_test_output(response)

            # Write test files to disk
            test_files_created = await self._write_test_files(
                context.project_id,
                test_output.get("test_files", []) +
                test_output.get("test_configuration", []) +
                test_output.get("test_data", [])
            )

            # Run tests if requested
            test_results = None
            if context.metadata.get("run_tests", True):
                test_results = await self._run_tests(context.project_id, test_output)

            logger.info(f"[Tester Agent] Generated {len(test_files_created)} test files")

            return {
                "success": True,
                "agent": self.name,
                "test_strategy": test_output.get("test_strategy", {}),
                "test_files_created": test_files_created,
                "test_execution": test_output.get("test_execution", {}),
                "test_results": test_results,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Tester Agent] Error: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_test_generation_prompt(
        self,
        user_request: str,
        code_files: Optional[List[Dict]],
        architecture: Optional[Dict]
    ) -> str:
        """Build enhanced prompt with code context"""

        prompt_parts = [
            f"USER REQUEST:\n{user_request}\n"
        ]

        if architecture:
            prompt_parts.append(f"\nSYSTEM ARCHITECTURE:\n{json.dumps(architecture, indent=2)}\n")

        if code_files:
            # Include relevant code files for context
            prompt_parts.append("\nGENERATED CODE FILES:\n")
            for file_info in code_files[:10]:  # Limit to first 10 files for context
                prompt_parts.append(f"\nFile: {file_info['path']}")
                prompt_parts.append(f"Language: {file_info.get('language', 'unknown')}")
                # Include first 50 lines of code for context
                content = file_info.get('content', '')
                lines = content.split('\n')[:50]
                prompt_parts.append(f"```\n{chr(10).join(lines)}\n```\n")

        prompt_parts.append("""
TASK:
Generate comprehensive test suites for this project. Include:

1. **Unit Tests**:
   - Test individual functions/methods
   - Test API endpoints
   - Test database models
   - Test utility functions

2. **Integration Tests**:
   - Test complete workflows
   - Test API with database
   - Test authentication flow

3. **Frontend Tests** (if applicable):
   - Component rendering tests
   - User interaction tests
   - State management tests

4. **E2E Tests**:
   - Critical user journeys
   - Authentication → CRUD → Logout flows

5. **Test Configuration**:
   - pytest.ini, jest.config.js, etc.
   - Coverage settings
   - Test database setup

6. **Test Data**:
   - Fixtures and factories
   - Sample data

Requirements:
- Aim for 80%+ code coverage
- Test edge cases and errors
- Educational comments
- Follow AAA pattern (Arrange, Act, Assert)
- Use appropriate test frameworks

Output valid JSON following the specified format.
""")

        return "\n".join(prompt_parts)

    def _parse_test_output(self, response: str) -> Dict:
        """Parse JSON output from Claude"""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1

            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            json_str = response[start:end]
            test_output = json.loads(json_str)

            return test_output

        except json.JSONDecodeError as e:
            logger.error(f"[Tester Agent] JSON parse error: {e}")
            raise ValueError(f"Invalid JSON in Claude response: {e}")

    async def _write_test_files(
        self,
        project_id: str,
        test_files: List[Dict]
    ) -> List[Dict]:
        """Write test files to disk"""
        created_files = []

        for file_info in test_files:
            try:
                file_path = file_info["path"]
                content = file_info["content"]

                result = await file_manager.create_file(
                    project_id=project_id,
                    file_path=file_path,
                    content=content
                )

                if result["success"]:
                    created_files.append({
                        "path": file_path,
                        "test_type": file_info.get("test_type"),
                        "tests_count": file_info.get("tests_count"),
                        "description": file_info.get("description")
                    })
                    logger.info(f"[Tester Agent] Created test file: {file_path}")

            except Exception as e:
                logger.error(f"[Tester Agent] Error writing test file: {e}")

        return created_files

    async def _run_tests(
        self,
        project_id: str,
        test_output: Dict
    ) -> Dict:
        """
        Run the generated tests

        Args:
            project_id: Project identifier
            test_output: Test configuration with commands

        Returns:
            Dict with test execution results
        """
        try:
            test_commands = test_output.get("test_execution", {}).get("commands", {})
            results = {}

            # Run backend tests
            if "backend" in test_commands:
                backend_result = await build_system.test(
                    project_id=project_id,
                    test_command=test_commands["backend"]
                )
                results["backend"] = backend_result

            # Run frontend tests
            if "frontend" in test_commands:
                frontend_result = await build_system.test(
                    project_id=project_id,
                    test_command=test_commands["frontend"]
                )
                results["frontend"] = frontend_result

            return {
                "executed": True,
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Tester Agent] Error running tests: {e}")
            return {
                "executed": False,
                "error": str(e)
            }

    async def generate_test_for_file(
        self,
        file_path: str,
        file_content: str,
        language: str
    ) -> Dict:
        """
        Generate tests for a specific file

        Args:
            file_path: Path to file to test
            file_content: Content of the file
            language: Programming language

        Returns:
            Dict with test file content
        """
        prompt = f"""
Generate comprehensive tests for this file:

FILE: {file_path}
LANGUAGE: {language}

CODE:
```
{file_content}
```

Generate:
1. Unit tests for all public functions/methods
2. Edge case tests
3. Error scenario tests

Return JSON:
{{
  "test_file_path": "path/to/test_file",
  "content": "complete test content",
  "tests_count": 10,
  "coverage_areas": ["function1", "function2"]
}}
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3
        )

        return self._parse_test_output(response)


# Singleton instance
tester_agent = TesterAgent()
