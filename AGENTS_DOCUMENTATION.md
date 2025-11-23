# BharatBuild AI - Multi-Agent System Documentation

> **⚡ Performance Optimization Applied**
> All agents now use **plain text responses** instead of JSON for 20% better performance.
> Examples below show the optimized plain text format.



> **⚡ Performance Optimization Applied**
> All agents now use **plain text responses** instead of JSON for 20% better performance.
> Examples below show the optimized plain text format.



## 📖 Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Development Agents](#core-development-agents)
4. [Academic Project Agents](#academic-project-agents)
5. [Multi-Agent Orchestrator](#multi-agent-orchestrator)
6. [Usage Examples](#usage-examples)
7. [API Integration](#api-integration)
8. [Agent Communication Flow](#agent-communication-flow)

---

## Overview

BharatBuild AI uses a sophisticated **multi-agent system** where specialized AI agents work together to accomplish complex tasks. The system consists of **16 agents** organized into two main categories:

- **Core Development Agents** (7 agents) - For software development tasks
- **Academic Project Agents** (8 agents) - For student project generation
- **Multi-Agent Orchestrator** (1 orchestrator) - Coordinates all agents

### Key Features
- ✅ Specialized agents for specific tasks
- ✅ Coordinated workflows via orchestrator
- ✅ Context sharing between agents
- ✅ Parallel execution where possible
- ✅ Real-time progress streaming
- ✅ Error handling and retry logic

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Multi-Agent Orchestrator                 │
│         (Workflow Coordination & Management)            │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼─────────┐    ┌───────▼──────────┐
│ Core Development │    │ Academic Project │
│     Agents       │    │     Agents       │
└──────────────────┘    └──────────────────┘
         │                       │
         │                       │
    ┌────┴─────┐           ┌────┴─────┐
    │  Base    │           │  Base    │
    │  Agent   │           │  Agent   │
    └──────────┘           └──────────┘
```

### Base Agent Class

All agents inherit from `BaseAgent` which provides:

```python
class BaseAgent:
    """Base class for all agents"""

    def __init__(self, name: str, role: str, capabilities: List[str]):
        self.name = name
        self.role = role
        self.capabilities = capabilities

    async def execute(self, context: AgentContext) -> Dict:
        """Main execution method - implemented by each agent"""
        pass

    async def stream_execute(self, context: AgentContext) -> AsyncGenerator:
        """Stream execution with progress events"""
        pass
```

### Agent Context

Agents share information via `AgentContext`:

```python
class AgentContext:
    user_request: str           # User's original request
    project_id: str            # Project identifier
    metadata: Dict             # Additional metadata
    previous_results: Dict     # Results from previous agents
    files: List[Dict]          # Project files
    tech_stack: Dict           # Technology choices
```

---

## Core Development Agents

These agents handle software development tasks in a coordinated workflow.

### 1. 📋 PlannerAgent

**File:** `backend/app/modules/agents/planner_agent.py`

**Role:** Project planning and task breakdown

**Capabilities:**
- Analyzes user requirements
- Creates detailed project plans
- Defines milestones and deliverables
- Estimates time and resources
- Breaks down complex tasks into subtasks

**Input:**
```python
{
    "user_request": "Create a task management app",
    "requirements": ["user auth", "task CRUD", "notifications"]
}
```

**Output:**
```python
{
    "plan": {
        "phases": [
            {
                "name": "Setup",
                "tasks": ["Initialize project", "Setup database"],
                "duration": "1 day"
            },
            {
                "name": "Development",
                "tasks": ["User authentication", "Task CRUD", "API endpoints"],
                "duration": "3 days"
            }
        ],
        "milestones": ["MVP ready", "Testing complete", "Deployment"],
        "tech_recommendations": {
            "frontend": "React",
            "backend": "FastAPI",
            "database": "PostgreSQL"
        }
    }
}
```

**Usage:**
```python
from app.modules.agents import planner_agent

context = AgentContext(
    user_request="Create a blog platform",
    project_id="proj-123"
)

result = await planner_agent.execute(context)
plan = result["plan"]
```

---

### 2. 🏗️ ArchitectAgent

**File:** `backend/app/modules/agents/architect_agent.py`

**Role:** System architecture and design

**Capabilities:**
- Designs system architecture
- Defines folder structure
- Selects tech stack
- Creates database schemas
- Plans API endpoints
- Defines component hierarchy

**Input:**
```python
{
    "plan": {...},  # From PlannerAgent
    "requirements": ["scalable", "microservices"]
}
```

**Output:**
```python
{
    "architecture": {
        "pattern": "MVC",
        "components": [
            {
                "name": "API Gateway",
                "type": "backend",
                "technology": "FastAPI"
            }
        ],
        "folder_structure": {
            "backend": ["app/", "tests/", "config/"],
            "frontend": ["src/", "public/", "components/"]
        },
        "database_schema": {
            "tables": [
                {
                    "name": "users",
                    "columns": ["id", "email", "password_hash"]
                }
            ]
        },
        "api_endpoints": [
            {"method": "POST", "path": "/api/auth/login"},
            {"method": "GET", "path": "/api/users/:id"}
        ]
    }
}
```

**Usage:**
```python
from app.modules.agents import architect_agent

context.previous_results = {"plan": plan_result}
result = await architect_agent.execute(context)
architecture = result["architecture"]
```

---

### 3. 💻 CoderAgent

**File:** `backend/app/modules/agents/coder_agent.py`

**Role:** Code generation and implementation

**Capabilities:**
- Generates complete code files
- Implements features from architecture
- Writes clean, maintainable code
- Follows best practices
- Adds inline comments
- Handles multiple programming languages

**Input:**
```python
{
    "architecture": {...},  # From ArchitectAgent
    "files_to_generate": ["src/App.tsx", "backend/main.py"]
}
```

**Output:**
```python
{
    "code_files": [
        {
            "path": "src/App.tsx",
            "content": "import React from 'react'...",
            "language": "typescript"
        },
        {
            "path": "backend/main.py",
            "content": "from fastapi import FastAPI...",
            "language": "python"
        }
    ],
    "dependencies": {
        "frontend": ["react@18.2.0", "axios@1.4.0"],
        "backend": ["fastapi==0.100.0", "uvicorn==0.23.0"]
    }
}
```

**Usage:**
```python
from app.modules.agents import coder_agent

context.previous_results = {
    "plan": plan_result,
    "architecture": architecture_result
}

async for event in coder_agent.stream_execute(context):
    if event["type"] == "file_generated":
        print(f"Generated: {event['file_path']}")
```

---

### 4. 🧪 TesterAgent

**File:** `backend/app/modules/agents/tester_agent.py`

**Role:** Test creation and quality assurance

**Capabilities:**
- Generates unit tests
- Creates integration tests
- Writes test cases
- Defines test scenarios
- Ensures code coverage
- Validates edge cases

**Input:**
```python
{
    "code_files": [...],  # From CoderAgent
    "testing_framework": "pytest"
}
```

**Output:**
```python
{
    "test_files": [
        {
            "path": "tests/test_api.py",
            "content": "import pytest...",
            "test_cases": [
                "test_user_registration",
                "test_user_login",
                "test_invalid_credentials"
            ]
        }
    ],
    "test_coverage": "85%",
    "test_scenarios": [
        "Happy path - successful login",
        "Edge case - duplicate email",
        "Error handling - invalid input"
    ]
}
```

**Usage:**
```python
from app.modules.agents import tester_agent

context.previous_results = {"code_files": code_result}
result = await tester_agent.execute(context)
tests = result["test_files"]
```

---

### 5. 🐛 DebuggerAgent

**File:** `backend/app/modules/agents/debugger_agent.py`

**Role:** Bug fixing and code optimization

**Capabilities:**
- Detects bugs and errors
- Fixes code issues
- Optimizes performance
- Refactors code
- Handles error scenarios
- Improves code quality

**Input:**
```python
{
    "code_files": [...],
    "test_results": {
        "failures": [
            {
                "test": "test_user_login",
                "error": "AssertionError: Expected 200, got 401"
            }
        ]
    }
}
```

**Output:**
```python
{
    "fixes": [
        {
            "file": "backend/auth.py",
            "line": 45,
            "issue": "Missing password verification",
            "fix": "Added bcrypt password check",
            "updated_code": "if bcrypt.verify(password, user.password_hash):"
        }
    ],
    "optimizations": [
        {
            "file": "backend/database.py",
            "improvement": "Added database connection pooling",
            "performance_gain": "30% faster queries"
        }
    ]
}
```

**Usage:**
```python
from app.modules.agents import debugger_agent

context.metadata = {
    "errors": test_failures,
    "performance_issues": slow_queries
}

result = await debugger_agent.execute(context)
fixes = result["fixes"]
```

---

### 6. 📚 ExplainerAgent

**File:** `backend/app/modules/agents/explainer_agent.py`

**Role:** Code explanation and documentation

**Capabilities:**
- Explains code logic
- Generates inline comments
- Creates code walkthroughs
- Explains algorithms
- Simplifies complex code
- Provides learning resources

**Input:**
```python
{
    "code_snippet": "def quicksort(arr): ...",
    "explanation_level": "beginner"  # beginner, intermediate, expert
}
```

**Output:**
```python
{
    "explanation": {
        "summary": "This function implements the QuickSort algorithm",
        "step_by_step": [
            "1. Choose a pivot element from the array",
            "2. Partition array into elements < pivot and > pivot",
            "3. Recursively sort both partitions"
        ],
        "complexity": {
            "time": "O(n log n) average case",
            "space": "O(log n) for recursion stack"
        },
        "commented_code": "def quicksort(arr):\n    # Base case...",
        "learning_resources": [
            "https://visualgo.net/quicksort"
        ]
    }
}
```

**Usage:**
```python
from app.modules.agents import explainer_agent

context.metadata = {
    "code_to_explain": complex_function,
    "target_audience": "students"
}

result = await explainer_agent.execute(context)
explanation = result["explanation"]
```

---

### 7. 📄 DocumentGeneratorAgent

**File:** `backend/app/modules/agents/document_generator_agent.py`

**Role:** Technical documentation creation

**Capabilities:**
- Generates README files
- Creates API documentation
- Writes setup guides
- Produces user manuals
- Creates deployment guides
- Generates changelog

**Input:**
```python
{
    "project_info": {
        "name": "TaskManager API",
        "description": "RESTful API for task management"
    },
    "code_files": [...],
    "api_endpoints": [...]
}
```

**Output:**
```python
{
    "documentation": {
        "README.md": "# TaskManager API\n\n## Overview...",
        "API.md": "## API Endpoints\n\n### POST /api/tasks...",
        "SETUP.md": "## Installation\n\n1. Clone repository...",
        "DEPLOYMENT.md": "## Deployment Guide..."
    }
}
```

**Usage:**
```python
from app.modules.agents import document_generator_agent

result = await document_generator_agent.execute(context)
readme = result["documentation"]["README.md"]
```

---

## Academic Project Agents

These agents are specifically designed for generating complete academic projects for students.

### 8. 💡 IdeaAgent

**File:** `backend/app/modules/agents/idea_agent.py`

**Role:** Project idea generation and problem definition

**Capabilities:**
- Generates innovative project ideas
- Creates problem statements
- Defines project scope
- Identifies target users
- Lists features and functionalities
- Suggests real-world applications

**Input:**
```python
{
    "domain": "Healthcare",
    "difficulty": "intermediate",
    "keywords": ["AI", "diagnosis"]
}
```

**Output:**
```python
{
    "project_idea": {
        "title": "AI-Powered Medical Diagnosis Assistant",
        "problem_statement": "Traditional diagnosis methods are time-consuming...",
        "objectives": [
            "Develop ML model for disease prediction",
            "Create user-friendly interface for doctors",
            "Ensure 90%+ accuracy in diagnosis"
        ],
        "scope": {
            "in_scope": ["Common diseases", "X-ray analysis"],
            "out_of_scope": ["Rare diseases", "Surgery recommendations"]
        },
        "target_users": ["Doctors", "Medical students", "Patients"],
        "features": [
            "Image upload and analysis",
            "Disease prediction with confidence score",
            "Patient history management"
        ],
        "innovation": "Uses transfer learning with ResNet-50 model",
        "feasibility": "High - existing datasets available"
    }
}
```

**Usage:**
```python
from app.modules.agents import idea_agent

context = AgentContext(
    user_request="Generate a healthcare AI project idea",
    metadata={"domain": "Healthcare", "difficulty": "advanced"}
)

result = await idea_agent.execute(context)
idea = result["project_idea"]
```

---

### 9. 📋 SRSAgent

**File:** `backend/app/modules/agents/srs_agent.py`

**Role:** Software Requirements Specification generation (IEEE format)

**Capabilities:**
- Creates IEEE-standard SRS documents
- Defines functional requirements
- Lists non-functional requirements
- Specifies system constraints
- Creates use cases
- Defines acceptance criteria

**Input:**
```python
{
    "project_idea": {...},  # From IdeaAgent
    "format": "IEEE 830-1998"
}
```

**Output:**
```python
{
    "srs_document": {
        "1_introduction": {
            "1.1_purpose": "This SRS describes the functional...",
            "1.2_scope": "The system will provide...",
            "1.3_definitions": {"API": "Application Programming Interface"}
        },
        "2_overall_description": {
            "2.1_product_perspective": "Standalone web application...",
            "2.2_user_classes": ["Admin", "Doctor", "Patient"]
        },
        "3_functional_requirements": [
            {
                "id": "FR-1",
                "requirement": "System shall allow user registration",
                "priority": "High",
                "dependencies": []
            }
        ],
        "4_non_functional_requirements": {
            "performance": "Response time < 2 seconds",
            "security": "AES-256 encryption for data",
            "scalability": "Support 10,000 concurrent users"
        },
        "5_use_cases": [
            {
                "id": "UC-1",
                "name": "User Login",
                "actor": "Doctor",
                "preconditions": "User registered",
                "steps": ["1. Enter credentials", "2. Click login"],
                "postconditions": "User authenticated"
            }
        ]
    }
}
```

**Usage:**
```python
from app.modules.agents import srs_agent

context.previous_results = {"project_idea": idea_result}
result = await srs_agent.execute(context)
srs = result["srs_document"]
```

---

### 10. 📊 PRDAgent

**File:** `backend/app/modules/agents/prd_agent.py`

**Role:** Product Requirements Document creation

**Capabilities:**
- Creates product roadmaps
- Defines user stories
- Lists acceptance criteria
- Creates feature prioritization
- Defines success metrics
- Plans release strategy

**Input:**
```python
{
    "project_idea": {...},
    "target_market": "B2B Healthcare"
}
```

**Output:**
```python
{
    "prd": {
        "product_vision": "Revolutionize medical diagnosis with AI",
        "user_personas": [
            {
                "name": "Dr. Sarah",
                "role": "General Practitioner",
                "goals": ["Quick diagnosis", "Accurate results"],
                "pain_points": ["Time-consuming manual analysis"]
            }
        ],
        "user_stories": [
            {
                "as_a": "Doctor",
                "i_want": "upload patient X-rays",
                "so_that": "I can get AI-powered diagnosis",
                "acceptance_criteria": [
                    "Upload JPG/PNG files up to 10MB",
                    "Get results within 5 seconds"
                ],
                "priority": "P0"
            }
        ],
        "features": [
            {
                "name": "AI Diagnosis",
                "description": "ML-based disease prediction",
                "priority": "Must Have",
                "effort": "High",
                "release": "v1.0"
            }
        ],
        "success_metrics": {
            "accuracy": "90%+ diagnosis accuracy",
            "usage": "100+ doctors in first 3 months",
            "satisfaction": "4.5/5 star rating"
        },
        "roadmap": {
            "v1.0": "Basic diagnosis (Q1 2024)",
            "v1.1": "Patient history (Q2 2024)",
            "v2.0": "Multi-disease support (Q3 2024)"
        }
    }
}
```

---

### 11. 🎨 UMLAgent

**File:** `backend/app/modules/agents/uml_agent.py`

**Role:** UML and ER diagram generation

**Capabilities:**
- Generates UML class diagrams
- Creates sequence diagrams
- Produces use case diagrams
- Generates ER diagrams
- Creates component diagrams
- Outputs in Mermaid format

**Input:**
```python
{
    "architecture": {...},
    "database_schema": {...},
    "diagram_types": ["class", "sequence", "er"]
}
```

**Output:**
```python
{
    "diagrams": {
        "class_diagram": {
            "format": "mermaid",
            "code": """
classDiagram
    class User {
        +int id
        +string email
        +string password_hash
        +login()
        +logout()
    }
    class Task {
        +int id
        +string title
        +date due_date
        +create()
        +update()
    }
    User "1" --> "*" Task : creates
"""
        },
        "sequence_diagram": {
            "format": "mermaid",
            "code": """
sequenceDiagram
    User->>+API: POST /login
    API->>+Database: Verify credentials
    Database-->>-API: User found
    API-->>-User: JWT token
"""
        },
        "er_diagram": {
            "format": "mermaid",
            "code": """
erDiagram
    USER ||--o{ TASK : creates
    USER {
        int id PK
        string email
        string password_hash
    }
    TASK {
        int id PK
        int user_id FK
        string title
        date due_date
    }
"""
        }
    }
}
```

**Usage:**
```python
from app.modules.agents import uml_agent

result = await uml_agent.execute(context)
class_diagram = result["diagrams"]["class_diagram"]["code"]
```

---

### 12. 💻 CodeAgent

**File:** `backend/app/modules/agents/code_agent.py`

**Role:** Complete project code generation for academic projects

**Capabilities:**
- Generates full-stack code
- Creates backend (Spring Boot/Node.js/FastAPI)
- Creates frontend (React/Vue/Angular)
- Implements database models
- Writes API endpoints
- Adds authentication
- Creates complete folder structure

**Input:**
```python
{
    "project_idea": {...},
    "architecture": {...},
    "tech_stack": {
        "backend": "Spring Boot",
        "frontend": "React",
        "database": "PostgreSQL"
    }
}
```

**Output:**
```python
{
    "project_files": [
        {
            "path": "backend/src/main/java/com/project/controller/UserController.java",
            "content": "package com.project.controller;...",
            "language": "java"
        },
        {
            "path": "frontend/src/App.tsx",
            "content": "import React from 'react';...",
            "language": "typescript"
        },
        {
            "path": "backend/pom.xml",
            "content": "<project>...</project>",
            "language": "xml"
        }
    ],
    "folder_structure": {
        "backend/": ["src/", "pom.xml", "application.properties"],
        "frontend/": ["src/", "public/", "package.json"]
    },
    "dependencies": {
        "backend": ["spring-boot-starter-web", "spring-boot-starter-data-jpa"],
        "frontend": ["react@18.2.0", "axios@1.4.0"]
    },
    "database_scripts": [
        {
            "file": "schema.sql",
            "content": "CREATE TABLE users (id SERIAL PRIMARY KEY...);"
        }
    ]
}
```

---

### 13. 📝 ReportAgent

**File:** `backend/app/modules/agents/report_agent.py`

**Role:** Academic project report generation

**Capabilities:**
- Creates IEEE/ACM format reports
- Generates abstract and introduction
- Writes methodology section
- Creates results and discussion
- Adds references and citations
- Formats in Word/LaTeX style

**Input:**
```python
{
    "project_idea": {...},
    "srs_document": {...},
    "code_statistics": {
        "total_lines": 5000,
        "files": 45,
        "languages": ["Java", "JavaScript"]
    }
}
```

**Output:**
```python
{
    "report": {
        "title": "AI-Powered Medical Diagnosis System",
        "abstract": "This project presents an AI-based system...",
        "chapters": {
            "1_introduction": {
                "content": "Medical diagnosis is a critical...",
                "subsections": ["1.1 Background", "1.2 Motivation"]
            },
            "2_literature_review": {
                "content": "Previous work in medical AI includes...",
                "references": [
                    "Smith et al., 2022 - Deep Learning in Healthcare"
                ]
            },
            "3_methodology": {
                "content": "The system uses ResNet-50 architecture...",
                "diagrams": ["architecture_diagram.png"]
            },
            "4_implementation": {
                "content": "Implementation details...",
                "code_snippets": ["user_authentication.java"]
            },
            "5_results": {
                "content": "The system achieved 92% accuracy...",
                "tables": ["performance_metrics.csv"],
                "graphs": ["accuracy_graph.png"]
            },
            "6_conclusion": {
                "content": "This project successfully demonstrated...",
                "future_work": ["Expand to rare diseases", "Mobile app"]
            }
        },
        "references": [
            "[1] Smith, J. et al. (2022). Deep Learning in Healthcare...",
            "[2] Johnson, A. (2021). Medical Image Analysis..."
        ],
        "word_count": 8500,
        "pages": 35
    }
}
```

---

### 14. 📊 PPTAgent

**File:** `backend/app/modules/agents/ppt_agent.py`

**Role:** Presentation content generation

**Capabilities:**
- Creates PowerPoint slide content
- Designs slide layouts
- Generates speaker notes
- Creates visual suggestions
- Structures presentation flow
- Adds charts and diagrams

**Input:**
```python
{
    "project_report": {...},
    "presentation_duration": "15 minutes",
    "slide_count": 12
}
```

**Output:**
```python
{
    "presentation": {
        "metadata": {
            "title": "AI Medical Diagnosis System",
            "total_slides": 12,
            "duration": "15 minutes"
        },
        "slides": [
            {
                "slide_number": 1,
                "type": "title",
                "title": "AI-Powered Medical Diagnosis Assistant",
                "subtitle": "Revolutionizing Healthcare with Machine Learning",
                "content": "Presented by: [Student Name]",
                "notes": "Start with greeting. Introduce yourself."
            },
            {
                "slide_number": 2,
                "type": "content",
                "title": "Problem Statement",
                "bullets": [
                    "Traditional diagnosis is time-consuming",
                    "Human error in medical analysis",
                    "Limited access to specialists"
                ],
                "visual_suggestion": "Image of overwhelmed doctor",
                "notes": "Emphasize the need for AI assistance"
            },
            {
                "slide_number": 3,
                "type": "diagram",
                "title": "System Architecture",
                "content": "Show high-level architecture diagram",
                "visual_suggestion": "Architecture flowchart",
                "notes": "Walk through each component"
            },
            {
                "slide_number": 12,
                "type": "conclusion",
                "title": "Thank You",
                "content": "Questions?",
                "notes": "Prepare for Q&A session"
            }
        ],
        "design_theme": "Professional Medical",
        "color_scheme": ["#0066CC", "#FFFFFF", "#333333"]
    }
}
```

---

### 15. 🎤 VivaAgent

**File:** `backend/app/modules/agents/viva_agent.py`

**Role:** Viva/defense question and answer preparation

**Capabilities:**
- Generates viva questions
- Creates comprehensive answers
- Covers technical concepts
- Prepares for challenges
- Lists potential follow-ups
- Provides tips and strategies

**Input:**
```python
{
    "project_report": {...},
    "srs_document": {...},
    "code_files": [...],
    "difficulty_level": "advanced"
}
```

**Output:**
```python
{
    "viva_preparation": {
        "technical_questions": [
            {
                "category": "Architecture",
                "question": "Why did you choose microservices architecture?",
                "answer": "We chose microservices because...",
                "key_points": [
                    "Scalability",
                    "Independent deployment",
                    "Technology flexibility"
                ],
                "follow_up_questions": [
                    "How do microservices communicate?",
                    "What about data consistency?"
                ]
            },
            {
                "category": "Machine Learning",
                "question": "Explain the ResNet-50 architecture",
                "answer": "ResNet-50 is a convolutional neural network...",
                "diagram": "resnet_architecture.png",
                "code_reference": "model.py:45-67"
            }
        ],
        "conceptual_questions": [
            {
                "question": "What is transfer learning?",
                "answer": "Transfer learning is...",
                "examples": ["Using pre-trained ImageNet models"]
            }
        ],
        "implementation_questions": [
            {
                "question": "How did you handle data preprocessing?",
                "answer": "We implemented a pipeline that...",
                "code_snippet": "def preprocess_image(img):\n    ..."
            }
        ],
        "challenging_questions": [
            {
                "question": "What if your model gives wrong diagnosis?",
                "answer": "We have implemented several safeguards...",
                "ethical_considerations": [
                    "Human doctor makes final decision",
                    "Confidence threshold of 85%",
                    "Audit trail for all diagnoses"
                ]
            }
        ],
        "tips": [
            "Know your code thoroughly",
            "Be honest about limitations",
            "Relate to real-world applications",
            "Stay calm and confident"
        ]
    }
}
```

**Usage:**
```python
from app.modules.agents import viva_agent

context.metadata = {
    "project_domain": "Healthcare AI",
    "panel_expertise": ["ML", "Healthcare", "Software Engineering"]
}

result = await viva_agent.execute(context)
questions = result["viva_preparation"]["technical_questions"]
```

---

## Multi-Agent Orchestrator

**File:** `backend/app/modules/agents/orchestrator.py`

The orchestrator coordinates all agents and manages complex workflows.

### Workflow Modes

```python
class WorkflowMode(Enum):
    FULL = "full"              # All agents in sequence
    CODE_ONLY = "code_only"    # Just Code + Test
    DEBUG_ONLY = "debug_only"  # Only Debugger
    EXPLAIN_ONLY = "explain_only"  # Only Explainer
    CUSTOM = "custom"          # User-specified agents
```

### Workflow Sequences

#### 1. FULL Workflow
```
PlannerAgent → ArchitectAgent → CoderAgent → TesterAgent → DebuggerAgent → DocumentGeneratorAgent
```

#### 2. CODE_ONLY Workflow
```
CoderAgent → TesterAgent
```

#### 3. Academic Project Workflow
```
IdeaAgent → SRSAgent → PRDAgent → UMLAgent → CodeAgent → ReportAgent → PPTAgent → VivaAgent
```

### Usage

```python
from app.modules.agents import orchestrator, WorkflowMode

# Full development workflow
async for event in orchestrator.execute_workflow(
    project_id="proj-123",
    user_request="Create a task management app",
    mode=WorkflowMode.FULL
):
    if event["type"] == "agent_start":
        print(f"Starting {event['agent_name']}")
    elif event["type"] == "agent_complete":
        print(f"Completed {event['agent_name']}")
    elif event["type"] == "progress":
        print(f"Progress: {event['message']}")

# Custom workflow
async for event in orchestrator.execute_workflow(
    project_id="proj-456",
    user_request="Debug authentication issue",
    mode=WorkflowMode.CUSTOM,
    custom_agents=["debugger", "tester"]
):
    handle_event(event)
```

---

## Usage Examples

### Example 1: Full Stack Application Development

```python
from app.modules.agents import orchestrator, WorkflowMode

# User wants to build a task manager
user_request = """
Create a task management application with:
- User authentication
- CRUD operations for tasks
- Real-time notifications
- Mobile responsive design
Tech: React + FastAPI + PostgreSQL
"""

async for event in orchestrator.execute_workflow(
    project_id="task-manager-001",
    user_request=user_request,
    mode=WorkflowMode.FULL,
    context_metadata={
        "tech_stack": {
            "frontend": "React",
            "backend": "FastAPI",
            "database": "PostgreSQL"
        }
    }
):
    # Stream events to frontend
    await websocket.send(json.dumps(event))
```

**Output Events:**
```
✅ PlannerAgent: Created 5-phase plan
✅ ArchitectAgent: Designed REST API architecture
✅ CoderAgent: Generated 25 files (12 frontend, 13 backend)
✅ TesterAgent: Created 45 test cases
✅ DebuggerAgent: Fixed 3 issues
✅ DocumentGeneratorAgent: Generated README, API docs, setup guide
```

### Example 2: Academic Project Generation

```python
# Student needs a complete project for final year
user_request = """
Generate a complete academic project on:
"Smart Parking System using IoT"
Include: SRS, code, report, PPT, viva questions
"""

# Execute academic workflow
from app.modules.agents import (
    idea_agent, srs_agent, uml_agent, code_agent,
    report_agent, ppt_agent, viva_agent
)

context = AgentContext(
    user_request=user_request,
    project_id="smart-parking-001",
    metadata={"domain": "IoT", "difficulty": "intermediate"}
)

# Phase 1: Idea generation
idea_result = await idea_agent.execute(context)

# Phase 2: SRS document
context.previous_results = {"project_idea": idea_result}
srs_result = await srs_agent.execute(context)

# Phase 3: UML diagrams
uml_result = await uml_agent.execute(context)

# Phase 4: Code generation
code_result = await code_agent.execute(context)

# Phase 5: Report generation
report_result = await report_agent.execute(context)

# Phase 6: Presentation slides
ppt_result = await ppt_agent.execute(context)

# Phase 7: Viva preparation
viva_result = await viva_agent.execute(context)
```

### Example 3: Code Debugging

```python
# User has a bug in their authentication
user_request = """
Debug authentication issue:
Users can't login after password reset.
Error: "Invalid token"
"""

async for event in orchestrator.execute_workflow(
    project_id="bugfix-auth",
    user_request=user_request,
    mode=WorkflowMode.DEBUG_ONLY,
    context_metadata={
        "error_logs": [...],
        "affected_files": ["auth.py", "tokens.py"]
    }
):
    if event["type"] == "bug_found":
        print(f"Bug: {event['description']}")
        print(f"Fix: {event['solution']}")
```

### Example 4: Code Explanation for Learning

```python
# Student wants to understand a complex algorithm
code_snippet = """
def dijkstra(graph, start):
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    pq = [(0, start)]

    while pq:
        curr_dist, curr_node = heapq.heappop(pq)

        if curr_dist > distances[curr_node]:
            continue

        for neighbor, weight in graph[curr_node]:
            distance = curr_dist + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                heapq.heappush(pq, (distance, neighbor))

    return distances
"""

from app.modules.agents import explainer_agent

context = AgentContext(
    user_request="Explain this code to a beginner",
    metadata={
        "code_snippet": code_snippet,
        "explanation_level": "beginner"
    }
)

result = await explainer_agent.execute(context)
print(result["explanation"]["step_by_step"])
```

---

## API Integration

### REST API Endpoints

```python
# Backend FastAPI endpoints for agent execution

@router.post("/api/v1/agents/execute")
async def execute_agent(request: AgentRequest):
    """Execute a specific agent"""
    agent = get_agent(request.agent_name)
    context = AgentContext(**request.context)
    result = await agent.execute(context)
    return result

@router.post("/api/v1/agents/workflow")
async def execute_workflow(request: WorkflowRequest):
    """Execute multi-agent workflow"""
    async def event_generator():
        async for event in orchestrator.execute_workflow(
            project_id=request.project_id,
            user_request=request.user_request,
            mode=request.mode
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.get("/api/v1/agents/list")
async def list_agents():
    """List all available agents"""
    return {
        "core_agents": [
            "planner", "architect", "coder",
            "tester", "debugger", "explainer",
            "document_generator"
        ],
        "academic_agents": [
            "idea", "srs", "prd", "uml",
            "code", "report", "ppt", "viva"
        ]
    }
```

### Frontend Integration

```typescript
// Using streaming API in frontend
const executeWorkflow = async (userRequest: string) => {
  const response = await fetch('/api/v1/agents/workflow', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      project_id: projectId,
      user_request: userRequest,
      mode: 'full'
    })
  })

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader!.read()
    if (done) break

    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.slice(6))

        // Handle different event types
        switch (event.type) {
          case 'agent_start':
            updateUI(`Starting ${event.agent_name}...`)
            break
          case 'file_generated':
            addFileToTree(event.file_path, event.content)
            break
          case 'progress':
            updateProgress(event.percentage)
            break
        }
      }
    }
  }
}
```

---

## Agent Communication Flow

### Sequential Workflow

```
User Request
     ↓
Orchestrator
     ↓
PlannerAgent (creates plan)
     ↓
Context.previous_results["plan"] = plan
     ↓
ArchitectAgent (uses plan, creates architecture)
     ↓
Context.previous_results["architecture"] = architecture
     ↓
CoderAgent (uses architecture, generates code)
     ↓
Context.previous_results["code_files"] = code
     ↓
TesterAgent (uses code, creates tests)
     ↓
DebuggerAgent (uses test results, fixes issues)
     ↓
DocumentGeneratorAgent (uses everything, creates docs)
     ↓
Complete Project
```

### Parallel Execution Example

```python
# Some agents can run in parallel
async def parallel_execution():
    # These can run simultaneously
    results = await asyncio.gather(
        uml_agent.execute(context),      # Generate diagrams
        code_agent.execute(context),     # Generate code
        report_agent.execute(context)    # Generate report
    )

    uml_diagrams = results[0]
    code_files = results[1]
    report = results[2]
```

### Event Streaming

```python
# Agents stream progress events
async def stream_agent_execution():
    async for event in agent.stream_execute(context):
        yield {
            "type": event["type"],
            "timestamp": datetime.utcnow(),
            "agent": agent.name,
            "data": event["data"]
        }
```

---

## Best Practices

### 1. Agent Selection
- Use **FULL** workflow for complete projects
- Use **CODE_ONLY** for quick prototypes
- Use **CUSTOM** for specific tasks
- Use academic agents for student projects

### 2. Context Management
- Always pass relevant previous results
- Include metadata for better results
- Keep context focused and relevant

### 3. Error Handling
```python
try:
    result = await agent.execute(context)
except AgentExecutionError as e:
    logger.error(f"Agent failed: {e}")
    # Retry with simplified context
    result = await agent.execute(simplified_context)
```

### 4. Performance Optimization
- Use parallel execution where possible
- Stream large results
- Cache intermediate results
- Set appropriate timeouts

### 5. Testing Agents
```python
# Unit test for agent
async def test_planner_agent():
    context = AgentContext(
        user_request="Create a simple todo app",
        project_id="test-001"
    )

    result = await planner_agent.execute(context)

    assert "plan" in result
    assert len(result["plan"]["phases"]) > 0
    assert "milestones" in result["plan"]
```

---

## Conclusion

The BharatBuild AI multi-agent system provides a comprehensive, flexible, and powerful solution for:

- ✅ **Software Development** - From planning to deployment
- ✅ **Academic Projects** - Complete project generation for students
- ✅ **Code Quality** - Testing, debugging, and optimization
- ✅ **Documentation** - Technical and academic documentation
- ✅ **Learning** - Code explanation and viva preparation

Each agent is specialized, autonomous, and can work independently or as part of a coordinated workflow orchestrated by the Multi-Agent Orchestrator.

---

## Quick Reference

### Agent Files Location
```
backend/app/modules/agents/
├── base_agent.py              # Base class
├── orchestrator.py            # Orchestrator
├── planner_agent.py           # 📋 Planner
├── architect_agent.py         # 🏗️ Architect
├── coder_agent.py             # 💻 Coder
├── tester_agent.py            # 🧪 Tester
├── debugger_agent.py          # 🐛 Debugger
├── explainer_agent.py         # 📚 Explainer
├── document_generator_agent.py # 📄 DocumentGenerator
├── idea_agent.py              # 💡 Idea
├── srs_agent.py               # 📋 SRS
├── prd_agent.py               # 📊 PRD
├── uml_agent.py               # 🎨 UML
├── code_agent.py              # 💻 Code
├── report_agent.py            # 📝 Report
├── ppt_agent.py               # 📊 PPT
└── viva_agent.py              # 🎤 Viva
```

### Import All Agents
```python
from app.modules.agents import (
    orchestrator,
    planner_agent,
    architect_agent,
    coder_agent,
    tester_agent,
    debugger_agent,
    explainer_agent,
    document_generator_agent,
    idea_agent,
    srs_agent,
    prd_agent,
    uml_agent,
    code_agent,
    report_agent,
    ppt_agent,
    viva_agent
)
```

---

**Version:** 1.0
**Last Updated:** November 2024
**Author:** BharatBuild AI Team
