# BharatBuild AI - Codebase Stabilization Plan

## Executive Summary

Current State:
- **Backend Test Coverage**: ~10% (21 tests for 222 files)
- **Frontend Test Coverage**: 0%
- **Silent Exceptions**: 738 generic catches, 101 pass statements
- **Technical Debt**: 29 TODO/FIXME markers
- **Fix Commit Rate**: ~60% of recent commits are bug fixes

Goal: Reduce bug fix commits to <20% and increase test coverage to 60%+

---

## Phase 1: Immediate Stabilization (Week 1)

### 1.1 Add Pre-commit Hooks
Prevent bad code from being committed.

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml (already created)
pre-commit install
```

**Checks:**
- Python linting (ruff)
- Type checking (mypy)
- Frontend linting (eslint)
- No secrets in code
- File size limits

### 1.2 Fix Critical Silent Exceptions
Priority files with most silent failures:

| File | Silent Exceptions | Priority |
|------|-------------------|----------|
| `dynamic_orchestrator.py` | 45 | HIGH |
| `docker_executor.py` | 44 | HIGH |
| `orchestrator.py` (endpoints) | 27 | HIGH |
| `bolt.py` | 14 | MEDIUM |
| `word_generator.py` | 15 | MEDIUM |

**Action**: Replace `pass` with proper logging:
```python
# Before
except Exception:
    pass

# After
except Exception as e:
    logger.error(f"[ModuleName] Operation failed: {e}", exc_info=True)
    raise  # or return appropriate error response
```

### 1.3 Add Critical Path Tests
Must-have tests for core functionality:

1. **Authentication** (`test_auth_critical.py`)
   - Login/logout flow
   - Token refresh
   - Session isolation

2. **Document Generation** (`test_document_generation.py`)
   - SRS generation
   - PPT generation
   - UML diagram generation

3. **Project Operations** (`test_project_critical.py`)
   - Create project
   - Load project files
   - Save/sync files

---

## Phase 2: Test Infrastructure (Week 2-3)

### 2.1 Backend Test Structure
```
backend/tests/
├── unit/
│   ├── agents/           # Agent logic tests
│   ├── services/         # Service layer tests
│   ├── api/              # API endpoint tests
│   └── automation/       # Document generators
├── integration/
│   ├── test_auth_flow.py
│   ├── test_project_flow.py
│   └── test_document_flow.py
└── fixtures/
    ├── sample_projects.py
    ├── mock_claude.py
    └── test_data.py
```

### 2.2 Frontend Test Structure
```
frontend/
├── __tests__/
│   ├── components/
│   ├── hooks/
│   ├── utils/
│   └── pages/
├── jest.config.js
└── setupTests.ts
```

### 2.3 Test Coverage Targets

| Week | Backend | Frontend | Total |
|------|---------|----------|-------|
| Current | 10% | 0% | 5% |
| Week 2 | 30% | 10% | 20% |
| Week 3 | 50% | 30% | 40% |
| Week 4 | 60% | 50% | 55% |

---

## Phase 3: CI/CD Enforcement (Week 3-4)

### 3.1 GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [master, main, develop]
  pull_request:
    branches: [master, main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Backend Tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest tests/ --cov=app --cov-fail-under=50

      - name: Frontend Tests
        run: |
          cd frontend
          npm ci
          npm run test:ci

      - name: Type Check
        run: |
          cd backend
          mypy app/ --ignore-missing-imports
```

### 3.2 Branch Protection Rules
- Require PR reviews before merge
- Require status checks to pass
- Require branches to be up to date
- No force push to main/master

---

## Phase 4: Code Quality (Ongoing)

### 4.1 Error Handling Standards

**DO:**
```python
from app.core.exceptions import DocumentGenerationError

async def generate_document(project_id: str) -> Document:
    try:
        project = await get_project(project_id)
        if not project:
            raise DocumentGenerationError(f"Project {project_id} not found")

        return await _generate(project)
    except DocumentGenerationError:
        raise  # Re-raise known errors
    except Exception as e:
        logger.error(f"Unexpected error generating document: {e}", exc_info=True)
        raise DocumentGenerationError(f"Generation failed: {str(e)}")
```

**DON'T:**
```python
async def generate_document(project_id: str):
    try:
        # ... code
    except Exception:
        pass  # NEVER do this
```

### 4.2 Type Hints Standards

**Required for:**
- All function parameters
- All return types
- Class attributes

```python
# Good
async def create_project(
    name: str,
    user_id: UUID,
    project_type: str = "web"
) -> Project:
    ...

# Bad
async def create_project(name, user_id, project_type="web"):
    ...
```

### 4.3 API Response Standards

All endpoints should return consistent responses:

```python
# Success
{
    "success": true,
    "data": { ... },
    "message": "Operation completed"
}

# Error
{
    "success": false,
    "error": {
        "code": "PROJECT_NOT_FOUND",
        "message": "Project with ID xyz not found"
    }
}
```

---

## Phase 5: Technical Debt Cleanup

### 5.1 TODO/FIXME Resolution
Current count: 29

| Priority | File | Issue |
|----------|------|-------|
| HIGH | `coder_agent.py` | 5 TODOs |
| HIGH | `document_generator_agent.py` | 3 TODOs |
| MEDIUM | `writer_agent.py` | 2 TODOs |
| MEDIUM | `bolt_instant_agent.py` | 2 TODOs |

**Target**: Resolve all HIGH priority by Week 2, all by Week 4.

### 5.2 Hardcoded Values Audit
Move to configuration:
- API endpoints
- File paths
- Template defaults
- Error messages

---

## Metrics & Monitoring

### Weekly Check
- [ ] Test coverage percentage
- [ ] Number of fix commits vs feature commits
- [ ] Open TODO/FIXME count
- [ ] CI/CD pass rate

### Success Criteria
| Metric | Current | Target |
|--------|---------|--------|
| Test Coverage | 5% | 60% |
| Fix Commit Rate | 60% | <20% |
| CI Pass Rate | N/A | >95% |
| TODO Count | 29 | 0 |
| Silent Exceptions | 101 | 0 |

---

## Action Items by Role

### Developer Daily
1. Run tests before committing
2. Write test for any new code
3. Never use bare `except:` or `except Exception: pass`
4. Add type hints to new functions

### Code Review Checklist
- [ ] Tests included for new code?
- [ ] No silent exception handling?
- [ ] Type hints present?
- [ ] No hardcoded values?
- [ ] Error responses consistent?

---

## Getting Started

```bash
# 1. Install pre-commit hooks
cd BharatBuild_AI
pip install pre-commit
pre-commit install

# 2. Run existing tests
cd backend
pytest tests/ -v

# 3. Check coverage
pytest tests/ --cov=app --cov-report=html

# 4. Run type checks
mypy app/ --ignore-missing-imports
```

---

*Last Updated: December 2024*
*Owner: Development Team*
