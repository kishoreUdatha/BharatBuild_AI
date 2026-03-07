#!/usr/bin/env python3
"""
Generate Claude-Style Training Data for Qwen Fine-tuning V2
Simplified version with proper escaping
"""

import json
from pathlib import Path
from typing import List, Dict

OUTPUT_DIR = Path(__file__).parent / "claude_style_data"

# System prompt for Claude-style responses
SYSTEM_PROMPT = """You are an expert software engineer. When given a task, respond with this structure:

PLAN:
1) First step
2) Second step

FILES:
- path/to/file1.py
- path/to/file2.ts

PATCH:
*** Begin Patch
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -line,count +line,count @@
 context
-removed line
+added line
*** End Patch

COMMANDS:
- command1
- command2

NOTES:
- Important notes

Use unified diff format. Be precise with file paths."""


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
# SPEC -> IMPLEMENTATION EXAMPLES
# ============================================================================

SPEC_EXAMPLES = [
    create_example(
        user_prompt="Implement JWT authentication with FastAPI including register, login, and protected routes.",
        response="""PLAN:
1) Create User model with password hashing
2) Implement JWT token generation
3) Create auth endpoints (register, login)
4) Add dependency for protected routes

FILES:
- backend/app/models/user.py
- backend/app/core/security.py
- backend/app/api/auth.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/user.py
@@ -0,0 +1,25 @@
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
+    email = Column(String, unique=True, index=True)
+    password_hash = Column(String, nullable=False)
+    is_active = Column(Boolean, default=True)
+    created_at = Column(DateTime(timezone=True), server_default=func.now())
+
+    def set_password(self, password: str):
+        self.password_hash = pwd_context.hash(password)
+
+    def verify_password(self, password: str) -> bool:
+        return pwd_context.verify(password, self.password_hash)

--- /dev/null
+++ b/backend/app/core/security.py
@@ -0,0 +1,35 @@
+from datetime import datetime, timedelta
+from jose import JWTError, jwt
+from fastapi import HTTPException, Depends
+from fastapi.security import OAuth2PasswordBearer
+from sqlalchemy.orm import Session
+from app.core.config import settings
+from app.db.session import get_db
+from app.models.user import User
+
+oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
+
+def create_access_token(user_id: int) -> str:
+    expire = datetime.utcnow() + timedelta(hours=24)
+    return jwt.encode(
+        {"sub": str(user_id), "exp": expire},
+        settings.SECRET_KEY,
+        algorithm="HS256"
+    )
+
+async def get_current_user(
+    token: str = Depends(oauth2_scheme),
+    db: Session = Depends(get_db)
+) -> User:
+    try:
+        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
+        user_id = int(payload.get("sub"))
+    except JWTError:
+        raise HTTPException(status_code=401, detail="Invalid token")
+
+    user = db.query(User).filter(User.id == user_id).first()
+    if not user:
+        raise HTTPException(status_code=401, detail="User not found")
+    return user

--- /dev/null
+++ b/backend/app/api/auth.py
@@ -0,0 +1,45 @@
+from fastapi import APIRouter, Depends, HTTPException
+from fastapi.security import OAuth2PasswordRequestForm
+from sqlalchemy.orm import Session
+from pydantic import BaseModel, EmailStr
+from app.db.session import get_db
+from app.models.user import User
+from app.core.security import create_access_token
+
+router = APIRouter(prefix="/api/auth", tags=["Auth"])
+
+class UserCreate(BaseModel):
+    email: EmailStr
+    password: str
+
+class Token(BaseModel):
+    access_token: str
+    token_type: str = "bearer"
+
+@router.post("/register", status_code=201)
+async def register(data: UserCreate, db: Session = Depends(get_db)):
+    if db.query(User).filter(User.email == data.email).first():
+        raise HTTPException(400, "Email exists")
+
+    user = User(email=data.email)
+    user.set_password(data.password)
+    db.add(user)
+    db.commit()
+    return {"message": "User created"}
+
+@router.post("/login", response_model=Token)
+async def login(
+    form: OAuth2PasswordRequestForm = Depends(),
+    db: Session = Depends(get_db)
+):
+    user = db.query(User).filter(User.email == form.username).first()
+    if not user or not user.verify_password(form.password):
+        raise HTTPException(401, "Invalid credentials")
+
+    return Token(access_token=create_access_token(user.id))
*** End Patch

COMMANDS:
- cd backend && alembic upgrade head
- cd backend && pytest tests/test_auth.py -v

NOTES:
- SECRET_KEY must be set in environment
- Add rate limiting for production
- Consider refresh tokens for longer sessions""",
        category="spec_to_implementation"
    ),

    create_example(
        user_prompt="Create a REST API for a blog with posts, pagination, and search.",
        response="""PLAN:
1) Create Post model with relationships
2) Implement CRUD endpoints
3) Add pagination with offset/limit
4) Add search by title/content

FILES:
- backend/app/models/post.py
- backend/app/api/posts.py
- backend/app/schemas/post.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/post.py
@@ -0,0 +1,18 @@
+from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
+from sqlalchemy.orm import relationship
+from sqlalchemy.sql import func
+from app.db.base import Base
+
+class Post(Base):
+    __tablename__ = "posts"
+
+    id = Column(Integer, primary_key=True)
+    title = Column(String(200), nullable=False)
+    content = Column(Text, nullable=False)
+    author_id = Column(Integer, ForeignKey("users.id"))
+    created_at = Column(DateTime(timezone=True), server_default=func.now())
+    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
+
+    author = relationship("User", back_populates="posts")

--- /dev/null
+++ b/backend/app/api/posts.py
@@ -0,0 +1,70 @@
+from fastapi import APIRouter, Depends, HTTPException, Query
+from sqlalchemy.orm import Session
+from sqlalchemy import or_
+from typing import List, Optional
+from app.db.session import get_db
+from app.models.post import Post
+from app.core.security import get_current_user
+from app.schemas.post import PostCreate, PostResponse, PostList
+
+router = APIRouter(prefix="/api/posts", tags=["Posts"])
+
+@router.get("/", response_model=PostList)
+async def list_posts(
+    page: int = Query(1, ge=1),
+    per_page: int = Query(20, ge=1, le=100),
+    search: Optional[str] = None,
+    db: Session = Depends(get_db)
+):
+    query = db.query(Post)
+
+    if search:
+        query = query.filter(or_(
+            Post.title.ilike(f"%{search}%"),
+            Post.content.ilike(f"%{search}%")
+        ))
+
+    total = query.count()
+    posts = query.offset((page - 1) * per_page).limit(per_page).all()
+
+    return PostList(
+        items=posts,
+        total=total,
+        page=page,
+        pages=(total + per_page - 1) // per_page
+    )
+
+@router.post("/", response_model=PostResponse, status_code=201)
+async def create_post(
+    data: PostCreate,
+    user = Depends(get_current_user),
+    db: Session = Depends(get_db)
+):
+    post = Post(**data.dict(), author_id=user.id)
+    db.add(post)
+    db.commit()
+    db.refresh(post)
+    return post
+
+@router.get("/{post_id}", response_model=PostResponse)
+async def get_post(post_id: int, db: Session = Depends(get_db)):
+    post = db.query(Post).filter(Post.id == post_id).first()
+    if not post:
+        raise HTTPException(404, "Post not found")
+    return post
+
+@router.delete("/{post_id}", status_code=204)
+async def delete_post(
+    post_id: int,
+    user = Depends(get_current_user),
+    db: Session = Depends(get_db)
+):
+    post = db.query(Post).filter(Post.id == post_id).first()
+    if not post:
+        raise HTTPException(404, "Post not found")
+    if post.author_id != user.id:
+        raise HTTPException(403, "Not authorized")
+    db.delete(post)
+    db.commit()
*** End Patch

COMMANDS:
- cd backend && alembic upgrade head
- cd backend && pytest tests/test_posts.py -v

NOTES:
- Search uses ILIKE for case-insensitive matching
- Consider full-text search for large datasets
- Add caching for frequently accessed posts""",
        category="spec_to_implementation"
    ),

    create_example(
        user_prompt="Implement file upload with S3 storage and virus scanning.",
        response="""PLAN:
1) Create upload endpoint with validation
2) Implement S3 storage service
3) Add file type and size validation
4) Integrate virus scanning placeholder

FILES:
- backend/app/api/upload.py
- backend/app/services/storage.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/services/storage.py
@@ -0,0 +1,40 @@
+import boto3
+from uuid import uuid4
+from app.core.config import settings
+
+class StorageService:
+    def __init__(self):
+        self.s3 = boto3.client("s3")
+        self.bucket = settings.S3_BUCKET
+
+    async def upload(self, file_obj, filename: str, content_type: str) -> str:
+        key = f"uploads/{uuid4().hex}/{filename}"
+
+        self.s3.upload_fileobj(
+            file_obj,
+            self.bucket,
+            key,
+            ExtraArgs={"ContentType": content_type}
+        )
+
+        return f"https://{self.bucket}.s3.amazonaws.com/{key}"
+
+    async def delete(self, key: str):
+        self.s3.delete_object(Bucket=self.bucket, Key=key)

--- /dev/null
+++ b/backend/app/api/upload.py
@@ -0,0 +1,45 @@
+from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
+from app.services.storage import StorageService
+from app.core.security import get_current_user
+
+router = APIRouter(prefix="/api/upload", tags=["Upload"])
+
+ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
+MAX_SIZE = 10 * 1024 * 1024  # 10MB
+
+async def scan_file(content: bytes) -> bool:
+    # Placeholder for virus scanning (ClamAV integration)
+    return True
+
+@router.post("/")
+async def upload_file(
+    file: UploadFile = File(...),
+    user = Depends(get_current_user),
+    storage: StorageService = Depends()
+):
+    # Validate content type
+    if file.content_type not in ALLOWED_TYPES:
+        raise HTTPException(400, "File type not allowed")
+
+    # Check file size
+    content = await file.read()
+    if len(content) > MAX_SIZE:
+        raise HTTPException(400, "File too large")
+
+    # Virus scan
+    if not await scan_file(content):
+        raise HTTPException(400, "File failed security scan")
+
+    # Reset file position and upload
+    file.file.seek(0)
+    url = await storage.upload(file.file, file.filename, file.content_type)
+
+    return {"url": url, "filename": file.filename}
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_upload.py -v
- aws s3 ls s3://your-bucket/uploads/

NOTES:
- Implement actual virus scanning with ClamAV
- Consider async processing for large files
- Add file metadata storage in database""",
        category="spec_to_implementation"
    ),

    create_example(
        user_prompt="Create a WebSocket chat system with rooms and message history.",
        response="""PLAN:
1) Create ChatRoom manager class
2) Implement WebSocket endpoint
3) Add message persistence
4) Handle user join/leave events

FILES:
- backend/app/websocket/chat.py
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
+    room_id = Column(String, index=True)
+    user_id = Column(Integer, ForeignKey("users.id"))
+    content = Column(Text, nullable=False)
+    created_at = Column(DateTime(timezone=True), server_default=func.now())

--- /dev/null
+++ b/backend/app/websocket/chat.py
@@ -0,0 +1,65 @@
+from fastapi import WebSocket, WebSocketDisconnect
+from typing import Dict, List
+import json
+
+class ChatRoom:
+    def __init__(self, room_id: str):
+        self.room_id = room_id
+        self.connections: Dict[int, WebSocket] = {}
+
+    async def connect(self, user_id: int, ws: WebSocket):
+        await ws.accept()
+        self.connections[user_id] = ws
+        await self.broadcast({"type": "join", "user_id": user_id})
+
+    async def disconnect(self, user_id: int):
+        self.connections.pop(user_id, None)
+        await self.broadcast({"type": "leave", "user_id": user_id})
+
+    async def broadcast(self, message: dict, exclude: int = None):
+        for uid, ws in self.connections.items():
+            if uid != exclude:
+                try:
+                    await ws.send_json(message)
+                except:
+                    pass
+
+class ChatManager:
+    def __init__(self):
+        self.rooms: Dict[str, ChatRoom] = {}
+
+    def get_room(self, room_id: str) -> ChatRoom:
+        if room_id not in self.rooms:
+            self.rooms[room_id] = ChatRoom(room_id)
+        return self.rooms[room_id]
+
+manager = ChatManager()
+
+@app.websocket("/ws/chat/{room_id}")
+async def chat_endpoint(ws: WebSocket, room_id: str, token: str):
+    user = await verify_token(token)
+    if not user:
+        await ws.close(code=4001)
+        return
+
+    room = manager.get_room(room_id)
+    await room.connect(user.id, ws)
+
+    try:
+        while True:
+            data = await ws.receive_json()
+
+            if data["type"] == "message":
+                # Save to database
+                msg = Message(
+                    room_id=room_id,
+                    user_id=user.id,
+                    content=data["content"]
+                )
+                db.add(msg)
+                db.commit()
+
+                # Broadcast
+                await room.broadcast({
+                    "type": "message",
+                    "user_id": user.id,
+                    "content": data["content"]
+                })
+    except WebSocketDisconnect:
+        await room.disconnect(user.id)
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_chat.py -v
- websocat ws://localhost:8000/ws/chat/test?token=xxx

NOTES:
- Add Redis PubSub for multi-server deployment
- Implement typing indicators
- Consider message encryption""",
        category="spec_to_implementation"
    ),

    create_example(
        user_prompt="Implement rate limiting middleware with Redis.",
        response="""PLAN:
1) Create Redis-based rate limiter
2) Implement sliding window algorithm
3) Add per-user and per-IP limits
4) Create FastAPI middleware

FILES:
- backend/app/middleware/rate_limit.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/middleware/rate_limit.py
@@ -0,0 +1,70 @@
+import time
+import redis
+from fastapi import Request, HTTPException
+from starlette.middleware.base import BaseHTTPMiddleware
+
+redis_client = redis.Redis(host="localhost", port=6379, db=0)
+
+class RateLimiter:
+    def __init__(self, requests_per_minute: int = 60):
+        self.rpm = requests_per_minute
+
+    def get_identifier(self, request: Request) -> str:
+        # Use user ID if authenticated, else IP
+        if hasattr(request.state, "user_id"):
+            return f"user:{request.state.user_id}"
+        forwarded = request.headers.get("X-Forwarded-For")
+        ip = forwarded.split(",")[0] if forwarded else request.client.host
+        return f"ip:{ip}"
+
+    def check(self, identifier: str) -> tuple:
+        now = int(time.time())
+        key = f"rate:{identifier}:{now // 60}"
+
+        pipe = redis_client.pipeline()
+        pipe.incr(key)
+        pipe.expire(key, 120)
+        results = pipe.execute()
+
+        count = results[0]
+        remaining = max(0, self.rpm - count)
+
+        headers = {
+            "X-RateLimit-Limit": str(self.rpm),
+            "X-RateLimit-Remaining": str(remaining),
+            "X-RateLimit-Reset": str((now // 60 + 1) * 60)
+        }
+
+        return count <= self.rpm, headers
+
+class RateLimitMiddleware(BaseHTTPMiddleware):
+    def __init__(self, app, limiter: RateLimiter = None):
+        super().__init__(app)
+        self.limiter = limiter or RateLimiter()
+
+    async def dispatch(self, request: Request, call_next):
+        identifier = self.limiter.get_identifier(request)
+        allowed, headers = self.limiter.check(identifier)
+
+        if not allowed:
+            raise HTTPException(
+                status_code=429,
+                detail="Rate limit exceeded",
+                headers=headers
+            )
+
+        response = await call_next(request)
+        for key, value in headers.items():
+            response.headers[key] = value
+        return response
+
+# Usage:
+# app.add_middleware(RateLimitMiddleware)
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_rate_limit.py -v
- redis-cli KEYS "rate:*"

NOTES:
- Sliding window prevents burst at window boundaries
- Consider different limits per endpoint
- Add Redis cluster support for HA""",
        category="spec_to_implementation"
    ),
]

# ============================================================================
# BUG -> FIX EXAMPLES
# ============================================================================

BUG_EXAMPLES = [
    create_example(
        user_prompt="""Fix this production error:
```
sqlalchemy.exc.TimeoutError: QueuePool limit reached, connection timed out
```
Code:
```python
def get_user(user_id):
    session = Session()
    return session.query(User).filter(User.id == user_id).first()
```""",
        response="""PLAN:
1) Add context manager for session cleanup
2) Configure connection pool properly
3) Create FastAPI dependency for sessions

FILES:
- backend/app/db/session.py

PATCH:
*** Begin Patch
--- a/backend/app/db/session.py
+++ b/backend/app/db/session.py
@@ -1,8 +1,30 @@
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
+    pool_pre_ping=True
+)
 Session = sessionmaker(bind=engine)

-def get_user(user_id):
-    session = Session()
-    return session.query(User).filter(User.id == user_id).first()
+def get_db() -> Generator[Session, None, None]:
+    db = Session()
+    try:
+        yield db
+    finally:
+        db.close()
+
+# Usage with FastAPI:
+# @app.get("/users/{user_id}")
+# def get_user(user_id: int, db: Session = Depends(get_db)):
+#     return db.query(User).filter(User.id == user_id).first()
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_db.py -v

NOTES:
- Root cause: Sessions never closed
- pool_pre_ping checks connection health
- Always use context manager or dependency""",
        category="bug_fix"
    ),

    create_example(
        user_prompt="""Fix race condition causing negative balance:
```
Error: Negative balance for user 123
Balance: -50.00
```
Code:
```python
@app.post("/purchase")
async def purchase(product_id: int, user = Depends(get_user), db = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if user.balance >= product.price:
        user.balance -= product.price
        db.commit()
```""",
        response="""PLAN:
1) Add row-level locking with FOR UPDATE
2) Use atomic database update
3) Add idempotency key

FILES:
- backend/app/api/purchase.py

PATCH:
*** Begin Patch
--- a/backend/app/api/purchase.py
+++ b/backend/app/api/purchase.py
@@ -1,8 +1,30 @@
+from sqlalchemy import text
+from fastapi import Header
+
 @app.post("/purchase")
 async def purchase(
     product_id: int,
+    idempotency_key: str = Header(...),
     user = Depends(get_user),
     db = Depends(get_db)
 ):
-    product = db.query(Product).get(product_id)
-    if user.balance >= product.price:
-        user.balance -= product.price
-        db.commit()
+    # Check idempotency
+    existing = db.execute(
+        text("SELECT id FROM orders WHERE idempotency_key = :key"),
+        {"key": idempotency_key}
+    ).first()
+    if existing:
+        return {"order_id": existing.id, "duplicate": True}
+
+    # Atomic update with balance check
+    result = db.execute(
+        text("""
+            UPDATE users
+            SET balance = balance - :price
+            WHERE id = :user_id AND balance >= :price
+            RETURNING balance
+        """),
+        {"user_id": user.id, "price": product.price}
+    ).first()
+
+    if not result:
+        raise HTTPException(400, "Insufficient balance")
+
+    # Create order with idempotency key
+    order = Order(user_id=user.id, product_id=product_id, idempotency_key=idempotency_key)
+    db.add(order)
+    db.commit()
+    return {"order_id": order.id}
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_purchase_concurrent.py -v

NOTES:
- Atomic UPDATE prevents race condition
- Idempotency key prevents duplicate orders
- Consider using SELECT FOR UPDATE for complex logic""",
        category="bug_fix"
    ),

    create_example(
        user_prompt="""Fix SQL injection vulnerability:
```python
@app.get("/search")
def search(query: str, db = Depends(get_db)):
    sql = f"SELECT * FROM products WHERE name LIKE '%{query}%'"
    return db.execute(sql).fetchall()
```""",
        response="""PLAN:
1) Use parameterized queries
2) Add input validation
3) Use ORM instead of raw SQL

FILES:
- backend/app/api/search.py

PATCH:
*** Begin Patch
--- a/backend/app/api/search.py
+++ b/backend/app/api/search.py
@@ -1,5 +1,20 @@
+from fastapi import Query
+from sqlalchemy.orm import Session
+from app.models import Product
+
 @app.get("/search")
-def search(query: str, db = Depends(get_db)):
-    sql = f"SELECT * FROM products WHERE name LIKE '%{query}%'"
-    return db.execute(sql).fetchall()
+def search(
+    query: str = Query(..., min_length=1, max_length=100),
+    db: Session = Depends(get_db)
+):
+    # Use ORM - automatically parameterized
+    results = db.query(Product).filter(
+        Product.name.ilike(f"%{query}%")
+    ).limit(100).all()
+
+    return results
+
+# If raw SQL needed, use parameters:
+# from sqlalchemy import text
+# db.execute(text("SELECT * FROM products WHERE name ILIKE :q"), {"q": f"%{query}%"})
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_search_security.py -v

NOTES:
- ORM automatically escapes parameters
- Always use parameterized queries
- Add input length limits""",
        category="bug_fix"
    ),

    create_example(
        user_prompt="""Fix N+1 query causing slow page loads:
```python
@app.get("/posts")
def get_posts(db = Depends(get_db)):
    posts = db.query(Post).all()
    return [{"title": p.title, "author": p.author.name} for p in posts]
```""",
        response="""PLAN:
1) Use eager loading with joinedload
2) Select only needed columns
3) Add query optimization

FILES:
- backend/app/api/posts.py

PATCH:
*** Begin Patch
--- a/backend/app/api/posts.py
+++ b/backend/app/api/posts.py
@@ -1,5 +1,15 @@
+from sqlalchemy.orm import joinedload
+
 @app.get("/posts")
 def get_posts(db = Depends(get_db)):
-    posts = db.query(Post).all()
-    return [{"title": p.title, "author": p.author.name} for p in posts]
+    # Eager load author to prevent N+1 queries
+    posts = db.query(Post).options(
+        joinedload(Post.author)
+    ).all()
+
+    return [
+        {
+            "title": p.title,
+            "author": p.author.name
+        }
+        for p in posts
+    ]
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_posts.py -v
- SQLALCHEMY_ECHO=1 pytest tests/test_posts.py -v

NOTES:
- joinedload for many-to-one relations
- selectinload for one-to-many
- Use SQLALCHEMY_ECHO to debug queries""",
        category="bug_fix"
    ),

    create_example(
        user_prompt="""Fix memory leak in WebSocket handler:
```python
connections = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)
    while True:
        data = await ws.receive_text()
        for conn in connections:
            await conn.send_text(data)
```""",
        response="""PLAN:
1) Add disconnect cleanup
2) Use weak references or proper tracking
3) Handle exceptions properly

FILES:
- backend/app/websocket/handler.py

PATCH:
*** Begin Patch
--- a/backend/app/websocket/handler.py
+++ b/backend/app/websocket/handler.py
@@ -1,10 +1,35 @@
-connections = []
+from fastapi import WebSocket, WebSocketDisconnect
+from typing import Set
+import asyncio
+
+class ConnectionManager:
+    def __init__(self):
+        self.connections: Set[WebSocket] = set()
+        self._lock = asyncio.Lock()
+
+    async def connect(self, ws: WebSocket):
+        await ws.accept()
+        async with self._lock:
+            self.connections.add(ws)
+
+    async def disconnect(self, ws: WebSocket):
+        async with self._lock:
+            self.connections.discard(ws)
+
+    async def broadcast(self, message: str):
+        dead = []
+        for conn in list(self.connections):
+            try:
+                await conn.send_text(message)
+            except:
+                dead.append(conn)
+        for conn in dead:
+            await self.disconnect(conn)
+
+manager = ConnectionManager()

 @app.websocket("/ws")
 async def websocket_endpoint(ws: WebSocket):
-    await ws.accept()
-    connections.append(ws)
-    while True:
-        data = await ws.receive_text()
-        for conn in connections:
-            await conn.send_text(data)
+    await manager.connect(ws)
+    try:
+        while True:
+            data = await ws.receive_text()
+            await manager.broadcast(data)
+    except WebSocketDisconnect:
+        await manager.disconnect(ws)
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_websocket.py -v

NOTES:
- Always handle disconnection cleanup
- Use Set instead of List for O(1) removal
- Add lock for thread safety""",
        category="bug_fix"
    ),
]

# ============================================================================
# TEST EXAMPLES
# ============================================================================

TEST_EXAMPLES = [
    create_example(
        user_prompt="""Add tests for this payment service:
```python
class PaymentService:
    def process_payment(self, user_id: int, amount: Decimal):
        user = self.db.query(User).get(user_id)
        if not user:
            raise ValueError("User not found")
        intent = self.stripe.PaymentIntent.create(amount=int(amount * 100))
        return Payment(user_id=user_id, amount=amount, intent_id=intent.id)
```""",
        response="""PLAN:
1) Create test fixtures
2) Add unit tests with mocks
3) Add error case tests
4) Add integration tests

FILES:
- backend/tests/test_payment_service.py
- backend/tests/conftest.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/tests/conftest.py
@@ -0,0 +1,25 @@
+import pytest
+from unittest.mock import MagicMock
+from sqlalchemy import create_engine
+from sqlalchemy.orm import sessionmaker
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
+def mock_stripe():
+    stripe = MagicMock()
+    stripe.PaymentIntent.create.return_value = MagicMock(id="pi_test_123")
+    return stripe

--- /dev/null
+++ b/backend/tests/test_payment_service.py
@@ -0,0 +1,50 @@
+import pytest
+from decimal import Decimal
+from unittest.mock import MagicMock
+from app.services.payment import PaymentService
+
+class TestPaymentService:
+    def test_process_payment_success(self, db_session, mock_stripe):
+        # Setup
+        user = User(id=1, email="test@example.com")
+        db_session.add(user)
+        db_session.commit()
+
+        service = PaymentService(mock_stripe, db_session)
+
+        # Execute
+        result = service.process_payment(user_id=1, amount=Decimal("99.99"))
+
+        # Verify
+        assert result.user_id == 1
+        assert result.amount == Decimal("99.99")
+        mock_stripe.PaymentIntent.create.assert_called_once_with(amount=9999)
+
+    def test_process_payment_user_not_found(self, db_session, mock_stripe):
+        service = PaymentService(mock_stripe, db_session)
+
+        with pytest.raises(ValueError, match="User not found"):
+            service.process_payment(user_id=999, amount=Decimal("50.00"))
+
+    def test_process_payment_negative_amount(self, db_session, mock_stripe):
+        user = User(id=1, email="test@example.com")
+        db_session.add(user)
+        db_session.commit()
+
+        service = PaymentService(mock_stripe, db_session)
+
+        with pytest.raises(ValueError, match="positive"):
+            service.process_payment(user_id=1, amount=Decimal("-10.00"))
+
+    @pytest.mark.parametrize("amount,cents", [
+        (Decimal("1.00"), 100),
+        (Decimal("99.99"), 9999),
+        (Decimal("0.50"), 50),
+    ])
+    def test_amount_conversion(self, db_session, mock_stripe, amount, cents):
+        user = User(id=1, email="test@example.com")
+        db_session.add(user)
+        db_session.commit()
+
+        service = PaymentService(mock_stripe, db_session)
+        service.process_payment(user_id=1, amount=amount)
+
+        mock_stripe.PaymentIntent.create.assert_called_with(amount=cents)
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_payment_service.py -v
- cd backend && pytest tests/test_payment_service.py --cov=app/services/payment

NOTES:
- Use fixtures for common setup
- Mock external services
- Parametrize for edge cases""",
        category="add_tests"
    ),
]

# ============================================================================
# REFACTOR EXAMPLES
# ============================================================================

REFACTOR_EXAMPLES = [
    create_example(
        user_prompt="""Refactor this god class:
```python
class UserManager:
    def register(self, email, password):
        if not "@" in email:
            raise ValueError("Invalid email")
        user = User(email=email, password=hashlib.md5(password).hexdigest())
        self.db.add(user)
        self.db.commit()
        self.email_service.send(email, "Welcome!")
        self.analytics.track("user_registered")
        return user
```""",
        response="""PLAN:
1) Extract validation to separate class
2) Use proper password hashing
3) Create repository for data access
4) Use events for side effects

FILES:
- backend/app/services/user_service.py
- backend/app/validators/user_validator.py
- backend/app/repositories/user_repository.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/validators/user_validator.py
@@ -0,0 +1,20 @@
+import re
+from dataclasses import dataclass
+
+@dataclass
+class ValidationResult:
+    is_valid: bool
+    errors: list
+
+class UserValidator:
+    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
+
+    def validate_registration(self, email: str, password: str) -> ValidationResult:
+        errors = []
+
+        if not self.EMAIL_REGEX.match(email):
+            errors.append("Invalid email format")
+        if len(password) < 8:
+            errors.append("Password must be at least 8 characters")
+
+        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

--- /dev/null
+++ b/backend/app/services/user_service.py
@@ -0,0 +1,40 @@
+from passlib.context import CryptContext
+from app.validators.user_validator import UserValidator
+from app.repositories.user_repository import UserRepository
+from app.events import EventBus, UserRegisteredEvent
+
+pwd_context = CryptContext(schemes=["bcrypt"])
+
+class UserService:
+    def __init__(self, repository: UserRepository, validator: UserValidator, event_bus: EventBus):
+        self.repository = repository
+        self.validator = validator
+        self.events = event_bus
+
+    async def register(self, email: str, password: str):
+        # Validate
+        validation = self.validator.validate_registration(email, password)
+        if not validation.is_valid:
+            return {"success": False, "errors": validation.errors}
+
+        # Check existing
+        if self.repository.find_by_email(email):
+            return {"success": False, "errors": ["Email already exists"]}
+
+        # Create user with proper hashing
+        user = User(email=email)
+        user.password_hash = pwd_context.hash(password)
+        self.repository.create(user)
+
+        # Publish event for side effects
+        await self.events.publish(UserRegisteredEvent(user_id=user.id, email=email))
+
+        return {"success": True, "user": user}
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_user_service.py -v

NOTES:
- Single Responsibility: Each class has one job
- Dependency Injection for testability
- Events decouple side effects
- bcrypt replaces MD5""",
        category="refactor"
    ),
]

# ============================================================================
# SECURITY EXAMPLES
# ============================================================================

SECURITY_EXAMPLES = [
    create_example(
        user_prompt="Implement RBAC (Role-Based Access Control) for API endpoints.",
        response="""PLAN:
1) Create Role and Permission models
2) Implement permission checker
3) Create FastAPI dependencies
4) Add caching for performance

FILES:
- backend/app/models/rbac.py
- backend/app/core/permissions.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/rbac.py
@@ -0,0 +1,25 @@
+from sqlalchemy import Column, Integer, String, ForeignKey, Table
+from sqlalchemy.orm import relationship
+from app.db.base import Base
+
+user_roles = Table(
+    "user_roles", Base.metadata,
+    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
+    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True)
+)
+
+role_permissions = Table(
+    "role_permissions", Base.metadata,
+    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
+    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True)
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
@@ -0,0 +1,45 @@
+from functools import wraps
+from fastapi import HTTPException, Depends
+from sqlalchemy.orm import Session
+import redis
+import json
+
+redis_client = redis.Redis()
+
+class PermissionChecker:
+    def __init__(self, db: Session):
+        self.db = db
+
+    def get_permissions(self, user_id: int) -> set:
+        # Check cache
+        cached = redis_client.get(f"perms:{user_id}")
+        if cached:
+            return set(json.loads(cached))
+
+        # Query database
+        user = self.db.query(User).get(user_id)
+        perms = set()
+        for role in user.roles:
+            for perm in role.permissions:
+                perms.add(f"{perm.resource}:{perm.action}")
+
+        # Cache for 5 minutes
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
+        async def wrapper(*args, user = Depends(get_current_user), db = Depends(get_db), **kwargs):
+            checker = PermissionChecker(db)
+            if not checker.has_permission(user.id, resource, action):
+                raise HTTPException(403, "Permission denied")
+            return await func(*args, user=user, db=db, **kwargs)
+        return wrapper
+    return decorator
+
+# Usage:
+# @router.delete("/users/{id}")
+# @require_permission("users", "delete")
+# async def delete_user(id: int, user = Depends(get_current_user)):
*** End Patch

COMMANDS:
- cd backend && alembic upgrade head
- cd backend && pytest tests/test_permissions.py -v

NOTES:
- Wildcard permissions for admin access
- Redis caching for performance
- Invalidate cache on role changes""",
        category="security"
    ),

    create_example(
        user_prompt="Add XSS protection for user-generated content.",
        response="""PLAN:
1) Add HTML sanitization
2) Implement content security policy
3) Use proper output encoding

FILES:
- backend/app/services/sanitizer.py
- backend/app/middleware/security.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/services/sanitizer.py
@@ -0,0 +1,30 @@
+import bleach
+import html
+
+ALLOWED_TAGS = ["b", "i", "em", "strong", "a", "code", "pre"]
+ALLOWED_ATTRS = {"a": ["href", "title"]}
+
+class ContentSanitizer:
+    @staticmethod
+    def sanitize_html(content: str, allow_tags: bool = False) -> str:
+        if allow_tags:
+            return bleach.clean(
+                content,
+                tags=ALLOWED_TAGS,
+                attributes=ALLOWED_ATTRS,
+                strip=True
+            )
+        return bleach.clean(content, tags=[], strip=True)
+
+    @staticmethod
+    def escape_text(content: str) -> str:
+        return html.escape(content)
+
+    @staticmethod
+    def linkify_safe(content: str) -> str:
+        return bleach.linkify(
+            content,
+            callbacks=[
+                lambda attrs, new: {**attrs, ("rel", "noopener nofollow")}
+            ]
+        )
*** End Patch

COMMANDS:
- cd backend && pip install bleach
- cd backend && pytest tests/test_sanitizer.py -v

NOTES:
- Always sanitize user input
- Use bleach for HTML sanitization
- Add noopener to external links""",
        category="security"
    ),
]

# ============================================================================
# DPO PREFERENCE PAIRS
# ============================================================================

DPO_PAIRS = [
    {
        "prompt": "Write a function to read a file",
        "rejected": """```python
def read_file(filename):
    f = open(filename)
    return f.read()
```""",
        "chosen": """```python
from pathlib import Path
from typing import Optional

def read_file(filename: str, encoding: str = "utf-8") -> Optional[str]:
    path = Path(filename)
    if not path.exists():
        return None

    with open(path, "r", encoding=encoding) as f:
        return f.read()
```

**Why better:** Uses context manager, handles missing files, type hints, Path for cross-platform."""
    },
    {
        "prompt": "Create a login endpoint",
        "rejected": """```python
@app.post("/login")
def login(username, password):
    user = db.query(User).filter(User.username == username).first()
    if user.password == password:
        return {"token": username}
```""",
        "chosen": """```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt

pwd_context = CryptContext(schemes=["bcrypt"])

@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()

    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token = jwt.encode({"sub": user.id}, SECRET_KEY)
    return {"access_token": token, "token_type": "bearer"}
```

**Why better:** Password hashing, proper HTTP status, JWT tokens, standard OAuth2 form."""
    },
    {
        "prompt": "Write a database query to get users with posts",
        "rejected": """```python
def get_users_with_posts():
    users = db.query(User).all()
    for user in users:
        user.posts = db.query(Post).filter(Post.user_id == user.id).all()
    return users
```""",
        "chosen": """```python
from sqlalchemy.orm import joinedload

def get_users_with_posts(db: Session, limit: int = 100):
    return db.query(User).options(
        joinedload(User.posts)
    ).limit(limit).all()
```

**Why better:** Prevents N+1 query problem, uses eager loading, has limit."""
    },
    {
        "prompt": "Implement caching",
        "rejected": """```python
cache = {}

def get_data(key):
    if key in cache:
        return cache[key]
    data = expensive_query(key)
    cache[key] = data
    return data
```""",
        "chosen": """```python
import redis
import json
from functools import wraps

redis_client = redis.Redis()

def cached(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{hash((args, tuple(kwargs.items())))}"

            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            redis_client.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

**Why better:** Redis for distributed caching, TTL for expiration, decorator pattern."""
    },
    {
        "prompt": "Validate email input",
        "rejected": """```python
def is_valid_email(email):
    return "@" in email
```""",
        "chosen": """```python
import re
from typing import Tuple

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$')

def validate_email(email: str) -> Tuple[bool, str]:
    if not email:
        return False, "Email is required"

    if len(email) > 254:
        return False, "Email too long"

    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format"

    return True, ""
```

**Why better:** Proper regex validation, length check, returns error message."""
    },
]


def generate_all_examples() -> List[dict]:
    """Generate all training examples."""
    all_examples = []

    # Add all categories
    all_examples.extend(SPEC_EXAMPLES)
    all_examples.extend(BUG_EXAMPLES)
    all_examples.extend(TEST_EXAMPLES)
    all_examples.extend(REFACTOR_EXAMPLES)
    all_examples.extend(SECURITY_EXAMPLES)

    return all_examples


def main():
    print("=" * 70)
    print("GENERATING CLAUDE-STYLE TRAINING DATA V2")
    print("=" * 70)

    OUTPUT_DIR.mkdir(exist_ok=True)

    examples = generate_all_examples()

    # Count by category
    categories = {}
    for ex in examples:
        cat = ex.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nTotal SFT Examples: {len(examples)}")
    print("\nBy Category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    # Save SFT examples
    sft_file = OUTPUT_DIR / "claude_style_sft.jsonl"
    with open(sft_file, 'w', encoding='utf-8') as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"\nSaved SFT to: {sft_file}")

    # Save DPO pairs
    print(f"\nDPO Pairs: {len(DPO_PAIRS)}")
    dpo_file = OUTPUT_DIR / "claude_style_dpo.jsonl"
    with open(dpo_file, 'w', encoding='utf-8') as f:
        for pair in DPO_PAIRS:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    print(f"Saved DPO to: {dpo_file}")

    # Create config
    config = {
        "version": "claude_style_v2",
        "total_sft_examples": len(examples),
        "total_dpo_pairs": len(DPO_PAIRS),
        "categories": categories,
        "output_format": {
            "sections": ["PLAN", "FILES", "PATCH", "COMMANDS", "NOTES"],
            "patch_format": "unified_diff"
        }
    }

    with open(OUTPUT_DIR / "config.json", 'w') as f:
        json.dump(config, f, indent=2)

    print("\n" + "=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
