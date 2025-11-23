# AGENT 3 - Code Generator Agent - Example Output

## Overview
The Code Generator Agent takes the plan from the Planner Agent and architecture from the Architect Agent, then generates complete, production-ready code for the entire project.

## Example Request

**User Input:**
> "Build a todo app with user authentication"

**Planner Agent Output:**
```json
{
  "project_understanding": {
    "name": "Todo App with Authentication",
    "type": "Full-stack web application"
  },
  "technology_stack": {
    "frontend": "Next.js 14 with TypeScript",
    "backend": "FastAPI with Python",
    "database": "PostgreSQL"
  }
}
```

**Architect Agent Output:**
```json
{
  "database_schema": {
    "entities": [
      {"name": "User", "fields": ["id", "email", "password_hash"]},
      {"name": "Todo", "fields": ["id", "title", "completed", "user_id"]}
    ]
  },
  "api_design": {
    "endpoints": [
      {"path": "/api/auth/register", "method": "POST"},
      {"path": "/api/auth/login", "method": "POST"},
      {"path": "/api/todos", "method": "GET"},
      {"path": "/api/todos", "method": "POST"}
    ]
  }
}
```

---

## Coder Agent Output

```json
{
  "project_metadata": {
    "name": "todo-app-fullstack",
    "tech_stack": {
      "frontend": "nextjs",
      "backend": "fastapi",
      "database": "postgresql",
      "other": ["typescript", "tailwindcss", "zustand", "prisma"]
    },
    "description": "Full-stack todo application with user authentication"
  },

  "folder_structure": {
    "root": "todo-app-fullstack",
    "directories": [
      "backend/",
      "backend/app/",
      "backend/app/models/",
      "backend/app/api/",
      "backend/app/api/endpoints/",
      "backend/app/core/",
      "backend/app/services/",
      "frontend/",
      "frontend/src/",
      "frontend/src/app/",
      "frontend/src/components/",
      "frontend/src/lib/",
      "frontend/src/store/"
    ]
  },

  "files": [
    {
      "path": "backend/app/main.py",
      "content": "\"\"\"\\nMain FastAPI Application\\nEntry point for the Todo API with authentication\\n\"\"\"\\n\\nfrom fastapi import FastAPI\\nfrom fastapi.middleware.cors import CORSMiddleware\\nfrom app.core.config import settings\\nfrom app.api.router import api_router\\nfrom app.core.database import engine, Base\\n\\n# Create database tables\\nBase.metadata.create_all(bind=engine)\\n\\napp = FastAPI(\\n    title=\\\"Todo API\\\",\\n    description=\\\"RESTful API for todo management with authentication\\\",\\n    version=\\\"1.0.0\\\"\\n)\\n\\n# CORS configuration to allow frontend access\\n# In production, replace with specific origin\\napp.add_middleware(\\n    CORSMiddleware,\\n    allow_origins=[\\\"http://localhost:3000\\\"],  # Next.js dev server\\n    allow_credentials=True,\\n    allow_methods=[\\\"*\\\"],\\n    allow_headers=[\\\"*\\\"],\\n)\\n\\n# Include API routes\\napp.include_router(api_router, prefix=\\\"/api\\\")\\n\\n\\n@app.get(\\\"/\\\")\\ndef root():\\n    \\\"\\\"\\\"Health check endpoint\\\"\\\"\\\"\\n    return {\\\"status\\\": \\\"healthy\\\", \\\"service\\\": \\\"Todo API\\\"}\\n\\n\\nif __name__ == \\\"__main__\\\":\\n    import uvicorn\\n    uvicorn.run(app, host=\\\"0.0.0.0\\\", port=8000, reload=True)\\n\",
      "language": "python",
      "description": "Main FastAPI application with CORS and database initialization",
      "dependencies": ["fastapi", "uvicorn"],
      "educational_notes": "CORS middleware allows cross-origin requests from the frontend. The create_all() method automatically creates database tables based on SQLAlchemy models."
    },

    {
      "path": "backend/app/models/user.py",
      "content": "\"\"\"\\nUser Model\\nDatabase model for user authentication\\n\"\"\"\\n\\nfrom sqlalchemy import Column, Integer, String, DateTime\\nfrom sqlalchemy.orm import relationship\\nfrom datetime import datetime\\nfrom app.core.database import Base\\n\\n\\nclass User(Base):\\n    \\\"\\\"\\\"\\n    User table for authentication\\n    \\n    Stores user credentials and profile information.\\n    Password is stored as a hash using bcrypt for security.\\n    \\\"\\\"\\\"\\n    __tablename__ = \\\"users\\\"\\n\\n    id = Column(Integer, primary_key=True, index=True)\\n    email = Column(String, unique=True, index=True, nullable=False)\\n    # Never store plaintext passwords - use bcrypt hash\\n    password_hash = Column(String, nullable=False)\\n    created_at = Column(DateTime, default=datetime.utcnow)\\n    \\n    # Relationship: One user has many todos\\n    todos = relationship(\\\"Todo\\\", back_populates=\\\"owner\\\", cascade=\\\"all, delete-orphan\\\")\\n\\n    def __repr__(self):\\n        return f\\\"<User(id={self.id}, email={self.email})>\\\"\\n\",
      "language": "python",
      "description": "SQLAlchemy User model with password hashing",
      "dependencies": ["sqlalchemy"],
      "educational_notes": "The relationship() defines a one-to-many relationship. cascade='all, delete-orphan' ensures todos are deleted when user is deleted."
    },

    {
      "path": "backend/app/models/todo.py",
      "content": "\"\"\"\\nTodo Model\\nDatabase model for todo items\\n\"\"\"\\n\\nfrom sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime\\nfrom sqlalchemy.orm import relationship\\nfrom datetime import datetime\\nfrom app.core.database import Base\\n\\n\\nclass Todo(Base):\\n    \\\"\\\"\\\"\\n    Todo table\\n    \\n    Each todo belongs to a user (foreign key relationship).\\n    The 'completed' field tracks whether the task is done.\\n    \\\"\\\"\\\"\\n    __tablename__ = \\\"todos\\\"\\n\\n    id = Column(Integer, primary_key=True, index=True)\\n    title = Column(String, nullable=False)\\n    description = Column(String, nullable=True)\\n    completed = Column(Boolean, default=False)\\n    created_at = Column(DateTime, default=datetime.utcnow)\\n    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)\\n    \\n    # Foreign key to users table\\n    user_id = Column(Integer, ForeignKey(\\\"users.id\\\"), nullable=False)\\n    \\n    # Relationship: Many todos belong to one user\\n    owner = relationship(\\\"User\\\", back_populates=\\\"todos\\\")\\n\\n    def __repr__(self):\\n        return f\\\"<Todo(id={self.id}, title={self.title}, completed={self.completed})>\\\"\\n\",
      "language": "python",
      "description": "SQLAlchemy Todo model with user relationship",
      "dependencies": ["sqlalchemy"],
      "educational_notes": "ForeignKey creates a link to the users table. The back_populates parameter creates a bidirectional relationship."
    },

    {
      "path": "backend/app/core/security.py",
      "content": "\"\"\"\\nSecurity Utilities\\nPassword hashing and JWT token management\\n\"\"\"\\n\\nfrom datetime import datetime, timedelta\\nfrom typing import Optional\\nfrom jose import JWTError, jwt\\nfrom passlib.context import CryptContext\\nfrom app.core.config import settings\\n\\n# Password hashing context using bcrypt\\n# bcrypt is designed to be slow, making brute-force attacks difficult\\npwd_context = CryptContext(schemes=[\\\"bcrypt\\\"], deprecated=\\\"auto\\\")\\n\\n\\ndef hash_password(password: str) -> str:\\n    \\\"\\\"\\\"\\n    Hash a plaintext password using bcrypt\\n    \\n    Args:\\n        password: Plaintext password from user\\n    \\n    Returns:\\n        Hashed password safe for database storage\\n    \\\"\\\"\\\"\\n    return pwd_context.hash(password)\\n\\n\\ndef verify_password(plain_password: str, hashed_password: str) -> bool:\\n    \\\"\\\"\\\"\\n    Verify a password against its hash\\n    \\n    Args:\\n        plain_password: Password to check\\n        hashed_password: Hash from database\\n    \\n    Returns:\\n        True if password matches, False otherwise\\n    \\\"\\\"\\\"\\n    return pwd_context.verify(plain_password, hashed_password)\\n\\n\\ndef create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:\\n    \\\"\\\"\\\"\\n    Create a JWT access token\\n    \\n    Args:\\n        data: Payload to encode in token (usually {\\\"sub\\\": user_email})\\n        expires_delta: Token lifetime (default: 15 minutes)\\n    \\n    Returns:\\n        Encoded JWT token\\n    \\\"\\\"\\\"\\n    to_encode = data.copy()\\n    \\n    # Set expiration time\\n    if expires_delta:\\n        expire = datetime.utcnow() + expires_delta\\n    else:\\n        expire = datetime.utcnow() + timedelta(minutes=15)\\n    \\n    to_encode.update({\\\"exp\\\": expire})\\n    \\n    # Encode token with secret key\\n    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=\\\"HS256\\\")\\n    return encoded_jwt\\n\\n\\ndef verify_token(token: str) -> Optional[str]:\\n    \\\"\\\"\\\"\\n    Verify and decode a JWT token\\n    \\n    Args:\\n        token: JWT token to verify\\n    \\n    Returns:\\n        Email from token payload, or None if invalid\\n    \\\"\\\"\\\"\\n    try:\\n        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[\\\"HS256\\\"])\\n        email: str = payload.get(\\\"sub\\\")\\n        return email\\n    except JWTError:\\n        return None\\n\",
      "language": "python",
      "description": "Password hashing with bcrypt and JWT token management",
      "dependencies": ["passlib", "python-jose"],
      "educational_notes": "Never store plaintext passwords! bcrypt adds a 'salt' to each password, making rainbow table attacks ineffective. JWT tokens allow stateless authentication."
    },

    {
      "path": "backend/app/api/endpoints/auth.py",
      "content": "\"\"\"\\nAuthentication Endpoints\\nUser registration and login\\n\"\"\"\\n\\nfrom fastapi import APIRouter, Depends, HTTPException, status\\nfrom sqlalchemy.orm import Session\\nfrom pydantic import BaseModel, EmailStr\\nfrom app.core.database import get_db\\nfrom app.models.user import User\\nfrom app.core.security import hash_password, verify_password, create_access_token\\nfrom datetime import timedelta\\n\\nrouter = APIRouter(prefix=\\\"/auth\\\", tags=[\\\"Authentication\\\"])\\n\\n\\nclass UserRegister(BaseModel):\\n    \\\"\\\"\\\"Registration request model\\\"\\\"\\\"\\n    email: EmailStr  # EmailStr validates email format\\n    password: str\\n\\n\\nclass UserLogin(BaseModel):\\n    \\\"\\\"\\\"Login request model\\\"\\\"\\\"\\n    email: EmailStr\\n    password: str\\n\\n\\nclass Token(BaseModel):\\n    \\\"\\\"\\\"Token response model\\\"\\\"\\\"\\n    access_token: str\\n    token_type: str\\n\\n\\n@router.post(\\\"/register\\\", response_model=Token, status_code=status.HTTP_201_CREATED)\\ndef register(user_data: UserRegister, db: Session = Depends(get_db)):\\n    \\\"\\\"\\\"\\n    Register a new user\\n    \\n    Steps:\\n    1. Check if email already exists\\n    2. Hash the password (never store plaintext!)\\n    3. Create user in database\\n    4. Return JWT token\\n    \\\"\\\"\\\"\\n    # Check if user already exists\\n    existing_user = db.query(User).filter(User.email == user_data.email).first()\\n    if existing_user:\\n        raise HTTPException(\\n            status_code=status.HTTP_400_BAD_REQUEST,\\n            detail=\\\"Email already registered\\\"\\n        )\\n    \\n    # Hash password before storing\\n    hashed_password = hash_password(user_data.password)\\n    \\n    # Create new user\\n    new_user = User(\\n        email=user_data.email,\\n        password_hash=hashed_password\\n    )\\n    \\n    db.add(new_user)\\n    db.commit()\\n    db.refresh(new_user)  # Get the generated ID\\n    \\n    # Create access token\\n    access_token = create_access_token(\\n        data={\\\"sub\\\": new_user.email},\\n        expires_delta=timedelta(days=7)\\n    )\\n    \\n    return {\\\"access_token\\\": access_token, \\\"token_type\\\": \\\"bearer\\\"}\\n\\n\\n@router.post(\\\"/login\\\", response_model=Token)\\ndef login(credentials: UserLogin, db: Session = Depends(get_db)):\\n    \\\"\\\"\\\"\\n    Login existing user\\n    \\n    Steps:\\n    1. Find user by email\\n    2. Verify password hash\\n    3. Return JWT token if valid\\n    \\\"\\\"\\\"\\n    # Find user\\n    user = db.query(User).filter(User.email == credentials.email).first()\\n    \\n    if not user:\\n        raise HTTPException(\\n            status_code=status.HTTP_401_UNAUTHORIZED,\\n            detail=\\\"Invalid email or password\\\"\\n        )\\n    \\n    # Verify password\\n    if not verify_password(credentials.password, user.password_hash):\\n        raise HTTPException(\\n            status_code=status.HTTP_401_UNAUTHORIZED,\\n            detail=\\\"Invalid email or password\\\"\\n        )\\n    \\n    # Create access token\\n    access_token = create_access_token(\\n        data={\\\"sub\\\": user.email},\\n        expires_delta=timedelta(days=7)\\n    )\\n    \\n    return {\\\"access_token\\\": access_token, \\\"token_type\\\": \\\"bearer\\\"}\\n\",
      "language": "python",
      "description": "Registration and login endpoints with JWT authentication",
      "dependencies": ["fastapi", "pydantic"],
      "educational_notes": "EmailStr automatically validates email format. HTTPException returns proper HTTP status codes. Depends() provides dependency injection for database session."
    },

    {
      "path": "frontend/src/app/page.tsx",
      "content": "'use client'\\n\\nimport { useState, useEffect } from 'react'\\nimport { useAuthStore } from '@/store/authStore'\\nimport { useTodoStore } from '@/store/todoStore'\\nimport TodoList from '@/components/TodoList'\\nimport AddTodo from '@/components/AddTodo'\\nimport LoginForm from '@/components/LoginForm'\\n\\n/**\\n * Main Home Page Component\\n * \\n * Shows login form if not authenticated,\\n * otherwise shows todo list\\n */\\nexport default function Home() {\\n  const { user, isAuthenticated } = useAuthStore()\\n  const { todos, fetchTodos, loading } = useTodoStore()\\n\\n  // Fetch todos when user logs in\\n  useEffect(() => {\\n    if (isAuthenticated) {\\n      fetchTodos()\\n    }\\n  }, [isAuthenticated, fetchTodos])\\n\\n  if (!isAuthenticated) {\\n    return (\\n      <div className=\\\"min-h-screen bg-gray-50 flex items-center justify-center\\\">\\n        <LoginForm />\\n      </div>\\n    )\\n  }\\n\\n  return (\\n    <div className=\\\"min-h-screen bg-gray-50 py-8\\\">\\n      <div className=\\\"max-w-2xl mx-auto px-4\\\">\\n        <h1 className=\\\"text-3xl font-bold text-gray-900 mb-8\\\">\\n          My Todos\\n        </h1>\\n        \\n        <AddTodo />\\n        \\n        {loading ? (\\n          <div className=\\\"text-center py-8\\\">\\n            <div className=\\\"animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto\\\"></div>\\n          </div>\\n        ) : (\\n          <TodoList todos={todos} />\\n        )}\\n      </div>\\n    </div>\\n  )\\n}\\n\",
      "language": "typescript",
      "description": "Next.js home page with authentication check and todo list",
      "dependencies": ["react", "next"],
      "educational_notes": "useEffect runs when dependencies change. The empty dependency array [] would run only on mount, but [isAuthenticated] runs when auth state changes."
    },

    {
      "path": "frontend/src/store/authStore.ts",
      "content": "/**\\n * Authentication Store\\n * Manages user authentication state using Zustand\\n */\\n\\nimport { create } from 'zustand'\\nimport { persist } from 'zustand/middleware'\\n\\ninterface User {\\n  email: string\\n}\\n\\ninterface AuthState {\\n  user: User | null\\n  token: string | null\\n  isAuthenticated: boolean\\n  login: (email: string, password: string) => Promise<void>\\n  register: (email: string, password: string) => Promise<void>\\n  logout: () => void\\n}\\n\\n/**\\n * Zustand store with persistence\\n * \\n * The persist middleware saves auth state to localStorage,\\n * so users stay logged in after refresh\\n */\\nexport const useAuthStore = create<AuthState>()(\\n  persist(\\n    (set) => ({\\n      user: null,\\n      token: null,\\n      isAuthenticated: false,\\n\\n      login: async (email: string, password: string) => {\\n        try {\\n          const response = await fetch('http://localhost:8000/api/auth/login', {\\n            method: 'POST',\\n            headers: { 'Content-Type': 'application/json' },\\n            body: JSON.stringify({ email, password })\\n          })\\n\\n          if (!response.ok) {\\n            throw new Error('Login failed')\\n          }\\n\\n          const data = await response.json()\\n          \\n          set({\\n            user: { email },\\n            token: data.access_token,\\n            isAuthenticated: true\\n          })\\n        } catch (error) {\\n          console.error('Login error:', error)\\n          throw error\\n        }\\n      },\\n\\n      register: async (email: string, password: string) => {\\n        try {\\n          const response = await fetch('http://localhost:8000/api/auth/register', {\\n            method: 'POST',\\n            headers: { 'Content-Type': 'application/json' },\\n            body: JSON.stringify({ email, password })\\n          })\\n\\n          if (!response.ok) {\\n            throw new Error('Registration failed')\\n          }\\n\\n          const data = await response.json()\\n          \\n          set({\\n            user: { email },\\n            token: data.access_token,\\n            isAuthenticated: true\\n          })\\n        } catch (error) {\\n          console.error('Registration error:', error)\\n          throw error\\n        }\\n      },\\n\\n      logout: () => {\\n        set({\\n          user: null,\\n          token: null,\\n          isAuthenticated: false\\n        })\\n      }\\n    }),\\n    {\\n      name: 'auth-storage' // localStorage key\\n    }\\n  )\\n)\\n\",
      "language": "typescript",
      "description": "Zustand store for authentication state management",
      "dependencies": ["zustand"],
      "educational_notes": "Zustand is simpler than Redux. The persist middleware automatically syncs state to localStorage. set() updates the store and triggers re-renders."
    }
  ],

  "configuration_files": [
    {
      "path": "backend/requirements.txt",
      "content": "fastapi==0.104.1\\nuvicorn[standard]==0.24.0\\nsqlalchemy==2.0.23\\npsycopg2-binary==2.9.9\\npydantic==2.5.0\\npython-jose[cryptography]==3.3.0\\npasslib[bcrypt]==1.7.4\\npython-multipart==0.0.6\\n",
      "description": "Python dependencies for FastAPI backend"
    },
    {
      "path": "frontend/package.json",
      "content": "{\\n  \\\"name\\\": \\\"todo-frontend\\\",\\n  \\\"version\\\": \\\"0.1.0\\\",\\n  \\\"private\\\": true,\\n  \\\"scripts\\\": {\\n    \\\"dev\\\": \\\"next dev\\\",\\n    \\\"build\\\": \\\"next build\\\",\\n    \\\"start\\\": \\\"next start\\\",\\n    \\\"lint\\\": \\\"next lint\\\"\\n  },\\n  \\\"dependencies\\\": {\\n    \\\"react\\\": \\\"^18.2.0\\\",\\n    \\\"react-dom\\\": \\\"^18.2.0\\\",\\n    \\\"next\\\": \\\"14.0.3\\\",\\n    \\\"zustand\\\": \\\"^4.4.7\\\",\\n    \\\"tailwindcss\\\": \\\"^3.3.5\\\"\\n  },\\n  \\\"devDependencies\\\": {\\n    \\\"typescript\\\": \\\"^5.3.2\\\",\\n    \\\"@types/node\\\": \\\"^20.9.0\\\",\\n    \\\"@types/react\\\": \\\"^18.2.37\\\",\\n    \\\"@types/react-dom\\\": \\\"^18.2.15\\\",\\n    \\\"autoprefixer\\\": \\\"^10.4.16\\\",\\n    \\\"postcss\\\": \\\"^8.4.31\\\"\\n  }\\n}\\n\",
      "description": "Node.js dependencies and scripts"
    },
    {
      "path": "backend/.env.example",
      "content": "# Database\\nDATABASE_URL=postgresql://user:password@localhost:5432/todo_db\\n\\n# Security\\nSECRET_KEY=your-secret-key-here-change-in-production\\nALGORITHM=HS256\\nACCESS_TOKEN_EXPIRE_MINUTES=10080\\n\\n# Server\\nBACKEND_HOST=0.0.0.0\\nBACKEND_PORT=8000\\n",
      "description": "Environment variables template (copy to .env)"
    },
    {
      "path": ".gitignore",
      "content": "# Python\\n__pycache__/\\n*.py[cod]\\n*$py.class\\n*.so\\n.Python\\nvenv/\\nenv/\\n.env\\n\\n# Node\\nnode_modules/\\n.next/\\nout/\\nbuild/\\n\\n# IDE\\n.vscode/\\n.idea/\\n*.swp\\n*.swo\\n\\n# Database\\n*.db\\n*.sqlite\\n\\n# Logs\\n*.log\\n",
      "description": "Git ignore file for Python and Node.js"
    }
  ],

  "setup_instructions": {
    "prerequisites": [
      "Install Python 3.10+",
      "Install Node.js 18+",
      "Install PostgreSQL 14+"
    ],
    "database": [
      "Create PostgreSQL database: createdb todo_db",
      "Update DATABASE_URL in backend/.env"
    ],
    "backend": [
      "cd backend",
      "python -m venv venv",
      "source venv/bin/activate  # On Windows: venv\\\\Scripts\\\\activate",
      "pip install -r requirements.txt",
      "cp .env.example .env",
      "Edit .env with your database credentials",
      "python -m uvicorn app.main:app --reload"
    ],
    "frontend": [
      "cd frontend",
      "npm install",
      "npm run dev"
    ],
    "access": [
      "Frontend: http://localhost:3000",
      "Backend API: http://localhost:8000",
      "API Docs: http://localhost:8000/docs"
    ]
  },

  "implementation_notes": {
    "security": [
      "Passwords hashed with bcrypt (never stored plaintext)",
      "JWT tokens for stateless authentication",
      "CORS configured for localhost (update for production)",
      "Email validation with Pydantic EmailStr",
      "SQL injection prevented by SQLAlchemy ORM"
    ],
    "best_practices": [
      "Clean code with type hints",
      "Comprehensive error handling",
      "Educational comments throughout",
      "RESTful API design",
      "Component-based frontend architecture",
      "State management with Zustand",
      "Database relationships properly defined"
    ],
    "learning_points": [
      "Authentication flow: register → hash password → store → login → verify → JWT",
      "Database relationships: User (1) → Todos (many)",
      "React hooks: useState for local state, useEffect for side effects",
      "API communication: fetch() with async/await",
      "TypeScript for type safety",
      "Tailwind CSS for styling"
    ],
    "future_improvements": [
      "Add refresh tokens for better security",
      "Implement password reset via email",
      "Add todo categories/tags",
      "Add due dates and reminders",
      "Implement real-time updates with WebSockets",
      "Add unit and integration tests",
      "Deploy to production (Vercel + Railway/Render)"
    ]
  }
}
```

---

## Key Features of the Code Generator Agent

### 1. **Complete File Generation**
- Generates ALL files needed, not just skeletons
- Includes backend models, API routes, frontend components
- Configuration files (package.json, requirements.txt, .env)
- Git ignore files

### 2. **Educational Comments**
```python
# Hash password before storing (never store plaintext!)
hashed_password = hash_password(user_data.password)
```

Every critical section has comments explaining:
- **WHY** the code works this way
- **Security considerations**
- **Learning points for students**

### 3. **Security Best Practices**
- Password hashing with bcrypt
- JWT token authentication
- Input validation with Pydantic
- SQL injection prevention
- CORS configuration

### 4. **Production-Ready Code**
- Proper error handling (try-catch blocks)
- Type hints and TypeScript
- Database relationships
- Loading states in UI
- Proper HTTP status codes

### 5. **Multiple Tech Stack Support**
The agent can generate:
- **Frontend**: React, Next.js, Vue, Angular
- **Backend**: FastAPI, Express, Spring Boot, Django
- **Database**: PostgreSQL, MongoDB, MySQL
- **Languages**: Python, TypeScript, JavaScript, Java, Go

### 6. **Auto-Correction**
If validation fails (missing files, placeholders, syntax errors), the agent:
1. Detects the issue
2. Calls Claude again with error context
3. Generates corrected code
4. Validates again

### 7. **Integration with File Manager**
All generated files are written to disk automatically:
```python
files_created = await self._write_files_to_disk(
    project_id="user-123-abc",
    files=code_output["files"]
)
```

---

## Usage Example

```python
from app.modules.agents import coder_agent, AgentContext

# Context from previous agents
context = AgentContext(
    user_request="Build a todo app with authentication",
    project_id="demo-001"
)

# Plan from Planner Agent
plan = {...}  # Project plan

# Architecture from Architect Agent
architecture = {...}  # System design

# Generate code
result = await coder_agent.process(
    context=context,
    plan=plan,
    architecture=architecture
)

# Result includes:
# - All generated files
# - Setup instructions
# - Implementation notes
# - Validation results
```

---

## What Gets Generated

For a full-stack todo app, the Coder Agent generates:

### Backend (Python/FastAPI)
- `main.py` - FastAPI app with CORS
- `models/user.py` - User model with relationships
- `models/todo.py` - Todo model with foreign keys
- `core/security.py` - Password hashing and JWT
- `core/database.py` - Database connection
- `core/config.py` - Settings management
- `api/endpoints/auth.py` - Register/login routes
- `api/endpoints/todos.py` - CRUD operations
- `requirements.txt` - All dependencies

### Frontend (Next.js/TypeScript)
- `app/page.tsx` - Main page component
- `components/LoginForm.tsx` - Login UI
- `components/TodoList.tsx` - Todo display
- `components/AddTodo.tsx` - Create todo
- `store/authStore.ts` - Auth state (Zustand)
- `store/todoStore.ts` - Todo state
- `lib/api.ts` - API client
- `package.json` - Dependencies
- `tailwind.config.js` - Styling config

### Configuration
- `.env.example` - Environment variables
- `.gitignore` - Git exclusions
- `README.md` - Setup instructions

**Total**: 20+ files with complete implementations!

---

## Next Steps

After the Coder Agent, we need:

1. **AGENT 4 - Tester Agent**: Generates and runs tests
2. **AGENT 5 - Debugger Agent**: Fixes runtime errors
3. **AGENT 6 - Explainer Agent**: Documents code

Would you like me to proceed with building these agents?
