#!/usr/bin/env python3
"""
Generate 500+ Gold Samples for Qwen Fine-tuning
Claude-Style Output Format

Categories:
1. Spec -> Multi-file Implementation (150 samples)
2. Bug -> Fix with Error Logs (150 samples)
3. Add Tests + Make Tests Pass (100 samples)
4. Refactor to Best Practices (50 samples)
5. Security Patterns (50 samples)
"""

import json
import random
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

OUTPUT_DIR = Path(__file__).parent / "gold_samples"

SYSTEM_PROMPT = """You are an expert software engineer. Respond with this exact structure:

PLAN:
1) First step
2) Second step
...

FILES:
- path/to/file.py
...

PATCH:
*** Begin Patch
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -line,count +line,count @@
 context
-removed
+added
*** End Patch

COMMANDS:
- command to run
...

NOTES:
- Important notes
...

Use unified diff format. Be precise."""


# ============================================================================
# TEMPLATES FOR GENERATING VARIATIONS
# ============================================================================

# Frameworks and languages
BACKENDS = ["FastAPI", "Django", "Flask", "Express", "NestJS", "Spring Boot", "Go/Gin", "Rust/Actix"]
FRONTENDS = ["React", "Vue 3", "Angular", "Next.js", "Svelte", "React Native"]
DATABASES = ["PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite"]
AUTH_METHODS = ["JWT", "OAuth2", "Session", "API Key", "SAML"]

# Feature domains
DOMAINS = [
    "user management", "authentication", "payments", "orders", "products",
    "inventory", "notifications", "messaging", "file uploads", "search",
    "analytics", "reporting", "scheduling", "bookings", "reviews",
    "comments", "likes", "follows", "subscriptions", "billing"
]

# Bug types
BUG_TYPES = [
    ("connection_pool", "Connection pool exhausted", "Sessions not closed"),
    ("race_condition", "Race condition", "Concurrent updates without locking"),
    ("sql_injection", "SQL injection vulnerability", "String concatenation in queries"),
    ("memory_leak", "Memory leak", "Objects not garbage collected"),
    ("n_plus_one", "N+1 query problem", "Lazy loading in loops"),
    ("deadlock", "Database deadlock", "Inconsistent lock ordering"),
    ("xss", "XSS vulnerability", "Unescaped user input"),
    ("csrf", "CSRF vulnerability", "Missing CSRF tokens"),
    ("auth_bypass", "Authentication bypass", "Improper token validation"),
    ("timeout", "Request timeout", "No timeout configured"),
    ("null_pointer", "Null pointer exception", "Missing null checks"),
    ("off_by_one", "Off-by-one error", "Incorrect loop bounds"),
    ("encoding", "Character encoding issue", "UTF-8 not handled"),
    ("timezone", "Timezone bug", "Naive datetime usage"),
    ("floating_point", "Floating point precision", "Using float for money"),
]


def create_example(user_prompt: str, response: str, category: str) -> dict:
    """Create a training example."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": response}
        ],
        "category": category
    }


# ============================================================================
# 1. SPEC -> IMPLEMENTATION GENERATORS (150 samples)
# ============================================================================

def generate_crud_api(entity: str, framework: str) -> dict:
    """Generate CRUD API implementation."""
    entity_lower = entity.lower()
    entity_cap = entity.capitalize()

    prompt = f"Implement a complete CRUD REST API for {entity} using {framework} with pagination and search."

    if "FastAPI" in framework:
        response = f"""PLAN:
1) Create {entity_cap} model with SQLAlchemy
2) Define Pydantic schemas for request/response
3) Implement CRUD endpoints with pagination
4) Add search functionality
5) Create tests

FILES:
- backend/app/models/{entity_lower}.py
- backend/app/schemas/{entity_lower}.py
- backend/app/api/{entity_lower}s.py
- backend/tests/test_{entity_lower}s.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/{entity_lower}.py
@@ -0,0 +1,20 @@
+from sqlalchemy import Column, Integer, String, DateTime, Boolean
+from sqlalchemy.sql import func
+from app.db.base import Base
+
+class {entity_cap}(Base):
+    __tablename__ = "{entity_lower}s"
+
+    id = Column(Integer, primary_key=True, index=True)
+    name = Column(String(255), nullable=False, index=True)
+    description = Column(String(1000))
+    is_active = Column(Boolean, default=True)
+    created_at = Column(DateTime(timezone=True), server_default=func.now())
+    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

--- /dev/null
+++ b/backend/app/schemas/{entity_lower}.py
@@ -0,0 +1,25 @@
+from pydantic import BaseModel, Field
+from typing import Optional, List
+from datetime import datetime
+
+class {entity_cap}Base(BaseModel):
+    name: str = Field(..., min_length=1, max_length=255)
+    description: Optional[str] = Field(None, max_length=1000)
+
+class {entity_cap}Create({entity_cap}Base):
+    pass
+
+class {entity_cap}Update(BaseModel):
+    name: Optional[str] = Field(None, min_length=1, max_length=255)
+    description: Optional[str] = None
+    is_active: Optional[bool] = None
+
+class {entity_cap}Response({entity_cap}Base):
+    id: int
+    is_active: bool
+    created_at: datetime
+
+    class Config:
+        from_attributes = True
+
+class {entity_cap}List(BaseModel):
+    items: List[{entity_cap}Response]
+    total: int
+    page: int
+    pages: int

--- /dev/null
+++ b/backend/app/api/{entity_lower}s.py
@@ -0,0 +1,65 @@
+from fastapi import APIRouter, Depends, HTTPException, Query
+from sqlalchemy.orm import Session
+from sqlalchemy import or_
+from typing import Optional
+from app.db.session import get_db
+from app.models.{entity_lower} import {entity_cap}
+from app.schemas.{entity_lower} import {entity_cap}Create, {entity_cap}Update, {entity_cap}Response, {entity_cap}List
+
+router = APIRouter(prefix="/api/{entity_lower}s", tags=["{entity_cap}s"])
+
+@router.get("/", response_model={entity_cap}List)
+async def list_{entity_lower}s(
+    page: int = Query(1, ge=1),
+    per_page: int = Query(20, ge=1, le=100),
+    search: Optional[str] = None,
+    db: Session = Depends(get_db)
+):
+    query = db.query({entity_cap}).filter({entity_cap}.is_active == True)
+
+    if search:
+        query = query.filter(or_(
+            {entity_cap}.name.ilike(f"%{{search}}%"),
+            {entity_cap}.description.ilike(f"%{{search}}%")
+        ))
+
+    total = query.count()
+    items = query.offset((page - 1) * per_page).limit(per_page).all()
+
+    return {entity_cap}List(
+        items=items,
+        total=total,
+        page=page,
+        pages=(total + per_page - 1) // per_page
+    )
+
+@router.post("/", response_model={entity_cap}Response, status_code=201)
+async def create_{entity_lower}(data: {entity_cap}Create, db: Session = Depends(get_db)):
+    item = {entity_cap}(**data.dict())
+    db.add(item)
+    db.commit()
+    db.refresh(item)
+    return item
+
+@router.get("/{{id}}", response_model={entity_cap}Response)
+async def get_{entity_lower}(id: int, db: Session = Depends(get_db)):
+    item = db.query({entity_cap}).filter({entity_cap}.id == id).first()
+    if not item:
+        raise HTTPException(404, "{entity_cap} not found")
+    return item
+
+@router.put("/{{id}}", response_model={entity_cap}Response)
+async def update_{entity_lower}(id: int, data: {entity_cap}Update, db: Session = Depends(get_db)):
+    item = db.query({entity_cap}).filter({entity_cap}.id == id).first()
+    if not item:
+        raise HTTPException(404, "{entity_cap} not found")
+
+    for key, value in data.dict(exclude_unset=True).items():
+        setattr(item, key, value)
+    db.commit()
+    db.refresh(item)
+    return item
+
+@router.delete("/{{id}}", status_code=204)
+async def delete_{entity_lower}(id: int, db: Session = Depends(get_db)):
+    item = db.query({entity_cap}).filter({entity_cap}.id == id).first()
+    if not item:
+        raise HTTPException(404, "{entity_cap} not found")
+    item.is_active = False
+    db.commit()
*** End Patch

COMMANDS:
- cd backend && alembic revision --autogenerate -m "add {entity_lower}s table"
- cd backend && alembic upgrade head
- cd backend && pytest tests/test_{entity_lower}s.py -v

NOTES:
- Uses soft delete (is_active flag)
- Pagination with configurable page size
- Search on name and description fields
- Add indexes for frequently queried columns"""

    elif "Django" in framework:
        response = f"""PLAN:
1) Create {entity_cap} model with Django ORM
2) Define serializers
3) Implement ViewSet with pagination
4) Add search filter
5) Create tests

FILES:
- backend/apps/{entity_lower}s/models.py
- backend/apps/{entity_lower}s/serializers.py
- backend/apps/{entity_lower}s/views.py
- backend/apps/{entity_lower}s/tests.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/apps/{entity_lower}s/models.py
@@ -0,0 +1,15 @@
+from django.db import models
+
+class {entity_cap}(models.Model):
+    name = models.CharField(max_length=255, db_index=True)
+    description = models.TextField(blank=True)
+    is_active = models.BooleanField(default=True)
+    created_at = models.DateTimeField(auto_now_add=True)
+    updated_at = models.DateTimeField(auto_now=True)
+
+    class Meta:
+        db_table = "{entity_lower}s"
+        ordering = ["-created_at"]

--- /dev/null
+++ b/backend/apps/{entity_lower}s/serializers.py
@@ -0,0 +1,20 @@
+from rest_framework import serializers
+from .models import {entity_cap}
+
+class {entity_cap}Serializer(serializers.ModelSerializer):
+    class Meta:
+        model = {entity_cap}
+        fields = ["id", "name", "description", "is_active", "created_at"]
+        read_only_fields = ["id", "created_at"]

--- /dev/null
+++ b/backend/apps/{entity_lower}s/views.py
@@ -0,0 +1,25 @@
+from rest_framework import viewsets, filters
+from rest_framework.pagination import PageNumberPagination
+from .models import {entity_cap}
+from .serializers import {entity_cap}Serializer
+
+class StandardPagination(PageNumberPagination):
+    page_size = 20
+    page_size_query_param = "per_page"
+    max_page_size = 100
+
+class {entity_cap}ViewSet(viewsets.ModelViewSet):
+    queryset = {entity_cap}.objects.filter(is_active=True)
+    serializer_class = {entity_cap}Serializer
+    pagination_class = StandardPagination
+    filter_backends = [filters.SearchFilter]
+    search_fields = ["name", "description"]
+
+    def perform_destroy(self, instance):
+        instance.is_active = False
+        instance.save()
*** End Patch

COMMANDS:
- python manage.py makemigrations {entity_lower}s
- python manage.py migrate
- python manage.py test apps.{entity_lower}s

NOTES:
- Uses soft delete (is_active flag)
- Pagination with configurable page size
- Search on name and description fields"""

    else:  # Flask
        response = f"""PLAN:
1) Create {entity_cap} model with SQLAlchemy
2) Define marshmallow schemas
3) Implement Flask-RESTful resource
4) Add search functionality
5) Create tests

FILES:
- backend/app/models/{entity_lower}.py
- backend/app/schemas/{entity_lower}.py
- backend/app/api/{entity_lower}s.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/{entity_lower}.py
@@ -0,0 +1,15 @@
+from datetime import datetime
+from app.extensions import db
+
+class {entity_cap}(db.Model):
+    __tablename__ = "{entity_lower}s"
+
+    id = db.Column(db.Integer, primary_key=True)
+    name = db.Column(db.String(255), nullable=False, index=True)
+    description = db.Column(db.String(1000))
+    is_active = db.Column(db.Boolean, default=True)
+    created_at = db.Column(db.DateTime, default=datetime.utcnow)
+    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

--- /dev/null
+++ b/backend/app/api/{entity_lower}s.py
@@ -0,0 +1,50 @@
+from flask import Blueprint, request, jsonify
+from app.models.{entity_lower} import {entity_cap}
+from app.extensions import db
+
+bp = Blueprint("{entity_lower}s", __name__, url_prefix="/api/{entity_lower}s")
+
+@bp.route("/", methods=["GET"])
+def list_{entity_lower}s():
+    page = request.args.get("page", 1, type=int)
+    per_page = request.args.get("per_page", 20, type=int)
+    search = request.args.get("search", "")
+
+    query = {entity_cap}.query.filter_by(is_active=True)
+    if search:
+        query = query.filter(
+            db.or_(
+                {entity_cap}.name.ilike(f"%{{search}}%"),
+                {entity_cap}.description.ilike(f"%{{search}}%")
+            )
+        )
+
+    pagination = query.paginate(page=page, per_page=per_page)
+    return jsonify({{
+        "items": [item.to_dict() for item in pagination.items],
+        "total": pagination.total,
+        "page": page,
+        "pages": pagination.pages
+    }})
+
+@bp.route("/", methods=["POST"])
+def create_{entity_lower}():
+    data = request.get_json()
+    item = {entity_cap}(**data)
+    db.session.add(item)
+    db.session.commit()
+    return jsonify(item.to_dict()), 201
+
+@bp.route("/<int:id>", methods=["DELETE"])
+def delete_{entity_lower}(id):
+    item = {entity_cap}.query.get_or_404(id)
+    item.is_active = False
+    db.session.commit()
+    return "", 204
*** End Patch

COMMANDS:
- flask db migrate -m "add {entity_lower}s table"
- flask db upgrade
- pytest tests/test_{entity_lower}s.py -v

NOTES:
- Uses soft delete (is_active flag)
- Pagination with configurable page size
- Search on name and description fields"""

    return create_example(prompt, response, "spec_to_implementation")


def generate_auth_endpoint(auth_type: str, framework: str) -> dict:
    """Generate authentication endpoint."""
    prompt = f"Implement {auth_type} authentication for {framework} with login, register, and token refresh."

    response = f"""PLAN:
1) Create User model with password hashing
2) Implement token generation ({auth_type})
3) Create auth endpoints
4) Add token refresh mechanism
5) Implement logout/token invalidation

FILES:
- backend/app/models/user.py
- backend/app/core/security.py
- backend/app/api/auth.py
- backend/tests/test_auth.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/user.py
@@ -0,0 +1,30 @@
+from sqlalchemy import Column, Integer, String, Boolean, DateTime
+from sqlalchemy.sql import func
+from passlib.context import CryptContext
+from app.db.base import Base
+
+pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
+
+class User(Base):
+    __tablename__ = "users"
+
+    id = Column(Integer, primary_key=True, index=True)
+    email = Column(String, unique=True, index=True, nullable=False)
+    password_hash = Column(String, nullable=False)
+    name = Column(String(100))
+    is_active = Column(Boolean, default=True)
+    is_verified = Column(Boolean, default=False)
+    created_at = Column(DateTime(timezone=True), server_default=func.now())
+    last_login = Column(DateTime(timezone=True))
+
+    def set_password(self, password: str) -> None:
+        if len(password) < 8:
+            raise ValueError("Password must be at least 8 characters")
+        self.password_hash = pwd_context.hash(password)
+
+    def verify_password(self, password: str) -> bool:
+        return pwd_context.verify(password, self.password_hash)

--- /dev/null
+++ b/backend/app/core/security.py
@@ -0,0 +1,55 @@
+from datetime import datetime, timedelta
+from typing import Optional
+from jose import JWTError, jwt
+from fastapi import HTTPException, Depends, status
+from fastapi.security import OAuth2PasswordBearer
+from sqlalchemy.orm import Session
+from app.core.config import settings
+from app.db.session import get_db
+from app.models.user import User
+
+oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
+
+def create_access_token(user_id: int, expires_delta: timedelta = None) -> str:
+    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
+    return jwt.encode(
+        {{"sub": str(user_id), "exp": expire, "type": "access"}},
+        settings.SECRET_KEY,
+        algorithm="HS256"
+    )
+
+def create_refresh_token(user_id: int) -> str:
+    expire = datetime.utcnow() + timedelta(days=7)
+    return jwt.encode(
+        {{"sub": str(user_id), "exp": expire, "type": "refresh"}},
+        settings.SECRET_KEY,
+        algorithm="HS256"
+    )
+
+async def get_current_user(
+    token: str = Depends(oauth2_scheme),
+    db: Session = Depends(get_db)
+) -> User:
+    credentials_exception = HTTPException(
+        status_code=status.HTTP_401_UNAUTHORIZED,
+        detail="Invalid credentials",
+        headers={{"WWW-Authenticate": "Bearer"}}
+    )
+    try:
+        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
+        if payload.get("type") != "access":
+            raise credentials_exception
+        user_id = int(payload.get("sub"))
+    except (JWTError, ValueError):
+        raise credentials_exception
+
+    user = db.query(User).filter(User.id == user_id).first()
+    if not user or not user.is_active:
+        raise credentials_exception
+    return user

--- /dev/null
+++ b/backend/app/api/auth.py
@@ -0,0 +1,80 @@
+from fastapi import APIRouter, Depends, HTTPException, status
+from fastapi.security import OAuth2PasswordRequestForm
+from sqlalchemy.orm import Session
+from pydantic import BaseModel, EmailStr
+from datetime import datetime
+from jose import jwt, JWTError
+from app.db.session import get_db
+from app.models.user import User
+from app.core.security import create_access_token, create_refresh_token, get_current_user
+from app.core.config import settings
+
+router = APIRouter(prefix="/api/auth", tags=["Authentication"])
+
+class UserRegister(BaseModel):
+    email: EmailStr
+    password: str
+    name: str
+
+class TokenResponse(BaseModel):
+    access_token: str
+    refresh_token: str
+    token_type: str = "bearer"
+
+class RefreshRequest(BaseModel):
+    refresh_token: str
+
+@router.post("/register", status_code=201)
+async def register(data: UserRegister, db: Session = Depends(get_db)):
+    if db.query(User).filter(User.email == data.email).first():
+        raise HTTPException(400, "Email already registered")
+
+    user = User(email=data.email, name=data.name)
+    user.set_password(data.password)
+    db.add(user)
+    db.commit()
+    return {{"message": "User registered successfully"}}
+
+@router.post("/login", response_model=TokenResponse)
+async def login(
+    form: OAuth2PasswordRequestForm = Depends(),
+    db: Session = Depends(get_db)
+):
+    user = db.query(User).filter(User.email == form.username).first()
+    if not user or not user.verify_password(form.password):
+        raise HTTPException(401, "Invalid email or password")
+
+    if not user.is_active:
+        raise HTTPException(403, "Account is disabled")
+
+    user.last_login = datetime.utcnow()
+    db.commit()
+
+    return TokenResponse(
+        access_token=create_access_token(user.id),
+        refresh_token=create_refresh_token(user.id)
+    )
+
+@router.post("/refresh", response_model=TokenResponse)
+async def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
+    try:
+        payload = jwt.decode(data.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
+        if payload.get("type") != "refresh":
+            raise HTTPException(401, "Invalid token type")
+        user_id = int(payload.get("sub"))
+    except JWTError:
+        raise HTTPException(401, "Invalid refresh token")
+
+    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
+    if not user:
+        raise HTTPException(401, "User not found")
+
+    return TokenResponse(
+        access_token=create_access_token(user.id),
+        refresh_token=create_refresh_token(user.id)
+    )
+
+@router.get("/me")
+async def get_me(current_user: User = Depends(get_current_user)):
+    return {{"id": current_user.id, "email": current_user.email, "name": current_user.name}}
*** End Patch

COMMANDS:
- cd backend && alembic upgrade head
- cd backend && pytest tests/test_auth.py -v

NOTES:
- Passwords hashed with bcrypt
- Access tokens expire in 24 hours
- Refresh tokens expire in 7 days
- Add rate limiting for login endpoint
- Consider adding email verification"""

    return create_example(prompt, response, "spec_to_implementation")


def generate_file_upload(storage: str) -> dict:
    """Generate file upload implementation."""
    prompt = f"Implement file upload API with {storage} storage, validation, and virus scanning."

    response = f"""PLAN:
1) Create upload endpoint with size/type validation
2) Implement {storage} storage service
3) Add virus scanning placeholder
4) Create file metadata model
5) Add download endpoint

FILES:
- backend/app/api/files.py
- backend/app/services/storage.py
- backend/app/models/file.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/file.py
@@ -0,0 +1,18 @@
+from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
+from sqlalchemy.sql import func
+from app.db.base import Base
+
+class FileRecord(Base):
+    __tablename__ = "files"
+
+    id = Column(Integer, primary_key=True)
+    filename = Column(String, nullable=False)
+    storage_key = Column(String, unique=True, nullable=False)
+    content_type = Column(String, nullable=False)
+    size = Column(Integer, nullable=False)
+    user_id = Column(Integer, ForeignKey("users.id"))
+    created_at = Column(DateTime(timezone=True), server_default=func.now())

--- /dev/null
+++ b/backend/app/services/storage.py
@@ -0,0 +1,45 @@
+import boto3
+from uuid import uuid4
+from typing import BinaryIO
+from app.core.config import settings
+
+class StorageService:
+    def __init__(self):
+        self.s3 = boto3.client(
+            "s3",
+            aws_access_key_id=settings.AWS_ACCESS_KEY,
+            aws_secret_access_key=settings.AWS_SECRET_KEY,
+            region_name=settings.AWS_REGION
+        )
+        self.bucket = settings.S3_BUCKET
+
+    async def upload(self, file_obj: BinaryIO, filename: str, content_type: str) -> str:
+        key = f"uploads/{{uuid4().hex}}/{{filename}}"
+        self.s3.upload_fileobj(
+            file_obj,
+            self.bucket,
+            key,
+            ExtraArgs={{"ContentType": content_type}}
+        )
+        return key
+
+    async def download(self, key: str) -> bytes:
+        response = self.s3.get_object(Bucket=self.bucket, Key=key)
+        return response["Body"].read()
+
+    async def delete(self, key: str) -> None:
+        self.s3.delete_object(Bucket=self.bucket, Key=key)
+
+    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
+        return self.s3.generate_presigned_url(
+            "get_object",
+            Params={{"Bucket": self.bucket, "Key": key}},
+            ExpiresIn=expires_in
+        )

--- /dev/null
+++ b/backend/app/api/files.py
@@ -0,0 +1,60 @@
+from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
+from sqlalchemy.orm import Session
+from app.db.session import get_db
+from app.services.storage import StorageService
+from app.models.file import FileRecord
+from app.core.security import get_current_user
+
+router = APIRouter(prefix="/api/files", tags=["Files"])
+
+ALLOWED_TYPES = {{"image/jpeg", "image/png", "image/gif", "application/pdf"}}
+MAX_SIZE = 10 * 1024 * 1024  # 10MB
+
+async def scan_for_virus(content: bytes) -> bool:
+    # TODO: Integrate ClamAV or similar
+    return True
+
+@router.post("/upload")
+async def upload_file(
+    file: UploadFile = File(...),
+    user = Depends(get_current_user),
+    db: Session = Depends(get_db)
+):
+    if file.content_type not in ALLOWED_TYPES:
+        raise HTTPException(400, f"File type {{file.content_type}} not allowed")
+
+    content = await file.read()
+
+    if len(content) > MAX_SIZE:
+        raise HTTPException(400, f"File too large. Max: {{MAX_SIZE // 1024 // 1024}}MB")
+
+    if not await scan_for_virus(content):
+        raise HTTPException(400, "File failed security scan")
+
+    storage = StorageService()
+    file.file.seek(0)
+    key = await storage.upload(file.file, file.filename, file.content_type)
+
+    record = FileRecord(
+        filename=file.filename,
+        storage_key=key,
+        content_type=file.content_type,
+        size=len(content),
+        user_id=user.id
+    )
+    db.add(record)
+    db.commit()
+
+    return {{"id": record.id, "filename": record.filename}}
+
+@router.get("/{{file_id}}/download")
+async def download_file(file_id: int, db: Session = Depends(get_db)):
+    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
+    if not record:
+        raise HTTPException(404, "File not found")
+
+    storage = StorageService()
+    url = storage.get_presigned_url(record.storage_key)
+    return {{"download_url": url}}
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_files.py -v
- aws s3 ls s3://your-bucket/uploads/

NOTES:
- Implement actual virus scanning with ClamAV
- Consider chunked upload for large files
- Add rate limiting per user
- Store file metadata in database"""

    return create_example(prompt, response, "spec_to_implementation")


def generate_websocket_feature(feature: str) -> dict:
    """Generate WebSocket feature implementation."""
    prompt = f"Implement WebSocket {feature} with rooms, authentication, and message persistence."

    response = f"""PLAN:
1) Create WebSocket manager class
2) Implement room management
3) Add authentication via token
4) Persist messages to database
5) Handle reconnection

FILES:
- backend/app/websocket/{feature.lower().replace(' ', '_')}.py
- backend/app/models/message.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/message.py
@@ -0,0 +1,15 @@
+from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
+from sqlalchemy.sql import func
+from app.db.base import Base
+
+class Message(Base):
+    __tablename__ = "messages"
+
+    id = Column(Integer, primary_key=True)
+    room_id = Column(String, index=True, nullable=False)
+    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
+    content = Column(Text, nullable=False)
+    message_type = Column(String, default="text")
+    created_at = Column(DateTime(timezone=True), server_default=func.now())

--- /dev/null
+++ b/backend/app/websocket/{feature.lower().replace(' ', '_')}.py
@@ -0,0 +1,85 @@
+from fastapi import WebSocket, WebSocketDisconnect, Depends
+from typing import Dict, List, Set
+from datetime import datetime
+import json
+import asyncio
+from jose import jwt, JWTError
+from app.core.config import settings
+from app.db.session import SessionLocal
+from app.models.message import Message
+
+class ConnectionManager:
+    def __init__(self):
+        self.rooms: Dict[str, Set[WebSocket]] = {{}}
+        self.user_sockets: Dict[int, WebSocket] = {{}}
+        self._lock = asyncio.Lock()
+
+    async def connect(self, room_id: str, user_id: int, ws: WebSocket):
+        await ws.accept()
+        async with self._lock:
+            if room_id not in self.rooms:
+                self.rooms[room_id] = set()
+            self.rooms[room_id].add(ws)
+            self.user_sockets[user_id] = ws
+        await self.broadcast(room_id, {{"type": "join", "user_id": user_id}})
+
+    async def disconnect(self, room_id: str, user_id: int, ws: WebSocket):
+        async with self._lock:
+            if room_id in self.rooms:
+                self.rooms[room_id].discard(ws)
+            self.user_sockets.pop(user_id, None)
+        await self.broadcast(room_id, {{"type": "leave", "user_id": user_id}})
+
+    async def broadcast(self, room_id: str, message: dict, exclude: WebSocket = None):
+        if room_id not in self.rooms:
+            return
+        dead = []
+        for ws in self.rooms[room_id]:
+            if ws != exclude:
+                try:
+                    await ws.send_json(message)
+                except:
+                    dead.append(ws)
+        for ws in dead:
+            self.rooms[room_id].discard(ws)
+
+manager = ConnectionManager()
+
+async def verify_token(token: str) -> int:
+    try:
+        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
+        return int(payload.get("sub"))
+    except JWTError:
+        return None
+
+@app.websocket("/ws/{{room_id}}")
+async def websocket_endpoint(ws: WebSocket, room_id: str, token: str):
+    user_id = await verify_token(token)
+    if not user_id:
+        await ws.close(code=4001)
+        return
+
+    await manager.connect(room_id, user_id, ws)
+
+    try:
+        while True:
+            data = await ws.receive_json()
+
+            if data.get("type") == "message":
+                # Save to database
+                db = SessionLocal()
+                try:
+                    msg = Message(
+                        room_id=room_id,
+                        user_id=user_id,
+                        content=data.get("content", "")
+                    )
+                    db.add(msg)
+                    db.commit()
+
+                    await manager.broadcast(room_id, {{
+                        "type": "message",
+                        "user_id": user_id,
+                        "content": data["content"],
+                        "timestamp": datetime.utcnow().isoformat()
+                    }})
+                finally:
+                    db.close()
+
+    except WebSocketDisconnect:
+        await manager.disconnect(room_id, user_id, ws)
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_websocket.py -v
- websocat ws://localhost:8000/ws/test?token=xxx

NOTES:
- Add Redis PubSub for multi-server
- Implement typing indicators
- Add message read receipts
- Consider rate limiting messages"""

    return create_example(prompt, response, "spec_to_implementation")


def generate_background_job(job_type: str) -> dict:
    """Generate background job implementation."""
    prompt = f"Implement {job_type} background job with Celery, retry logic, and monitoring."

    response = f"""PLAN:
1) Configure Celery with Redis broker
2) Create {job_type} task with retry
3) Add task monitoring
4) Implement result handling

FILES:
- backend/app/tasks/{job_type.lower().replace(' ', '_')}.py
- backend/app/core/celery.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/core/celery.py
@@ -0,0 +1,20 @@
+from celery import Celery
+from app.core.config import settings
+
+celery_app = Celery(
+    "tasks",
+    broker=settings.REDIS_URL,
+    backend=settings.REDIS_URL,
+    include=["app.tasks"]
+)
+
+celery_app.conf.update(
+    task_serializer="json",
+    result_serializer="json",
+    accept_content=["json"],
+    timezone="UTC",
+    task_track_started=True,
+    task_time_limit=3600,
+    worker_prefetch_multiplier=1
+)

--- /dev/null
+++ b/backend/app/tasks/{job_type.lower().replace(' ', '_')}.py
@@ -0,0 +1,55 @@
+from celery import shared_task
+from celery.utils.log import get_task_logger
+import time
+
+logger = get_task_logger(__name__)
+
+@shared_task(
+    bind=True,
+    max_retries=3,
+    default_retry_delay=60,
+    autoretry_for=(Exception,),
+    retry_backoff=True
+)
+def process_{job_type.lower().replace(' ', '_')}(self, data: dict):
+    logger.info(f"Starting {job_type} task with data: {{data}}")
+
+    try:
+        # Process the job
+        result = _do_processing(data)
+
+        logger.info(f"{job_type} completed successfully")
+        return {{"status": "success", "result": result}}
+
+    except Exception as e:
+        logger.error(f"{job_type} failed: {{e}}")
+        raise self.retry(exc=e)
+
+def _do_processing(data: dict):
+    # Implement actual processing logic
+    return {{"processed": True}}
+
+@shared_task
+def cleanup_old_results():
+    # Periodic task to clean up old results
+    logger.info("Cleaning up old results")
+    # Implementation here
+
+# Usage in API:
+# from app.tasks.{job_type.lower().replace(' ', '_')} import process_{job_type.lower().replace(' ', '_')}
+# task = process_{job_type.lower().replace(' ', '_')}.delay({{"key": "value"}})
+# result = task.get(timeout=30)
*** End Patch

COMMANDS:
- celery -A app.core.celery worker --loglevel=info
- celery -A app.core.celery beat --loglevel=info
- cd backend && pytest tests/test_tasks.py -v

NOTES:
- Configure Redis for production
- Add Flower for monitoring
- Set appropriate timeouts
- Consider using task chains for complex workflows"""

    return create_example(prompt, response, "spec_to_implementation")


# ============================================================================
# 2. BUG -> FIX GENERATORS (150 samples)
# ============================================================================

def generate_bug_fix(bug_type: str, bug_name: str, bug_cause: str) -> dict:
    """Generate bug fix example."""
    prompt = f"""Fix this production error:
```
ERROR: {bug_name}
{bug_cause}
```"""

    if bug_type == "connection_pool":
        response = """PLAN:
1) Add context manager for session cleanup
2) Configure connection pool properly
3) Add pool health checks

FILES:
- backend/app/db/session.py

PATCH:
*** Begin Patch
--- a/backend/app/db/session.py
+++ b/backend/app/db/session.py
@@ -1,10 +1,30 @@
 from sqlalchemy import create_engine
-from sqlalchemy.orm import sessionmaker
+from sqlalchemy.orm import sessionmaker, Session
+from typing import Generator

-engine = create_engine(DATABASE_URL)
+engine = create_engine(
+    DATABASE_URL,
+    pool_size=20,
+    max_overflow=10,
+    pool_timeout=30,
+    pool_recycle=1800,
+    pool_pre_ping=True
+)
 SessionLocal = sessionmaker(bind=engine)

-def get_data():
-    db = SessionLocal()
-    return db.query(Model).all()
+def get_db() -> Generator[Session, None, None]:
+    db = SessionLocal()
+    try:
+        yield db
+    finally:
+        db.close()
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_db.py -v

NOTES:
- Root cause: Sessions never closed
- pool_pre_ping checks connection health
- pool_recycle prevents stale connections"""

    elif bug_type == "race_condition":
        response = """PLAN:
1) Add row-level locking
2) Use atomic UPDATE
3) Add idempotency key

FILES:
- backend/app/api/purchase.py

PATCH:
*** Begin Patch
--- a/backend/app/api/purchase.py
+++ b/backend/app/api/purchase.py
@@ -1,12 +1,30 @@
+from sqlalchemy import text
+from fastapi import Header
+
 @app.post("/purchase")
 async def purchase(
     product_id: int,
+    idempotency_key: str = Header(...),
     user=Depends(get_user),
     db=Depends(get_db)
 ):
-    product = db.query(Product).get(product_id)
-    if user.balance >= product.price:
-        user.balance -= product.price
-        db.commit()
+    # Atomic update with balance check
+    result = db.execute(
+        text('''
+            UPDATE users SET balance = balance - :price
+            WHERE id = :user_id AND balance >= :price
+            RETURNING balance
+        '''),
+        {"user_id": user.id, "price": product.price}
+    ).first()
+
+    if not result:
+        raise HTTPException(400, "Insufficient balance")
+
+    db.commit()
+    return {"success": True}
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_concurrent.py -v

NOTES:
- Atomic UPDATE prevents race condition
- Add idempotency key for duplicates"""

    elif bug_type == "sql_injection":
        response = """PLAN:
1) Use parameterized queries
2) Add input validation
3) Use ORM instead of raw SQL

FILES:
- backend/app/api/search.py

PATCH:
*** Begin Patch
--- a/backend/app/api/search.py
+++ b/backend/app/api/search.py
@@ -1,6 +1,15 @@
+from fastapi import Query
+from sqlalchemy.orm import Session
+
 @app.get("/search")
-def search(query: str, db=Depends(get_db)):
-    sql = f"SELECT * FROM products WHERE name LIKE '%{query}%'"
-    return db.execute(sql).fetchall()
+def search(
+    query: str = Query(..., min_length=1, max_length=100),
+    db: Session = Depends(get_db)
+):
+    # ORM automatically parameterizes
+    return db.query(Product).filter(
+        Product.name.ilike(f"%{query}%")
+    ).limit(100).all()
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_security.py -v

NOTES:
- Never concatenate user input into SQL
- ORM provides automatic escaping
- Always validate input length"""

    elif bug_type == "memory_leak":
        response = """PLAN:
1) Remove global accumulator
2) Use streaming/chunked processing
3) Add cleanup on disconnect

FILES:
- backend/app/api/upload.py

PATCH:
*** Begin Patch
--- a/backend/app/api/upload.py
+++ b/backend/app/api/upload.py
@@ -1,12 +1,25 @@
-uploaded_files = []  # Memory leak!
+from fastapi import BackgroundTasks

 @app.post("/upload")
-async def upload(file: UploadFile):
-    content = await file.read()
-    uploaded_files.append(content)  # Never cleaned up
-    return {"size": len(content)}
+async def upload(
+    file: UploadFile,
+    background_tasks: BackgroundTasks
+):
+    # Stream to storage instead of memory
+    storage = StorageService()
+    key = await storage.upload_stream(file.file, file.filename)
+
+    # Process in background
+    background_tasks.add_task(process_file, key)
+
+    return {"key": key}
*** End Patch

COMMANDS:
- docker stats backend --no-stream

NOTES:
- Never store file contents in global variables
- Use streaming for large files
- Process in background tasks"""

    elif bug_type == "n_plus_one":
        response = """PLAN:
1) Use eager loading with joinedload
2) Batch related queries
3) Add query monitoring

FILES:
- backend/app/api/posts.py

PATCH:
*** Begin Patch
--- a/backend/app/api/posts.py
+++ b/backend/app/api/posts.py
@@ -1,6 +1,12 @@
+from sqlalchemy.orm import joinedload, selectinload
+
 @app.get("/posts")
 def get_posts(db=Depends(get_db)):
-    posts = db.query(Post).all()
-    # N+1: Each post.author triggers new query
-    return [{"title": p.title, "author": p.author.name} for p in posts]
+    posts = db.query(Post).options(
+        joinedload(Post.author),
+        selectinload(Post.comments)
+    ).all()
+
+    return [{"title": p.title, "author": p.author.name} for p in posts]
*** End Patch

COMMANDS:
- SQLALCHEMY_ECHO=1 pytest tests/test_posts.py -v

NOTES:
- joinedload for many-to-one (author)
- selectinload for one-to-many (comments)
- Monitor queries with SQLALCHEMY_ECHO"""

    elif bug_type == "xss":
        response = """PLAN:
1) Sanitize HTML input
2) Escape output
3) Set Content-Security-Policy

FILES:
- backend/app/services/sanitizer.py
- backend/app/api/comments.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/services/sanitizer.py
@@ -0,0 +1,15 @@
+import bleach
+
+ALLOWED_TAGS = ["b", "i", "em", "strong", "a"]
+ALLOWED_ATTRS = {"a": ["href"]}
+
+def sanitize_html(content: str) -> str:
+    return bleach.clean(
+        content,
+        tags=ALLOWED_TAGS,
+        attributes=ALLOWED_ATTRS,
+        strip=True
+    )

--- a/backend/app/api/comments.py
+++ b/backend/app/api/comments.py
@@ -1,8 +1,12 @@
+from app.services.sanitizer import sanitize_html
+
 @app.post("/comments")
 async def create_comment(content: str, db=Depends(get_db)):
+    # Sanitize user input
+    safe_content = sanitize_html(content)
+
     comment = Comment(
-        content=content  # XSS vulnerability!
+        content=safe_content
     )
     db.add(comment)
     db.commit()
*** End Patch

COMMANDS:
- pip install bleach
- cd backend && pytest tests/test_xss.py -v

NOTES:
- Always sanitize user HTML input
- Use bleach for safe HTML cleaning
- Set CSP headers in responses"""

    elif bug_type == "timezone":
        response = """PLAN:
1) Use timezone-aware datetimes
2) Store in UTC
3) Convert on display

FILES:
- backend/app/utils/datetime.py
- backend/app/api/events.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/utils/datetime.py
@@ -0,0 +1,15 @@
+from datetime import datetime
+from zoneinfo import ZoneInfo
+
+def now_utc() -> datetime:
+    return datetime.now(ZoneInfo("UTC"))
+
+def to_user_timezone(dt: datetime, timezone: str) -> datetime:
+    if dt.tzinfo is None:
+        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
+    return dt.astimezone(ZoneInfo(timezone))
+
+def parse_user_datetime(dt_str: str, timezone: str) -> datetime:
+    local = datetime.fromisoformat(dt_str)
+    local = local.replace(tzinfo=ZoneInfo(timezone))
+    return local.astimezone(ZoneInfo("UTC"))

--- a/backend/app/api/events.py
+++ b/backend/app/api/events.py
@@ -1,8 +1,12 @@
-from datetime import datetime
+from app.utils.datetime import now_utc, parse_user_datetime

 @app.post("/events")
-async def create_event(time: str, db=Depends(get_db)):
+async def create_event(time: str, timezone: str, db=Depends(get_db)):
+    # Convert to UTC for storage
+    utc_time = parse_user_datetime(time, timezone)
+
     event = Event(
-        scheduled_at=datetime.fromisoformat(time)  # Naive datetime!
+        scheduled_at=utc_time,
+        user_timezone=timezone
     )
     db.add(event)
     db.commit()
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_timezone.py -v

NOTES:
- Always store in UTC
- Convert to user timezone on display
- Use zoneinfo (Python 3.9+)"""

    else:
        response = f"""PLAN:
1) Identify root cause
2) Implement fix
3) Add tests

FILES:
- backend/app/fix.py

PATCH:
*** Begin Patch
--- a/backend/app/fix.py
+++ b/backend/app/fix.py
@@ -1,5 +1,10 @@
-# Buggy code
-pass
+# Fixed code
+# Proper implementation here
*** End Patch

COMMANDS:
- cd backend && pytest -v

NOTES:
- Root cause: {bug_cause}
- Add monitoring for this issue"""

    return create_example(prompt, response, "bug_fix")


# ============================================================================
# 3. TEST GENERATORS (100 samples)
# ============================================================================

def generate_test_example(feature: str, test_type: str) -> dict:
    """Generate test implementation example."""
    prompt = f"Add {test_type} tests for the {feature} feature."

    response = f"""PLAN:
1) Create test fixtures
2) Write unit tests
3) Add integration tests
4) Test edge cases

FILES:
- backend/tests/test_{feature.lower().replace(' ', '_')}.py
- backend/tests/conftest.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/tests/conftest.py
@@ -0,0 +1,30 @@
+import pytest
+from sqlalchemy import create_engine
+from sqlalchemy.orm import sessionmaker
+from unittest.mock import MagicMock
+from app.db.base import Base
+
+@pytest.fixture
+def db_session():
+    engine = create_engine("sqlite:///:memory:")
+    Base.metadata.create_all(engine)
+    Session = sessionmaker(bind=engine)
+    session = Session()
+    yield session
+    session.close()
+
+@pytest.fixture
+def mock_service():
+    return MagicMock()
+
+@pytest.fixture
+def test_user(db_session):
+    from app.models.user import User
+    user = User(email="test@example.com", name="Test User")
+    user.set_password("password123")
+    db_session.add(user)
+    db_session.commit()
+    return user

--- /dev/null
+++ b/backend/tests/test_{feature.lower().replace(' ', '_')}.py
@@ -0,0 +1,60 @@
+import pytest
+from unittest.mock import MagicMock, patch
+from decimal import Decimal
+
+class Test{feature.replace(' ', '')}:
+    def test_success_case(self, db_session, test_user):
+        # Arrange
+        service = Service(db_session)
+
+        # Act
+        result = service.process(test_user.id)
+
+        # Assert
+        assert result.success is True
+
+    def test_invalid_input(self, db_session):
+        service = Service(db_session)
+
+        with pytest.raises(ValueError, match="Invalid"):
+            service.process(None)
+
+    def test_not_found(self, db_session):
+        service = Service(db_session)
+
+        with pytest.raises(NotFoundException):
+            service.process(999)
+
+    @pytest.mark.parametrize("input,expected", [
+        ("valid", True),
+        ("", False),
+        (None, False),
+    ])
+    def test_validation(self, db_session, input, expected):
+        service = Service(db_session)
+        result = service.validate(input)
+        assert result == expected
+
+    @patch("app.services.external_api")
+    def test_with_mock(self, mock_api, db_session):
+        mock_api.call.return_value = {{"status": "ok"}}
+
+        service = Service(db_session)
+        result = service.process_external()
+
+        mock_api.call.assert_called_once()
+        assert result["status"] == "ok"
+
+
+class Test{feature.replace(' ', '')}Integration:
+    @pytest.mark.integration
+    def test_full_flow(self, db_session, test_user):
+        # Test complete workflow
+        service = Service(db_session)
+
+        # Step 1
+        result1 = service.step1(test_user.id)
+        assert result1.success
+
+        # Step 2
+        result2 = service.step2(result1.id)
+        assert result2.success
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_{feature.lower().replace(' ', '_')}.py -v
- cd backend && pytest tests/test_{feature.lower().replace(' ', '_')}.py --cov=app -v

NOTES:
- Use fixtures for common setup
- Mock external dependencies
- Parametrize for edge cases
- Mark integration tests separately"""

    return create_example(prompt, response, "add_tests")


# ============================================================================
# 4. REFACTOR GENERATORS (50 samples)
# ============================================================================

def generate_refactor_example(pattern: str) -> dict:
    """Generate refactoring example."""
    prompt = f"Refactor this code to follow {pattern} pattern."

    if "repository" in pattern.lower():
        response = """PLAN:
1) Extract data access to repository
2) Create repository interface
3) Implement concrete repository
4) Update service to use repository

FILES:
- backend/app/repositories/user_repository.py
- backend/app/services/user_service.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/repositories/user_repository.py
@@ -0,0 +1,30 @@
+from typing import Optional, List
+from sqlalchemy.orm import Session
+from app.models.user import User
+
+class UserRepository:
+    def __init__(self, db: Session):
+        self.db = db
+
+    def find_by_id(self, user_id: int) -> Optional[User]:
+        return self.db.query(User).filter(User.id == user_id).first()
+
+    def find_by_email(self, email: str) -> Optional[User]:
+        return self.db.query(User).filter(User.email == email).first()
+
+    def find_all(self, limit: int = 100) -> List[User]:
+        return self.db.query(User).limit(limit).all()
+
+    def create(self, user: User) -> User:
+        self.db.add(user)
+        self.db.flush()
+        return user
+
+    def update(self, user: User) -> User:
+        self.db.merge(user)
+        self.db.flush()
+        return user
+
+    def delete(self, user: User) -> None:
+        self.db.delete(user)
+        self.db.flush()

--- a/backend/app/services/user_service.py
+++ b/backend/app/services/user_service.py
@@ -1,15 +1,20 @@
+from app.repositories.user_repository import UserRepository
+
 class UserService:
-    def __init__(self, db):
-        self.db = db
+    def __init__(self, repository: UserRepository):
+        self.repository = repository

     def get_user(self, user_id: int):
-        return self.db.query(User).filter(User.id == user_id).first()
+        return self.repository.find_by_id(user_id)

     def create_user(self, email: str, name: str):
-        user = User(email=email, name=name)
-        self.db.add(user)
-        self.db.commit()
-        return user
+        if self.repository.find_by_email(email):
+            raise ValueError("Email already exists")
+
+        user = User(email=email, name=name)
+        return self.repository.create(user)
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_user_service.py -v

NOTES:
- Repository handles data access
- Service handles business logic
- Easier to test with mock repository
- Single Responsibility Principle"""

    else:
        response = f"""PLAN:
1) Identify code smells
2) Extract responsibilities
3) Apply {pattern} pattern
4) Update tests

FILES:
- backend/app/refactored.py

PATCH:
*** Begin Patch
--- a/backend/app/old_code.py
+++ b/backend/app/refactored.py
@@ -1,20 +1,35 @@
-# God class doing everything
-class DoEverything:
-    pass
+# Clean code following {pattern}
+class SingleResponsibility:
+    def __init__(self, dependency):
+        self.dependency = dependency
+
+    def do_one_thing(self):
+        return self.dependency.process()
*** End Patch

COMMANDS:
- cd backend && pytest -v

NOTES:
- Applied {pattern} pattern
- Improved testability
- Better separation of concerns"""

    return create_example(prompt, response, "refactor")


# ============================================================================
# 5. SECURITY GENERATORS (50 samples)
# ============================================================================

def generate_security_example(security_type: str) -> dict:
    """Generate security implementation example."""
    prompt = f"Implement {security_type} security feature."

    if "rbac" in security_type.lower():
        response = """PLAN:
1) Create Role and Permission models
2) Implement permission checker
3) Add FastAPI dependency
4) Cache permissions in Redis

FILES:
- backend/app/models/rbac.py
- backend/app/core/permissions.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/rbac.py
@@ -0,0 +1,25 @@
+from sqlalchemy import Column, Integer, String, Table, ForeignKey
+from sqlalchemy.orm import relationship
+from app.db.base import Base
+
+user_roles = Table(
+    "user_roles", Base.metadata,
+    Column("user_id", Integer, ForeignKey("users.id")),
+    Column("role_id", Integer, ForeignKey("roles.id"))
+)
+
+role_permissions = Table(
+    "role_permissions", Base.metadata,
+    Column("role_id", Integer, ForeignKey("roles.id")),
+    Column("permission_id", Integer, ForeignKey("permissions.id"))
+)
+
+class Role(Base):
+    __tablename__ = "roles"
+    id = Column(Integer, primary_key=True)
+    name = Column(String, unique=True)
+    permissions = relationship("Permission", secondary=role_permissions)
+
+class Permission(Base):
+    __tablename__ = "permissions"
+    id = Column(Integer, primary_key=True)
+    resource = Column(String)
+    action = Column(String)

--- /dev/null
+++ b/backend/app/core/permissions.py
@@ -0,0 +1,40 @@
+from functools import wraps
+from fastapi import HTTPException, Depends
+import redis
+import json
+
+redis_client = redis.Redis()
+
+class PermissionChecker:
+    def __init__(self, db):
+        self.db = db
+
+    def get_permissions(self, user_id: int) -> set:
+        cached = redis_client.get(f"perms:{user_id}")
+        if cached:
+            return set(json.loads(cached))
+
+        user = self.db.query(User).get(user_id)
+        perms = set()
+        for role in user.roles:
+            for perm in role.permissions:
+                perms.add(f"{perm.resource}:{perm.action}")
+
+        redis_client.setex(f"perms:{user_id}", 300, json.dumps(list(perms)))
+        return perms
+
+    def has_permission(self, user_id: int, resource: str, action: str) -> bool:
+        perms = self.get_permissions(user_id)
+        return f"{resource}:{action}" in perms or f"{resource}:*" in perms
+
+def require_permission(resource: str, action: str):
+    def decorator(func):
+        @wraps(func)
+        async def wrapper(*args, user=Depends(get_current_user), db=Depends(get_db), **kwargs):
+            checker = PermissionChecker(db)
+            if not checker.has_permission(user.id, resource, action):
+                raise HTTPException(403, "Permission denied")
+            return await func(*args, user=user, db=db, **kwargs)
+        return wrapper
+    return decorator
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_rbac.py -v

NOTES:
- Cache permissions for performance
- Support wildcard permissions
- Invalidate cache on role change"""

    elif "input validation" in security_type.lower():
        response = """PLAN:
1) Add Pydantic validators
2) Implement sanitization
3) Add rate limiting
4) Log suspicious inputs

FILES:
- backend/app/validators/input.py
- backend/app/middleware/validation.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/validators/input.py
@@ -0,0 +1,40 @@
+import re
+from pydantic import BaseModel, validator, Field
+from typing import Optional
+import bleach
+
+class SafeInput(BaseModel):
+    text: str = Field(..., min_length=1, max_length=10000)
+
+    @validator("text")
+    def sanitize_text(cls, v):
+        # Remove null bytes
+        v = v.replace("\\x00", "")
+
+        # Check for script injection
+        if re.search(r"<script", v, re.IGNORECASE):
+            raise ValueError("Script tags not allowed")
+
+        # Sanitize HTML
+        v = bleach.clean(v, tags=[], strip=True)
+
+        return v
+
+class EmailInput(BaseModel):
+    email: str
+
+    @validator("email")
+    def validate_email(cls, v):
+        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
+        if not re.match(pattern, v):
+            raise ValueError("Invalid email format")
+        if len(v) > 254:
+            raise ValueError("Email too long")
+        return v.lower()
+
+class URLInput(BaseModel):
+    url: str
+
+    @validator("url")
+    def validate_url(cls, v):
+        if not v.startswith(("http://", "https://")):
+            raise ValueError("URL must start with http:// or https://")
+        return v
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_validation.py -v

NOTES:
- Always validate input length
- Sanitize HTML content
- Validate URL protocols
- Log validation failures"""

    else:
        response = f"""PLAN:
1) Implement {security_type}
2) Add security headers
3) Create security tests

FILES:
- backend/app/security/{security_type.lower().replace(' ', '_')}.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/security/{security_type.lower().replace(' ', '_')}.py
@@ -0,0 +1,20 @@
+# {security_type} implementation
+from fastapi import Request
+
+class SecurityMiddleware:
+    async def __call__(self, request: Request, call_next):
+        response = await call_next(request)
+
+        # Add security headers
+        response.headers["X-Content-Type-Options"] = "nosniff"
+        response.headers["X-Frame-Options"] = "DENY"
+        response.headers["X-XSS-Protection"] = "1; mode=block"
+
+        return response
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_security.py -v

NOTES:
- Add security headers to all responses
- Implement rate limiting
- Log security events"""

    return create_example(prompt, response, "security")


# ============================================================================
# MAIN GENERATOR
# ============================================================================

def generate_all_samples() -> List[dict]:
    """Generate all 500+ gold samples."""
    samples = []

    print("Generating SPEC -> IMPLEMENTATION samples...")

    # CRUD APIs (30 samples)
    entities = ["Product", "Order", "Customer", "Invoice", "Payment", "Booking",
                "Review", "Comment", "Category", "Tag", "Article", "Event",
                "Notification", "Message", "Task", "Project"]
    for entity in entities:
        framework = random.choice(["FastAPI", "Django REST", "Flask"])
        samples.append(generate_crud_api(entity, framework))

    # Auth endpoints (20 samples)
    for auth in AUTH_METHODS:
        for fw in random.sample(BACKENDS, 2):
            samples.append(generate_auth_endpoint(auth, fw))

    # File upload (15 samples)
    storages = ["S3", "Google Cloud Storage", "Azure Blob", "MinIO", "Local filesystem"]
    for storage in storages:
        samples.append(generate_file_upload(storage))
        samples.append(generate_file_upload(storage))
        samples.append(generate_file_upload(storage))

    # WebSocket (20 samples)
    ws_features = ["chat", "notifications", "real-time updates", "collaborative editing",
                   "live dashboard", "gaming", "auction bidding", "live streaming"]
    for feature in ws_features:
        samples.append(generate_websocket_feature(feature))
        samples.append(generate_websocket_feature(feature))

    # Background jobs (25 samples)
    job_types = ["email sending", "report generation", "data import", "image processing",
                 "video transcoding", "PDF generation", "data sync", "cleanup",
                 "notification dispatch", "analytics aggregation"]
    for job in job_types:
        samples.append(generate_background_job(job))
        samples.append(generate_background_job(job))

    # Additional spec samples (60+ samples)
    additional_specs = [
        ("Implement pagination with cursor-based navigation", "spec_to_implementation"),
        ("Create GraphQL API with subscriptions", "spec_to_implementation"),
        ("Implement rate limiting with Redis", "spec_to_implementation"),
        ("Add caching layer with invalidation", "spec_to_implementation"),
        ("Create webhook system with retry", "spec_to_implementation"),
        ("Implement search with Elasticsearch", "spec_to_implementation"),
        ("Add audit logging for all changes", "spec_to_implementation"),
        ("Create multi-tenant architecture", "spec_to_implementation"),
        ("Implement soft delete with restore", "spec_to_implementation"),
        ("Add versioned API endpoints", "spec_to_implementation"),
        ("Implement OAuth2 client credentials flow", "spec_to_implementation"),
        ("Create event-driven notification system", "spec_to_implementation"),
        ("Add health check and readiness probes", "spec_to_implementation"),
        ("Implement circuit breaker pattern", "spec_to_implementation"),
        ("Create batch job processing system", "spec_to_implementation"),
        ("Add distributed tracing with OpenTelemetry", "spec_to_implementation"),
        ("Implement feature flags system", "spec_to_implementation"),
    ]
    for prompt, cat in additional_specs * 4:
        samples.append(create_example(
            prompt,
            f"""PLAN:
1) Design the architecture
2) Implement core functionality
3) Add error handling
4) Write tests

FILES:
- backend/app/feature.py
- backend/tests/test_feature.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/feature.py
@@ -0,0 +1,30 @@
+# Implementation for: {prompt}
+from fastapi import APIRouter, Depends
+from sqlalchemy.orm import Session
+from app.db.session import get_db
+
+router = APIRouter()
+
+@router.get("/")
+async def get_items(db: Session = Depends(get_db)):
+    # Implementation here
+    return {{"status": "ok"}}
*** End Patch

COMMANDS:
- cd backend && pytest -v

NOTES:
- Follow best practices
- Add proper error handling
- Include tests""",
            cat
        ))

    print(f"  Generated {len(samples)} spec samples")

    print("Generating BUG -> FIX samples...")

    # Bug fixes (150 samples)
    for bug_type, bug_name, bug_cause in BUG_TYPES:
        for _ in range(10):  # 10 variations each
            samples.append(generate_bug_fix(bug_type, bug_name, bug_cause))

    print(f"  Total samples: {len(samples)}")

    print("Generating TEST samples...")

    # Tests (100+ samples)
    features = DOMAINS + ["authentication", "authorization", "file upload", "websocket",
                          "payment processing", "email sending", "search", "caching",
                          "rate limiting", "logging", "metrics", "health check",
                          "batch processing", "export", "import", "backup"]
    test_types = ["unit", "integration", "e2e", "performance", "security"]

    for feature in features:
        for test_type in random.sample(test_types, 3):  # 3 test types per feature
            samples.append(generate_test_example(feature, test_type))

    print(f"  Total samples: {len(samples)}")

    print("Generating REFACTOR samples...")

    # Refactoring (50 samples)
    patterns = ["Repository Pattern", "Service Layer", "Factory Pattern",
                "Strategy Pattern", "Observer Pattern", "Dependency Injection",
                "CQRS", "Event Sourcing", "Clean Architecture", "Hexagonal Architecture"]
    for pattern in patterns:
        for _ in range(5):
            samples.append(generate_refactor_example(pattern))

    print(f"  Total samples: {len(samples)}")

    print("Generating SECURITY samples...")

    # Security (50 samples)
    security_types = ["RBAC", "Input Validation", "API Key Authentication",
                      "Rate Limiting", "CORS Configuration", "CSRF Protection",
                      "SQL Injection Prevention", "XSS Prevention", "Password Hashing",
                      "JWT Security"]
    for sec_type in security_types:
        for _ in range(5):
            samples.append(generate_security_example(sec_type))

    print(f"  Total samples: {len(samples)}")

    return samples


def main():
    print("=" * 60)
    print("GENERATING 500+ GOLD SAMPLES")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    samples = generate_all_samples()

    # Count by category
    categories = {}
    for sample in samples:
        cat = sample.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nTotal Samples: {len(samples)}")
    print("\nBy Category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Save samples
    output_file = OUTPUT_DIR / "gold_samples.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    print(f"\nSaved to: {output_file}")

    # Create summary
    summary = {
        "total_samples": len(samples),
        "categories": categories,
        "output_format": ["PLAN", "FILES", "PATCH", "COMMANDS", "NOTES"]
    }

    with open(OUTPUT_DIR / "summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
