# Contributing to BharatBuild AI

Thank you for your interest in contributing to BharatBuild AI! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Use the bug report template**
3. **Provide detailed information**:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots if applicable
   - Environment details (OS, Docker version, etc.)

### Suggesting Features

1. **Check existing feature requests**
2. **Use the feature request template**
3. **Provide clear use cases**
4. **Explain the value** it would add

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Write/update tests**
5. **Update documentation**
6. **Follow code style guidelines**
7. **Commit with clear messages**:
   ```bash
   git commit -m "feat: add new agent for document generation"
   ```
8. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
9. **Create a Pull Request**

## Development Setup

1. Follow the [SETUP_GUIDE.md](docs/SETUP_GUIDE.md)
2. Install development dependencies:
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If exists

   # Frontend
   cd frontend
   npm install
   ```

## Code Style Guidelines

### Python (Backend)

- Follow **PEP 8**
- Use **type hints**
- Maximum line length: **88 characters** (Black default)
- Use **docstrings** for functions and classes
- Run formatters before committing:
  ```bash
  black app
  isort app
  flake8 app
  mypy app
  ```

Example:
```python
async def create_project(
    user_id: UUID,
    project_data: ProjectCreate,
    db: AsyncSession
) -> Project:
    """
    Create a new project for the user.

    Args:
        user_id: The ID of the user creating the project
        project_data: Project creation data
        db: Database session

    Returns:
        The created project

    Raises:
        ValueError: If project data is invalid
    """
    project = Project(
        user_id=user_id,
        title=project_data.title,
        description=project_data.description
    )
    db.add(project)
    await db.commit()
    return project
```

### TypeScript/React (Frontend)

- Use **TypeScript** strictly
- Follow **Airbnb style guide**
- Use **functional components** with hooks
- Proper **prop types** definition
- Run linter before committing:
  ```bash
  npm run lint
  npm run type-check
  ```

Example:
```typescript
interface ProjectCardProps {
  project: Project
  onDelete: (id: string) => void
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  return (
    <div className="rounded-lg border p-4">
      <h3 className="text-lg font-semibold">{project.title}</h3>
      <p className="text-sm text-gray-600">{project.description}</p>
      <button onClick={() => onDelete(project.id)}>Delete</button>
    </div>
  )
}
```

## Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app --cov-report=html
```

Test structure:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/projects",
        json={"title": "Test Project", "mode": "student"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test Project"
```

### Frontend Tests

```bash
# Run tests
npm test

# Run with coverage
npm test -- --coverage
```

## Commit Message Guidelines

Follow **Conventional Commits**:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Examples:
```
feat: add UML diagram generation agent
fix: resolve authentication token expiry issue
docs: update API documentation for project endpoints
test: add tests for multi-agent orchestrator
```

## Project Structure

When adding new features, follow the existing structure:

### Backend
```
backend/app/
├── api/v1/endpoints/     # Add new API endpoints here
├── models/               # Add new database models
├── schemas/              # Add Pydantic schemas
├── modules/              # Add business logic
│   └── your_module/
│       ├── __init__.py
│       ├── service.py
│       ├── tasks.py      # Celery tasks
│       └── utils.py
└── utils/                # Shared utilities
```

### Frontend
```
frontend/src/
├── app/                  # Next.js pages
├── components/           # React components
│   └── YourComponent/
│       ├── index.tsx
│       └── YourComponent.test.tsx
├── lib/                  # Utilities and helpers
└── hooks/                # Custom React hooks
```

## Documentation

- Update relevant documentation in `/docs`
- Add JSDoc/docstrings to new functions
- Update API documentation if adding endpoints
- Update README if adding major features

## Areas Needing Contributions

High priority:
- [ ] Additional AI agents (UML, Report, PPT, Viva)
- [ ] Document generation utilities (DOCX, PPTX, PDF)
- [ ] Frontend dashboard and UI components
- [ ] WebSocket support for real-time updates
- [ ] Test coverage improvements
- [ ] Performance optimizations

Medium priority:
- [ ] Admin dashboard
- [ ] Analytics and reporting
- [ ] Email notification system
- [ ] File upload handling
- [ ] Advanced caching strategies

Nice to have:
- [ ] Mobile app
- [ ] CLI tool
- [ ] VSCode extension
- [ ] Browser extension
- [ ] Additional integrations

## Getting Help

- **Discord**: Join our community (link in README)
- **GitHub Discussions**: Ask questions
- **Email**: dev@bharatbuild.ai

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Recognized in the community

Thank you for contributing to BharatBuild AI! 🚀
