"""
Multi-File Project Training Data Generator
Generates comprehensive training examples for complete project generation

This creates training data for:
1. Full-stack projects with 10-20+ files
2. Architecture design
3. Database schema design
4. Multi-component applications
5. Complete folder structures
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from itertools import product


# ============================================================================
# PROJECT TEMPLATES - Full Multi-File Projects
# ============================================================================

FULL_STACK_PROJECTS = {
    "react_fastapi": {
        "name": "React + FastAPI Full Stack",
        "description": "Complete full-stack application with React frontend and FastAPI backend",
        "prompts": [
            "Create a complete {domain} application with React frontend and FastAPI backend",
            "Build a full-stack {domain} system using React, TypeScript, Tailwind CSS, FastAPI, and PostgreSQL",
            "Generate a complete {domain} project with authentication, CRUD operations, and dashboard",
        ],
    },
    "nextjs_fastapi": {
        "name": "Next.js + FastAPI Full Stack",
        "description": "Server-side rendered application with Next.js and FastAPI",
        "prompts": [
            "Create a complete {domain} application with Next.js frontend and FastAPI backend",
            "Build a full-stack {domain} system using Next.js 14, TypeScript, and FastAPI",
        ],
    },
    "vue_django": {
        "name": "Vue.js + Django Full Stack",
        "description": "Complete application with Vue.js frontend and Django REST backend",
        "prompts": [
            "Create a complete {domain} application with Vue.js frontend and Django backend",
            "Build a full-stack {domain} system using Vue 3, TypeScript, and Django REST Framework",
        ],
    },
    "angular_spring": {
        "name": "Angular + Spring Boot Full Stack",
        "description": "Enterprise application with Angular and Spring Boot",
        "prompts": [
            "Create a complete {domain} application with Angular frontend and Spring Boot backend",
            "Build an enterprise {domain} system using Angular, TypeScript, and Spring Boot with JPA",
        ],
    },
    "flutter_fastapi": {
        "name": "Flutter + FastAPI Mobile App",
        "description": "Cross-platform mobile app with Flutter and FastAPI backend",
        "prompts": [
            "Create a complete {domain} mobile app with Flutter and FastAPI backend",
            "Build a cross-platform {domain} application using Flutter, Dart, and FastAPI",
        ],
    },
}

DOMAINS = [
    ("e-commerce", "E-Commerce Platform", ["Product", "Category", "Cart", "Order", "Payment", "Review"]),
    ("task-management", "Task Management System", ["Project", "Task", "User", "Team", "Comment", "Attachment"]),
    ("blog", "Blog Platform", ["Post", "Category", "Tag", "Comment", "Author", "Like"]),
    ("inventory", "Inventory Management", ["Product", "Warehouse", "Stock", "Supplier", "PurchaseOrder", "Transfer"]),
    ("crm", "Customer Relationship Management", ["Contact", "Company", "Deal", "Activity", "Note", "Pipeline"]),
    ("booking", "Appointment Booking System", ["Service", "Provider", "Appointment", "Customer", "Schedule", "Payment"]),
    ("lms", "Learning Management System", ["Course", "Module", "Lesson", "Quiz", "Student", "Enrollment"]),
    ("social-media", "Social Media Platform", ["User", "Post", "Comment", "Like", "Follow", "Message"]),
    ("restaurant", "Restaurant Management", ["Menu", "MenuItem", "Order", "Table", "Reservation", "Staff"]),
    ("hr", "HR Management System", ["Employee", "Department", "Leave", "Attendance", "Payroll", "Performance"]),
]


def generate_react_fastapi_project(domain: str, domain_name: str, entities: List[str]) -> str:
    """Generate a complete React + FastAPI project structure"""

    primary_entity = entities[0]
    secondary_entity = entities[1] if len(entities) > 1 else entities[0]

    return f'''I'll create a complete {domain_name} with React frontend and FastAPI backend.

## Project Structure

```
{domain}-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── {primary_entity.lower()}.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── {primary_entity.lower()}.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       └── {primary_entity.lower()}s.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── {primary_entity.lower()}_service.py
│   ├── alembic/
│   │   └── versions/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   └── {primary_entity.lower()}s/
│   │   │       ├── page.tsx
│   │   │       └── [id]/
│   │   │           └── page.tsx
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   └── Table.tsx
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Footer.tsx
│   │   │   └── {primary_entity.lower()}/
│   │   │       ├── {primary_entity}List.tsx
│   │   │       ├── {primary_entity}Form.tsx
│   │   │       └── {primary_entity}Card.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   └── use{primary_entity}s.ts
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── utils.ts
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   ├── tailwind.config.js
│   └── tsconfig.json
├── docker-compose.yml
└── README.md
```

## Backend Files

### backend/app/main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import auth, {primary_entity.lower()}s

app = FastAPI(
    title="{domain_name} API",
    description="API for {domain_name}",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router({primary_entity.lower()}s.router, prefix="/api/{primary_entity.lower()}s", tags=["{primary_entity}s"])

@app.get("/health")
async def health_check():
    return {{"status": "healthy"}}
```

### backend/app/core/config.py
```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "{domain_name}"
    SECRET_KEY: str
    DATABASE_URL: str
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

### backend/app/core/database.py
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### backend/app/core/security.py
```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({{"exp": expire}})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None
```

### backend/app/models/user.py
```python
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### backend/app/models/{primary_entity.lower()}.py
```python
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class {primary_entity}(Base):
    __tablename__ = "{primary_entity.lower()}s"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    status = Column(String(50), default="active")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", backref="{primary_entity.lower()}s")
```

### backend/app/schemas/{primary_entity.lower()}.py
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class {primary_entity}Base(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = "active"

class {primary_entity}Create({primary_entity}Base):
    pass

class {primary_entity}Update(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class {primary_entity}Response({primary_entity}Base):
    id: UUID
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class {primary_entity}ListResponse(BaseModel):
    items: list[{primary_entity}Response]
    total: int
    page: int
    limit: int
```

### backend/app/api/endpoints/{primary_entity.lower()}s.py
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.{primary_entity.lower()} import {primary_entity}
from app.schemas.{primary_entity.lower()} import (
    {primary_entity}Create,
    {primary_entity}Update,
    {primary_entity}Response,
    {primary_entity}ListResponse,
)

router = APIRouter()

@router.get("/", response_model={primary_entity}ListResponse)
async def list_{primary_entity.lower()}s(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query({primary_entity})

    if search:
        query = query.filter({primary_entity}.name.ilike(f"%{{search}}%"))

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()

    return {primary_entity}ListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )

@router.get("/{{id}}", response_model={primary_entity}Response)
async def get_{primary_entity.lower()}(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query({primary_entity}).filter({primary_entity}.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="{primary_entity} not found")
    return item

@router.post("/", response_model={primary_entity}Response, status_code=201)
async def create_{primary_entity.lower()}(
    data: {primary_entity}Create,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = {primary_entity}(**data.model_dump(), created_by=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.put("/{{id}}", response_model={primary_entity}Response)
async def update_{primary_entity.lower()}(
    id: UUID,
    data: {primary_entity}Update,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query({primary_entity}).filter({primary_entity}.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="{primary_entity} not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item

@router.delete("/{{id}}", status_code=204)
async def delete_{primary_entity.lower()}(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query({primary_entity}).filter({primary_entity}.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="{primary_entity} not found")

    db.delete(item)
    db.commit()
```

### backend/requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
```

## Frontend Files

### frontend/src/app/layout.tsx
```tsx
import type {{ Metadata }} from 'next';
import {{ Inter }} from 'next/font/google';
import './globals.css';
import Navbar from '@/components/layout/Navbar';
import Sidebar from '@/components/layout/Sidebar';

const inter = Inter({{ subsets: ['latin'] }});

export const metadata: Metadata = {{
  title: '{domain_name}',
  description: '{domain_name} Application',
}};

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode;
}}) {{
  return (
    <html lang="en">
      <body className={{inter.className}}>
        <div className="flex h-screen bg-gray-100">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <Navbar />
            <main className="flex-1 overflow-y-auto p-6">
              {{children}}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}}
```

### frontend/src/components/layout/Navbar.tsx
```tsx
'use client';

import {{ useState }} from 'react';
import {{ useAuth }} from '@/hooks/useAuth';
import Button from '@/components/ui/Button';

export default function Navbar() {{
  const {{ user, logout }} = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">
          {domain_name}
        </h1>

        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">
            {{user?.email}}
          </span>
          <Button variant="outline" size="sm" onClick={{logout}}>
            Logout
          </Button>
        </div>
      </div>
    </nav>
  );
}}
```

### frontend/src/components/layout/Sidebar.tsx
```tsx
'use client';

import Link from 'next/link';
import {{ usePathname }} from 'next/navigation';
import {{ cn }} from '@/lib/utils';

const navigation = [
  {{ name: 'Dashboard', href: '/dashboard', icon: 'HomeIcon' }},
  {{ name: '{primary_entity}s', href: '/{primary_entity.lower()}s', icon: 'ListIcon' }},
  {{ name: 'Settings', href: '/settings', icon: 'SettingsIcon' }},
];

export default function Sidebar() {{
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-900 text-white">
      <div className="p-4">
        <h2 className="text-lg font-bold">{domain_name}</h2>
      </div>

      <nav className="mt-4">
        {{navigation.map((item) => (
          <Link
            key={{item.name}}
            href={{item.href}}
            className={{cn(
              'flex items-center px-4 py-3 text-sm',
              pathname === item.href
                ? 'bg-gray-800 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            )}}
          >
            {{item.name}}
          </Link>
        ))}}
      </nav>
    </aside>
  );
}}
```

### frontend/src/components/{primary_entity.lower()}/{primary_entity}List.tsx
```tsx
'use client';

import {{ useState }} from 'react';
import {{ use{primary_entity}s }} from '@/hooks/use{primary_entity}s';
import {primary_entity}Card from './{primary_entity}Card';
import {primary_entity}Form from './{primary_entity}Form';
import Button from '@/components/ui/Button';
import Modal from '@/components/ui/Modal';
import Input from '@/components/ui/Input';

export default function {primary_entity}List() {{
  const [search, setSearch] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const {{ {primary_entity.lower()}s, isLoading, create{primary_entity}, delete{primary_entity} }} = use{primary_entity}s({{ search }});

  if (isLoading) {{
    return <div className="flex justify-center p-8">Loading...</div>;
  }}

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{primary_entity}s</h1>
        <Button onClick={{() => setIsCreateOpen(true)}}>
          Add {primary_entity}
        </Button>
      </div>

      <Input
        placeholder="Search {primary_entity.lower()}s..."
        value={{search}}
        onChange={{(e) => setSearch(e.target.value)}}
        className="max-w-md"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {{{primary_entity.lower()}s?.map((item) => (
          <{primary_entity}Card
            key={{item.id}}
            {primary_entity.lower()}={{item}}
            onDelete={{() => delete{primary_entity}(item.id)}}
          />
        ))}}
      </div>

      <Modal
        isOpen={{isCreateOpen}}
        onClose={{() => setIsCreateOpen(false)}}
        title="Create {primary_entity}"
      >
        <{primary_entity}Form
          onSubmit={{async (data) => {{
            await create{primary_entity}(data);
            setIsCreateOpen(false);
          }}}}
          onCancel={{() => setIsCreateOpen(false)}}
        />
      </Modal>
    </div>
  );
}}
```

### frontend/src/components/{primary_entity.lower()}/{primary_entity}Form.tsx
```tsx
'use client';

import {{ useForm }} from 'react-hook-form';
import {{ zodResolver }} from '@hookform/resolvers/zod';
import {{ z }} from 'zod';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

const {primary_entity.lower()}Schema = z.object({{
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  status: z.enum(['active', 'inactive']).default('active'),
}});

type {primary_entity}FormData = z.infer<typeof {primary_entity.lower()}Schema>;

interface {primary_entity}FormProps {{
  initialData?: Partial<{primary_entity}FormData>;
  onSubmit: (data: {primary_entity}FormData) => Promise<void>;
  onCancel: () => void;
}}

export default function {primary_entity}Form({{
  initialData,
  onSubmit,
  onCancel,
}}: {primary_entity}FormProps) {{
  const {{
    register,
    handleSubmit,
    formState: {{ errors, isSubmitting }},
  }} = useForm<{primary_entity}FormData>({{
    resolver: zodResolver({primary_entity.lower()}Schema),
    defaultValues: initialData,
  }});

  return (
    <form onSubmit={{handleSubmit(onSubmit)}} className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">Name</label>
        <Input {{...register('name')}} placeholder="Enter name" />
        {{errors.name && (
          <p className="text-red-500 text-sm mt-1">{{errors.name.message}}</p>
        )}}
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Description</label>
        <textarea
          {{...register('description')}}
          className="w-full px-3 py-2 border rounded-lg"
          rows={{3}}
          placeholder="Enter description"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Status</label>
        <select {{...register('status')}} className="w-full px-3 py-2 border rounded-lg">
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      <div className="flex gap-3 justify-end">
        <Button type="button" variant="outline" onClick={{onCancel}}>
          Cancel
        </Button>
        <Button type="submit" isLoading={{isSubmitting}}>
          Save
        </Button>
      </div>
    </form>
  );
}}
```

### frontend/src/hooks/use{primary_entity}s.ts
```typescript
import useSWR from 'swr';
import {{ api }} from '@/lib/api';

interface Use{primary_entity}sOptions {{
  search?: string;
  page?: number;
  limit?: number;
}}

export function use{primary_entity}s(options: Use{primary_entity}sOptions = {{}}) {{
  const {{ search, page = 1, limit = 20 }} = options;

  const queryParams = new URLSearchParams();
  queryParams.set('page', page.toString());
  queryParams.set('limit', limit.toString());
  if (search) queryParams.set('search', search);

  const {{ data, error, isLoading, mutate }} = useSWR(
    `/{primary_entity.lower()}s?${{queryParams}}`,
    api.get
  );

  const create{primary_entity} = async (data: any) => {{
    await api.post('/{primary_entity.lower()}s', data);
    mutate();
  }};

  const update{primary_entity} = async (id: string, data: any) => {{
    await api.put(`/{primary_entity.lower()}s/${{id}}`, data);
    mutate();
  }};

  const delete{primary_entity} = async (id: string) => {{
    await api.delete(`/{primary_entity.lower()}s/${{id}}`);
    mutate();
  }};

  return {{
    {primary_entity.lower()}s: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    create{primary_entity},
    update{primary_entity},
    delete{primary_entity},
  }};
}}
```

### frontend/src/lib/api.ts
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

async function request(endpoint: string, options: RequestInit = {{}}) {{
  const token = localStorage.getItem('token');

  const response = await fetch(`${{API_URL}}${{endpoint}}`, {{
    ...options,
    headers: {{
      'Content-Type': 'application/json',
      ...(token && {{ Authorization: `Bearer ${{token}}` }}),
      ...options.headers,
    }},
  }});

  if (!response.ok) {{
    const error = await response.json().catch(() => ({{}}));
    throw new Error(error.detail || 'Request failed');
  }}

  if (response.status === 204) return null;
  return response.json();
}}

export const api = {{
  get: (endpoint: string) => request(endpoint),
  post: (endpoint: string, data: any) =>
    request(endpoint, {{ method: 'POST', body: JSON.stringify(data) }}),
  put: (endpoint: string, data: any) =>
    request(endpoint, {{ method: 'PUT', body: JSON.stringify(data) }}),
  delete: (endpoint: string) =>
    request(endpoint, {{ method: 'DELETE' }}),
}};
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {domain.replace('-', '_')}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/{domain.replace('-', '_')}
      SECRET_KEY: your-secret-key-here
    depends_on:
      - db
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api
    depends_on:
      - backend

volumes:
  postgres_data:
```

This is a complete, production-ready {domain_name} with:
- FastAPI backend with authentication, CRUD operations
- PostgreSQL database with SQLAlchemy ORM
- Next.js frontend with TypeScript and Tailwind CSS
- Docker Compose for easy deployment
- Proper error handling and validation
- Responsive UI with reusable components
'''


def generate_architecture_example(domain: str, domain_name: str, entities: List[str]) -> str:
    """Generate architecture design example"""
    return f'''I'll design the architecture for a {domain_name}.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer                            │
│                         (Nginx/ALB)                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Frontend      │ │   API Gateway   │ │   Admin Panel   │
│   (Next.js)     │ │   (Kong/AWS)    │ │   (React)       │
│   Port 3000     │ │                 │ │   Port 3001     │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend Services                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Auth Service   │  {entities[0]} Service  │  Notification Service │
│  (FastAPI)      │  (FastAPI)      │  (FastAPI)              │
│  Port 8001      │  Port 8002      │  Port 8003              │
└────────┬────────┴────────┬────────┴────────┬────────────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
├──────────────────┬──────────────────┬───────────────────────────┤
│   PostgreSQL     │   Redis Cache    │   S3 Storage              │
│   (Primary DB)   │   (Sessions)     │   (Files/Media)           │
└──────────────────┴──────────────────┴───────────────────────────┘
```

## Database Schema (ER Diagram)

```mermaid
erDiagram
    User ||--o{{ {entities[0]} : creates
    User {{
        uuid id PK
        string email UK
        string password_hash
        string full_name
        boolean is_active
        datetime created_at
    }}

    {entities[0]} ||--o{{ {entities[1] if len(entities) > 1 else 'Activity'} : has
    {entities[0]} {{
        uuid id PK
        string name
        text description
        string status
        uuid created_by FK
        datetime created_at
        datetime updated_at
    }}

    {entities[1] if len(entities) > 1 else 'Activity'} {{
        uuid id PK
        uuid {entities[0].lower()}_id FK
        string type
        json data
        datetime created_at
    }}
```

## API Design

### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register new user |
| POST | /api/auth/login | Login and get token |
| POST | /api/auth/refresh | Refresh access token |
| POST | /api/auth/logout | Logout user |
| GET | /api/auth/me | Get current user |

### {entities[0]} Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/{entities[0].lower()}s | List all {entities[0].lower()}s |
| GET | /api/{entities[0].lower()}s/:id | Get {entities[0].lower()} by ID |
| POST | /api/{entities[0].lower()}s | Create new {entities[0].lower()} |
| PUT | /api/{entities[0].lower()}s/:id | Update {entities[0].lower()} |
| DELETE | /api/{entities[0].lower()}s/:id | Delete {entities[0].lower()} |

## Technology Stack

| Layer | Technology | Reason |
|-------|------------|--------|
| Frontend | Next.js 14 + TypeScript | SEO, SSR, Type safety |
| Styling | Tailwind CSS | Rapid development |
| Backend | FastAPI | High performance, async |
| Database | PostgreSQL | ACID compliance, reliability |
| Cache | Redis | Session storage, caching |
| Auth | JWT + OAuth2 | Stateless, secure |
| Storage | AWS S3 | Scalable file storage |
| Container | Docker | Consistent environments |
| CI/CD | GitHub Actions | Automated deployment |

## Security Measures

1. **Authentication**: JWT with refresh tokens
2. **Authorization**: Role-based access control (RBAC)
3. **Data Validation**: Pydantic schemas, Zod on frontend
4. **SQL Injection**: SQLAlchemy ORM (parameterized queries)
5. **XSS Protection**: React auto-escaping, CSP headers
6. **CORS**: Configured for specific origins
7. **Rate Limiting**: Redis-based rate limiting
8. **HTTPS**: TLS encryption in production

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Route53   │───▶│ CloudFront  │───▶│     ALB     │         │
│  │   (DNS)     │    │   (CDN)     │    │             │         │
│  └─────────────┘    └─────────────┘    └──────┬──────┘         │
│                                               │                 │
│                     ┌─────────────────────────┼─────────────┐   │
│                     │         ECS Cluster     │             │   │
│                     │  ┌──────────┐  ┌──────────┐           │   │
│                     │  │ Frontend │  │ Backend  │           │   │
│                     │  │ Service  │  │ Service  │           │   │
│                     │  └──────────┘  └──────────┘           │   │
│                     └───────────────────────────────────────┘   │
│                                     │                           │
│         ┌───────────────────────────┼───────────────────┐       │
│         │         VPC               │                   │       │
│         │  ┌──────────┐  ┌──────────┐  ┌──────────┐    │       │
│         │  │   RDS    │  │ ElastiC  │  │    S3    │    │       │
│         │  │ (Postgres)│  │ (Redis)  │  │ (Storage)│    │       │
│         │  └──────────┘  └──────────┘  └──────────┘    │       │
│         └───────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

This architecture provides:
- High availability with load balancing
- Scalability with containerized services
- Security with VPC and proper access controls
- Performance with caching and CDN
'''


def generate_database_schema_example(domain: str, domain_name: str, entities: List[str]) -> str:
    """Generate database schema design example"""

    schema_parts = []
    for entity in entities[:4]:  # Limit to 4 entities for clarity
        schema_parts.append(f'''
### {entity} Table
```sql
CREATE TABLE {entity.lower()}s (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_{entity.lower()}s_name ON {entity.lower()}s(name);
CREATE INDEX idx_{entity.lower()}s_status ON {entity.lower()}s(status);
CREATE INDEX idx_{entity.lower()}s_created_by ON {entity.lower()}s(created_by);
```''')

    return f'''I'll design the complete database schema for {domain_name}.

## Database Schema Design

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```
{chr(10).join(schema_parts)}

## Relationships

```mermaid
erDiagram
    users ||--o{{ {entities[0].lower()}s : creates
    {entities[0].lower()}s ||--o{{ {entities[1].lower() if len(entities) > 1 else 'activities'}s : contains
    users {{
        uuid id PK
        varchar email UK
        varchar password_hash
        varchar full_name
        varchar role
        boolean is_active
        timestamp created_at
    }}
    {entities[0].lower()}s {{
        uuid id PK
        varchar name
        text description
        varchar status
        uuid created_by FK
        timestamp created_at
    }}
```

## SQLAlchemy Models

```python
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    {entities[0].lower()}s = relationship("{entities[0]}", back_populates="owner")


class {entities[0]}(Base):
    __tablename__ = "{entities[0].lower()}s"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    status = Column(String(50), default="active", index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="{entities[0].lower()}s")
```

## Alembic Migration

```python
"""create initial tables

Revision ID: 001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('role', sa.String(50), default='user'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # {entities[0]}s table
    op.create_table(
        '{entities[0].lower()}s',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('idx_{entities[0].lower()}s_name', '{entities[0].lower()}s', ['name'])


def downgrade():
    op.drop_table('{entities[0].lower()}s')
    op.drop_table('users')
```

This database schema provides:
- UUID primary keys for security
- Proper indexing for performance
- Audit timestamps (created_at, updated_at)
- Soft delete capability with is_active
- Foreign key relationships
- Role-based access control support
'''


def create_training_example(system_prompt: str, user_prompt: str, assistant_response: str) -> Dict:
    """Create a single training example in the correct format"""
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ]
    }


def generate_multifile_training_data(output_file: Path, num_examples: int = 500):
    """Generate multi-file project training data"""

    examples = []

    system_prompts = [
        "You are an expert full-stack developer. Generate complete, production-ready multi-file projects with proper folder structure, all necessary files, and best practices.",
        "You are a senior software architect. Design and implement complete applications with multiple files, proper architecture, and production-ready code.",
        "You are an expert in building full-stack applications. Create complete project structures with frontend, backend, database schemas, and deployment configurations.",
    ]

    # Generate full project examples
    for domain, domain_name, entities in DOMAINS:
        for stack_key, stack_info in FULL_STACK_PROJECTS.items():
            for prompt_template in stack_info["prompts"]:
                user_prompt = prompt_template.format(domain=domain_name)

                # Generate appropriate response based on stack
                if "react_fastapi" in stack_key or "nextjs_fastapi" in stack_key:
                    response = generate_react_fastapi_project(domain, domain_name, entities)
                else:
                    response = generate_react_fastapi_project(domain, domain_name, entities)  # Default to React+FastAPI

                example = create_training_example(
                    random.choice(system_prompts),
                    user_prompt,
                    response
                )
                examples.append(example)

    # Generate architecture examples
    architecture_prompts = [
        "Design the system architecture for a {domain}",
        "Create the architecture diagram and API design for a {domain}",
        "Design a scalable architecture for a {domain} application",
    ]

    for domain, domain_name, entities in DOMAINS:
        for prompt_template in architecture_prompts:
            user_prompt = prompt_template.format(domain=domain_name)
            response = generate_architecture_example(domain, domain_name, entities)

            example = create_training_example(
                "You are a senior software architect. Design comprehensive system architectures with diagrams, API designs, and technology recommendations.",
                user_prompt,
                response
            )
            examples.append(example)

    # Generate database schema examples
    schema_prompts = [
        "Design the database schema for a {domain}",
        "Create the complete database design with tables, relationships, and migrations for a {domain}",
        "Design the data model and database schema for a {domain} application",
    ]

    for domain, domain_name, entities in DOMAINS:
        for prompt_template in schema_prompts:
            user_prompt = prompt_template.format(domain=domain_name)
            response = generate_database_schema_example(domain, domain_name, entities)

            example = create_training_example(
                "You are a database architect. Design comprehensive database schemas with tables, relationships, indexes, and ORM models.",
                user_prompt,
                response
            )
            examples.append(example)

    # Shuffle and limit
    random.shuffle(examples)
    examples = examples[:num_examples]

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print(f"Generated {len(examples)} multi-file project examples")
    print(f"Saved to: {output_file}")

    return len(examples)


if __name__ == "__main__":
    output_dir = Path(__file__).parent / "multifile"
    output_dir.mkdir(exist_ok=True)

    # Generate training data
    train_file = output_dir / "train.jsonl"
    num_train = generate_multifile_training_data(train_file, num_examples=500)

    # Generate eval data (smaller subset)
    eval_file = output_dir / "eval.jsonl"
    num_eval = generate_multifile_training_data(eval_file, num_examples=50)

    print(f"\nTotal: {num_train} training + {num_eval} eval examples")
