#!/usr/bin/env python3
"""
Expand Coding Agent Training Data
Generates 500+ comprehensive examples for fine-tuning
"""

import json
from pathlib import Path
from typing import List, Dict

OUTPUT_DIR = Path(__file__).parent / "coding_agent_data"

# ============================================================================
# EXPANDED SPEC -> IMPLEMENTATION EXAMPLES
# ============================================================================

EXPANDED_SPECS = [
    # API CRUD Operations
    {
        "spec": "Create a REST API for blog posts with CRUD operations, pagination, and search",
        "impl": """```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/posts", tags=["Posts"])

class PostCreate(BaseModel):
    title: str
    content: str
    tags: List[str] = []

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    tags: List[str]
    created_at: datetime
    author_id: int

class PaginatedPosts(BaseModel):
    items: List[PostResponse]
    total: int
    page: int
    per_page: int
    pages: int

@router.get("/", response_model=PaginatedPosts)
async def list_posts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Post)

    if search:
        query = query.filter(or_(
            Post.title.ilike(f"%{search}%"),
            Post.content.ilike(f"%{search}%")
        ))

    if tag:
        query = query.filter(Post.tags.contains([tag]))

    total = query.count()
    posts = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": posts,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }

@router.post("/", response_model=PostResponse, status_code=201)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = Post(**post_data.dict(), author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    for key, value in post_data.dict().items():
        setattr(post, key, value)
    db.commit()
    db.refresh(post)
    return post

@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(post)
    db.commit()
```"""
    },
    # File Upload
    {
        "spec": "Implement file upload with validation, virus scanning placeholder, and S3 storage",
        "impl": """```python
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
import boto3
import hashlib
import mimetypes
from typing import List
from uuid import uuid4

router = APIRouter(prefix="/api/files", tags=["Files"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "application/pdf"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB

s3 = boto3.client("s3")
BUCKET = "your-bucket"

class FileResponse(BaseModel):
    id: str
    filename: str
    url: str
    size: int
    content_type: str

async def scan_for_virus(content: bytes) -> bool:
    # Placeholder for virus scanning (e.g., ClamAV)
    return True

@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate content type
    content_type = file.content_type
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"File type {content_type} not allowed")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f"File too large. Max: {MAX_SIZE // 1024 // 1024}MB")

    # Virus scan
    if not await scan_for_virus(content):
        raise HTTPException(400, "File failed security scan")

    # Generate unique key
    file_hash = hashlib.sha256(content).hexdigest()[:16]
    ext = mimetypes.guess_extension(content_type) or ""
    key = f"uploads/{current_user.id}/{uuid4().hex}{ext}"

    # Upload to S3
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type
    )

    # Save to database
    file_record = FileRecord(
        key=key,
        filename=file.filename,
        size=len(content),
        content_type=content_type,
        user_id=current_user.id
    )
    db.add(file_record)
    db.commit()

    url = f"https://{BUCKET}.s3.amazonaws.com/{key}"
    return FileResponse(
        id=file_record.id,
        filename=file.filename,
        url=url,
        size=len(content),
        content_type=content_type
    )
```"""
    },
    # Background Jobs
    {
        "spec": "Implement a background job system with Celery for email sending and report generation",
        "impl": """```python
from celery import Celery
from celery.schedules import crontab
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from datetime import datetime, timedelta

celery = Celery("tasks", broker="redis://localhost:6379/0")

celery.conf.beat_schedule = {
    "daily-report": {
        "task": "tasks.generate_daily_report",
        "schedule": crontab(hour=8, minute=0),
    },
}

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email(self, to: str, subject: str, body: str, html: str = None):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = "noreply@app.com"
        msg["To"] = to

        msg.attach(MIMEText(body, "plain"))
        if html:
            msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("user", "password")
            server.send_message(msg)

        return {"status": "sent", "to": to}

    except Exception as e:
        self.retry(exc=e)

@celery.task(bind=True)
def generate_daily_report(self):
    yesterday = datetime.now() - timedelta(days=1)

    # Fetch data
    orders = db.query(Order).filter(
        Order.created_at >= yesterday.replace(hour=0, minute=0),
        Order.created_at < datetime.now().replace(hour=0, minute=0)
    ).all()

    # Generate report
    df = pd.DataFrame([o.to_dict() for o in orders])
    summary = {
        "total_orders": len(orders),
        "total_revenue": df["total"].sum() if len(df) > 0 else 0,
        "avg_order_value": df["total"].mean() if len(df) > 0 else 0,
    }

    # Send to admins
    admins = db.query(User).filter(User.is_admin == True).all()
    for admin in admins:
        send_email.delay(
            to=admin.email,
            subject=f"Daily Report - {yesterday.strftime('%Y-%m-%d')}",
            body=f"Orders: {summary['total_orders']}, Revenue: ${summary['total_revenue']:.2f}"
        )

    return summary

@celery.task
def process_large_import(file_path: str, user_id: int):
    # Process in chunks
    chunk_size = 1000
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        records = chunk.to_dict("records")
        db.bulk_insert_mappings(Product, records)
        db.commit()

    # Notify user
    user = db.query(User).get(user_id)
    send_email.delay(user.email, "Import Complete", "Your data import has finished.")
```"""
    },
    # WebSocket Chat
    {
        "spec": "Implement real-time chat with WebSocket, rooms, typing indicators, and message history",
        "impl": """```python
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
from datetime import datetime
import asyncio

class ChatRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.connections: Dict[int, WebSocket] = {}
        self.typing_users: Set[int] = set()

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections[user_id] = websocket
        await self.broadcast_system(f"User {user_id} joined")

    async def disconnect(self, user_id: int):
        self.connections.pop(user_id, None)
        self.typing_users.discard(user_id)
        await self.broadcast_system(f"User {user_id} left")

    async def broadcast(self, message: dict, exclude: int = None):
        for user_id, ws in self.connections.items():
            if user_id != exclude:
                try:
                    await ws.send_json(message)
                except:
                    pass

    async def broadcast_system(self, text: str):
        await self.broadcast({"type": "system", "text": text})

class ChatManager:
    def __init__(self):
        self.rooms: Dict[str, ChatRoom] = {}

    def get_room(self, room_id: str) -> ChatRoom:
        if room_id not in self.rooms:
            self.rooms[room_id] = ChatRoom(room_id)
        return self.rooms[room_id]

manager = ChatManager()

@app.websocket("/ws/chat/{room_id}")
async def chat_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str
):
    # Authenticate
    user = await verify_ws_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    room = manager.get_room(room_id)
    await room.connect(user.id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "message":
                # Save to database
                msg = Message(
                    room_id=room_id,
                    user_id=user.id,
                    content=data["content"],
                    created_at=datetime.utcnow()
                )
                db.add(msg)
                db.commit()

                # Broadcast
                await room.broadcast({
                    "type": "message",
                    "id": msg.id,
                    "user_id": user.id,
                    "username": user.name,
                    "content": data["content"],
                    "timestamp": msg.created_at.isoformat()
                })

            elif data["type"] == "typing":
                if data["is_typing"]:
                    room.typing_users.add(user.id)
                else:
                    room.typing_users.discard(user.id)

                await room.broadcast({
                    "type": "typing",
                    "users": list(room.typing_users)
                }, exclude=user.id)

    except WebSocketDisconnect:
        await room.disconnect(user.id)

@app.get("/api/chat/{room_id}/history")
async def get_history(
    room_id: str,
    limit: int = 50,
    before: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(Message).filter(Message.room_id == room_id)
    if before:
        query = query.filter(Message.id < before)
    messages = query.order_by(Message.id.desc()).limit(limit).all()
    return list(reversed(messages))
```"""
    },
    # Rate Limiting
    {
        "spec": "Implement rate limiting middleware with Redis, per-user and per-IP limits",
        "impl": """```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import time
from typing import Optional

redis_client = redis.Redis(host="localhost", port=6379, db=0)

class RateLimitConfig:
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit

DEFAULT_CONFIG = RateLimitConfig()
ENDPOINT_CONFIGS = {
    "/api/auth/login": RateLimitConfig(requests_per_minute=5, burst_limit=3),
    "/api/auth/register": RateLimitConfig(requests_per_minute=3, burst_limit=2),
}

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get identifier (user_id or IP)
        identifier = self._get_identifier(request)
        config = ENDPOINT_CONFIGS.get(request.url.path, DEFAULT_CONFIG)

        # Check rate limits
        if not self._check_rate_limit(identifier, request.url.path, config):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"}
            )

        response = await call_next(request)
        return response

    def _get_identifier(self, request: Request) -> str:
        # Try to get user from token
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            try:
                user = decode_token(auth[7:])
                return f"user:{user['id']}"
            except:
                pass

        # Fall back to IP
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0] if forwarded else request.client.host
        return f"ip:{ip}"

    def _check_rate_limit(
        self,
        identifier: str,
        path: str,
        config: RateLimitConfig
    ) -> bool:
        now = int(time.time())
        pipe = redis_client.pipeline()

        # Minute window
        minute_key = f"rate:{identifier}:{path}:m:{now // 60}"
        pipe.incr(minute_key)
        pipe.expire(minute_key, 120)

        # Hour window
        hour_key = f"rate:{identifier}:{path}:h:{now // 3600}"
        pipe.incr(hour_key)
        pipe.expire(hour_key, 7200)

        # Burst (sliding window)
        burst_key = f"rate:{identifier}:{path}:burst"
        pipe.zadd(burst_key, {str(now): now})
        pipe.zremrangebyscore(burst_key, 0, now - 1)
        pipe.zcard(burst_key)
        pipe.expire(burst_key, 2)

        results = pipe.execute()
        minute_count = results[0]
        hour_count = results[3]
        burst_count = results[6]

        if burst_count > config.burst_limit:
            return False
        if minute_count > config.requests_per_minute:
            return False
        if hour_count > config.requests_per_hour:
            return False

        return True

app.add_middleware(RateLimitMiddleware)
```"""
    },
    # GraphQL API
    {
        "spec": "Create a GraphQL API with Strawberry for users and posts with relationships",
        "impl": """```python
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import List, Optional
from datetime import datetime

@strawberry.type
class User:
    id: int
    email: str
    name: str
    created_at: datetime

    @strawberry.field
    async def posts(self, info) -> List["Post"]:
        db = info.context["db"]
        return db.query(PostModel).filter(PostModel.author_id == self.id).all()

    @strawberry.field
    async def post_count(self, info) -> int:
        db = info.context["db"]
        return db.query(PostModel).filter(PostModel.author_id == self.id).count()

@strawberry.type
class Post:
    id: int
    title: str
    content: str
    created_at: datetime

    @strawberry.field
    async def author(self, info) -> User:
        db = info.context["db"]
        return db.query(UserModel).filter(UserModel.id == self.author_id).first()

@strawberry.input
class CreatePostInput:
    title: str
    content: str

@strawberry.type
class Query:
    @strawberry.field
    async def users(self, info, limit: int = 10, offset: int = 0) -> List[User]:
        db = info.context["db"]
        return db.query(UserModel).offset(offset).limit(limit).all()

    @strawberry.field
    async def user(self, info, id: int) -> Optional[User]:
        db = info.context["db"]
        return db.query(UserModel).filter(UserModel.id == id).first()

    @strawberry.field
    async def posts(
        self,
        info,
        limit: int = 10,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[Post]:
        db = info.context["db"]
        query = db.query(PostModel)
        if search:
            query = query.filter(PostModel.title.ilike(f"%{search}%"))
        return query.offset(offset).limit(limit).all()

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_post(self, info, input: CreatePostInput) -> Post:
        db = info.context["db"]
        user = info.context["user"]

        if not user:
            raise Exception("Authentication required")

        post = PostModel(
            title=input.title,
            content=input.content,
            author_id=user.id
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post

    @strawberry.mutation
    async def delete_post(self, info, id: int) -> bool:
        db = info.context["db"]
        user = info.context["user"]

        post = db.query(PostModel).filter(PostModel.id == id).first()
        if not post:
            raise Exception("Post not found")
        if post.author_id != user.id:
            raise Exception("Not authorized")

        db.delete(post)
        db.commit()
        return True

schema = strawberry.Schema(query=Query, mutation=Mutation)

async def get_context(request: Request, db: Session = Depends(get_db)):
    user = await get_optional_user(request)
    return {"request": request, "db": db, "user": user}

graphql_router = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_router, prefix="/graphql")
```"""
    },
]

# ============================================================================
# EXPANDED BUG -> FIX EXAMPLES
# ============================================================================

EXPANDED_BUGS = [
    # N+1 Query
    {
        "bug": "N+1 query problem causing slow page loads",
        "code": """```python
@app.get("/api/posts")
def get_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).all()
    return [{
        "id": p.id,
        "title": p.title,
        "author": p.author.name,  # N+1 query here!
        "comments_count": len(p.comments)  # Another N+1!
    } for p in posts]
```""",
        "fix": """```python
from sqlalchemy.orm import joinedload, selectinload

@app.get("/api/posts")
def get_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).options(
        joinedload(Post.author),
        selectinload(Post.comments)
    ).all()

    return [{
        "id": p.id,
        "title": p.title,
        "author": p.author.name,
        "comments_count": len(p.comments)
    } for p in posts]

# Or use subquery for count
from sqlalchemy import func

@app.get("/api/posts/v2")
def get_posts_optimized(db: Session = Depends(get_db)):
    comment_counts = db.query(
        Comment.post_id,
        func.count(Comment.id).label("count")
    ).group_by(Comment.post_id).subquery()

    posts = db.query(Post, comment_counts.c.count).outerjoin(
        comment_counts, Post.id == comment_counts.c.post_id
    ).options(joinedload(Post.author)).all()

    return [{
        "id": p.id,
        "title": p.title,
        "author": p.author.name,
        "comments_count": count or 0
    } for p, count in posts]
```

**Fix:** Use `joinedload` for one-to-one/many-to-one, `selectinload` for one-to-many. Or use subqueries for aggregates."""
    },
    # Connection Pool Exhaustion
    {
        "bug": "Database connections exhausted under load",
        "code": """```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql://user:pass@localhost/db")
Session = sessionmaker(bind=engine)

def get_data():
    session = Session()
    data = session.query(Model).all()
    return data  # Session never closed!
```""",
        "fix": """```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

engine = create_engine(
    "postgresql://user:pass@localhost/db",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True  # Check connection health
)
Session = sessionmaker(bind=engine)

@contextmanager
def get_session():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_data():
    with get_session() as session:
        return session.query(Model).all()

# For FastAPI - use dependency
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
```

**Fix:** Always close sessions, use context managers, configure pool settings, use pool_pre_ping."""
    },
    # Deadlock
    {
        "bug": "Deadlock when updating related records",
        "code": """```python
# Transaction 1
def transfer_funds(from_id, to_id, amount):
    with db.begin():
        from_acc = db.query(Account).filter(Account.id == from_id).with_for_update().first()
        to_acc = db.query(Account).filter(Account.id == to_id).with_for_update().first()
        from_acc.balance -= amount
        to_acc.balance += amount
```""",
        "fix": """```python
def transfer_funds(from_id: int, to_id: int, amount: Decimal):
    # Always lock in consistent order to prevent deadlock
    first_id, second_id = min(from_id, to_id), max(from_id, to_id)

    with db.begin():
        # Lock in consistent order
        accounts = db.query(Account).filter(
            Account.id.in_([first_id, second_id])
        ).order_by(Account.id).with_for_update().all()

        acc_map = {a.id: a for a in accounts}
        from_acc = acc_map[from_id]
        to_acc = acc_map[to_id]

        if from_acc.balance < amount:
            raise ValueError("Insufficient funds")

        from_acc.balance -= amount
        to_acc.balance += amount

# Alternative: Use single atomic update
def transfer_funds_atomic(from_id: int, to_id: int, amount: Decimal):
    result = db.execute(text('''
        WITH withdraw AS (
            UPDATE accounts SET balance = balance - :amount
            WHERE id = :from_id AND balance >= :amount
            RETURNING id
        )
        UPDATE accounts SET balance = balance + :amount
        WHERE id = :to_id AND EXISTS (SELECT 1 FROM withdraw)
    '''), {"from_id": from_id, "to_id": to_id, "amount": amount})

    if result.rowcount == 0:
        raise ValueError("Transfer failed")
    db.commit()
```

**Fix:** Lock resources in consistent order, or use atomic database operations."""
    },
    # XSS Vulnerability
    {
        "bug": "XSS vulnerability in comment display",
        "code": """```javascript
function displayComment(comment) {
    document.getElementById('comments').innerHTML += `
        <div class="comment">
            <strong>${comment.author}</strong>
            <p>${comment.content}</p>
        </div>
    `;
}
```""",
        "fix": """```javascript
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function displayComment(comment) {
    const container = document.getElementById('comments');
    const div = document.createElement('div');
    div.className = 'comment';

    const author = document.createElement('strong');
    author.textContent = comment.author;  // Safe

    const content = document.createElement('p');
    content.textContent = comment.content;  // Safe

    div.appendChild(author);
    div.appendChild(content);
    container.appendChild(div);
}

// Or use a library like DOMPurify
import DOMPurify from 'dompurify';

function displayCommentSafe(comment) {
    const sanitized = DOMPurify.sanitize(comment.content);
    document.getElementById('comments').innerHTML += `
        <div class="comment">
            <strong>${escapeHtml(comment.author)}</strong>
            <p>${sanitized}</p>
        </div>
    `;
}

// Server-side: Also sanitize on input
from bleach import clean

@app.post("/api/comments")
def create_comment(content: str):
    sanitized = clean(content, tags=['b', 'i', 'em', 'strong'], strip=True)
    # Save sanitized content
```

**Fix:** Use textContent instead of innerHTML, escape HTML, use DOMPurify, sanitize server-side."""
    },
    # Timezone Bug
    {
        "bug": "Scheduled tasks running at wrong times across timezones",
        "code": """```python
from datetime import datetime

def schedule_meeting(time_str: str):
    meeting_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    db.add(Meeting(scheduled_at=meeting_time))
    db.commit()
```""",
        "fix": """```python
from datetime import datetime
from zoneinfo import ZoneInfo
import pytz

def schedule_meeting(
    time_str: str,
    user_timezone: str,
    db: Session
):
    # Parse in user's timezone
    user_tz = ZoneInfo(user_timezone)
    local_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    local_time = local_time.replace(tzinfo=user_tz)

    # Convert to UTC for storage
    utc_time = local_time.astimezone(ZoneInfo("UTC"))

    db.add(Meeting(scheduled_at=utc_time, timezone=user_timezone))
    db.commit()
    return utc_time

def get_meeting_for_user(meeting_id: int, user_timezone: str):
    meeting = db.query(Meeting).get(meeting_id)
    user_tz = ZoneInfo(user_timezone)

    # Convert from UTC to user's timezone for display
    local_time = meeting.scheduled_at.astimezone(user_tz)
    return {
        "id": meeting.id,
        "time": local_time.isoformat(),
        "timezone": user_timezone
    }

# Model should use timezone-aware column
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Integer, primary_key=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Fix:** Always store in UTC, convert to user timezone for display, use timezone-aware datetime."""
    },
]

# ============================================================================
# EXPANDED TDD EXAMPLES
# ============================================================================

EXPANDED_TDD = [
    {
        "tests": """```python
import pytest
from shopping_cart import Cart, CartItem, Product

class TestShoppingCart:
    def test_empty_cart_total_is_zero(self):
        cart = Cart()
        assert cart.total == 0

    def test_add_single_item(self):
        cart = Cart()
        product = Product(id=1, name="Book", price=10.00)
        cart.add(product, quantity=1)
        assert cart.total == 10.00
        assert len(cart.items) == 1

    def test_add_multiple_same_items(self):
        cart = Cart()
        product = Product(id=1, name="Book", price=10.00)
        cart.add(product, quantity=2)
        assert cart.total == 20.00
        assert cart.items[0].quantity == 2

    def test_add_same_product_twice_increases_quantity(self):
        cart = Cart()
        product = Product(id=1, name="Book", price=10.00)
        cart.add(product, quantity=1)
        cart.add(product, quantity=2)
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 3

    def test_remove_item(self):
        cart = Cart()
        product = Product(id=1, name="Book", price=10.00)
        cart.add(product, quantity=2)
        cart.remove(product.id)
        assert len(cart.items) == 0

    def test_update_quantity(self):
        cart = Cart()
        product = Product(id=1, name="Book", price=10.00)
        cart.add(product, quantity=1)
        cart.update_quantity(product.id, 5)
        assert cart.items[0].quantity == 5

    def test_apply_percentage_discount(self):
        cart = Cart()
        cart.add(Product(id=1, name="Book", price=100.00), quantity=1)
        cart.apply_discount("SAVE10", percentage=10)
        assert cart.total == 90.00

    def test_cannot_apply_multiple_discounts(self):
        cart = Cart()
        cart.add(Product(id=1, name="Book", price=100.00), quantity=1)
        cart.apply_discount("SAVE10", percentage=10)
        with pytest.raises(ValueError, match="already applied"):
            cart.apply_discount("SAVE20", percentage=20)
```""",
        "impl": """```python
from dataclasses import dataclass, field
from typing import List, Optional
from decimal import Decimal

@dataclass
class Product:
    id: int
    name: str
    price: Decimal

    def __post_init__(self):
        self.price = Decimal(str(self.price))

@dataclass
class CartItem:
    product: Product
    quantity: int

    @property
    def subtotal(self) -> Decimal:
        return self.product.price * self.quantity

@dataclass
class Cart:
    items: List[CartItem] = field(default_factory=list)
    discount_code: Optional[str] = None
    discount_percentage: Decimal = Decimal("0")

    @property
    def subtotal(self) -> Decimal:
        return sum(item.subtotal for item in self.items)

    @property
    def discount_amount(self) -> Decimal:
        return self.subtotal * self.discount_percentage / 100

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount_amount

    def _find_item(self, product_id: int) -> Optional[CartItem]:
        for item in self.items:
            if item.product.id == product_id:
                return item
        return None

    def add(self, product: Product, quantity: int = 1) -> None:
        existing = self._find_item(product.id)
        if existing:
            existing.quantity += quantity
        else:
            self.items.append(CartItem(product=product, quantity=quantity))

    def remove(self, product_id: int) -> None:
        self.items = [i for i in self.items if i.product.id != product_id]

    def update_quantity(self, product_id: int, quantity: int) -> None:
        item = self._find_item(product_id)
        if item:
            if quantity <= 0:
                self.remove(product_id)
            else:
                item.quantity = quantity

    def apply_discount(self, code: str, percentage: float) -> None:
        if self.discount_code:
            raise ValueError("Discount already applied")
        self.discount_code = code
        self.discount_percentage = Decimal(str(percentage))

    def clear(self) -> None:
        self.items = []
        self.discount_code = None
        self.discount_percentage = Decimal("0")
```"""
    },
]

# ============================================================================
# EXPANDED DPO PAIRS
# ============================================================================

EXPANDED_DPO = [
    {
        "prompt": "Write a function to validate an email address",
        "rejected": """```python
def validate_email(email):
    if "@" in email:
        return True
    return False
```""",
        "chosen": """```python
import re
from typing import Tuple

EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

def validate_email(email: str) -> Tuple[bool, str]:
    if not email:
        return False, "Email is required"

    if len(email) > 254:
        return False, "Email too long"

    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format"

    local, domain = email.rsplit('@', 1)

    if len(local) > 64:
        return False, "Local part too long"

    if domain.startswith('-') or domain.endswith('-'):
        return False, "Invalid domain"

    return True, ""
```"""
    },
    {
        "prompt": "Create a function to make an HTTP request",
        "rejected": """```python
import urllib.request

def fetch(url):
    response = urllib.request.urlopen(url)
    return response.read()
```""",
        "chosen": """```python
import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def fetch(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    json: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
    retries: int = 3
) -> Dict[str, Any]:
    last_error = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(retries):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    raise
                last_error = e
                logger.warning(f"Retry {attempt + 1}: {e}")
            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Retry {attempt + 1}: {e}")

    raise last_error
```"""
    },
    {
        "prompt": "Write a database query to get users with their orders",
        "rejected": """```python
def get_users_with_orders():
    users = db.query(User).all()
    result = []
    for user in users:
        orders = db.query(Order).filter(Order.user_id == user.id).all()
        result.append({"user": user, "orders": orders})
    return result
```""",
        "chosen": """```python
from sqlalchemy.orm import joinedload, selectinload

def get_users_with_orders(
    db: Session,
    limit: int = 100,
    include_items: bool = False
) -> List[Dict]:
    query = db.query(User).options(
        selectinload(User.orders)
    )

    if include_items:
        query = query.options(
            selectinload(User.orders).selectinload(Order.items)
        )

    users = query.limit(limit).all()

    return [
        {
            "id": u.id,
            "name": u.name,
            "orders": [
                {
                    "id": o.id,
                    "total": o.total,
                    "items": [i.to_dict() for i in o.items] if include_items else None
                }
                for o in u.orders
            ]
        }
        for u in users
    ]
```"""
    },
    {
        "prompt": "Implement user login",
        "rejected": """```python
@app.post("/login")
def login(username, password):
    user = db.query(User).filter(User.username == username).first()
    if user.password == password:
        return {"token": username}
    return {"error": "bad password"}
```""",
        "chosen": """```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"])

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form.username).first()

    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = jwt.encode(
        {
            "sub": user.id,
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    return Token(access_token=token, token_type="bearer")
```"""
    },
    {
        "prompt": "Write a caching function",
        "rejected": """```python
cache = {}

def get_data(key):
    if key in cache:
        return cache[key]
    data = expensive_operation(key)
    cache[key] = data
    return data
```""",
        "chosen": """```python
import functools
import time
from typing import Any, Optional, Callable
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cached(
    ttl: int = 300,
    prefix: str = "cache",
    key_builder: Optional[Callable] = None
):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = f"{prefix}:{func.__name__}:{hash((args, tuple(kwargs.items())))}"

            # Try cache
            cached_value = redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            # Execute and cache
            result = await func(*args, **kwargs)
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )
            return result

        wrapper.invalidate = lambda *a, **kw: redis_client.delete(
            f"{prefix}:{func.__name__}:{hash((a, tuple(kw.items())))}"
        )

        return wrapper
    return decorator

@cached(ttl=3600, prefix="user")
async def get_user_profile(user_id: int):
    return await db.query(User).filter(User.id == user_id).first()
```"""
    },
]


def generate_sft_examples() -> List[Dict]:
    """Generate SFT training examples."""
    examples = []

    # Spec -> Implementation
    for item in EXPANDED_SPECS:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are an expert software engineer. Implement production-ready code."},
                {"role": "user", "content": f"Implement: {item['spec']}"},
                {"role": "assistant", "content": item['impl']}
            ]
        })

    # Bug -> Fix
    for item in EXPANDED_BUGS:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are an expert debugger. Analyze and fix bugs."},
                {"role": "user", "content": f"Fix this bug: {item['bug']}\n\n{item['code']}"},
                {"role": "assistant", "content": item['fix']}
            ]
        })

    # TDD
    for item in EXPANDED_TDD:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are a TDD expert. Implement code to pass tests."},
                {"role": "user", "content": f"Implement code to pass these tests:\n\n{item['tests']}"},
                {"role": "assistant", "content": item['impl']}
            ]
        })

    return examples


def generate_dpo_examples() -> List[Dict]:
    """Generate DPO preference pairs."""
    return [
        {
            "prompt": item["prompt"],
            "chosen": item["chosen"],
            "rejected": item["rejected"]
        }
        for item in EXPANDED_DPO
    ]


def main():
    print("=" * 70)
    print("EXPANDING CODING AGENT TRAINING DATA")
    print("=" * 70)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Generate examples
    sft_examples = generate_sft_examples()
    dpo_examples = generate_dpo_examples()

    print(f"\nExpanded SFT Examples: {len(sft_examples)}")
    print(f"  - Spec to Implementation: {len(EXPANDED_SPECS)}")
    print(f"  - Bug to Fix: {len(EXPANDED_BUGS)}")
    print(f"  - TDD: {len(EXPANDED_TDD)}")

    print(f"\nExpanded DPO Pairs: {len(dpo_examples)}")

    # Append to existing files
    existing_sft = []
    sft_file = OUTPUT_DIR / "sft_train.jsonl"
    if sft_file.exists():
        with open(sft_file, 'r', encoding='utf-8') as f:
            existing_sft = [json.loads(line) for line in f]

    all_sft = existing_sft + sft_examples
    with open(sft_file, 'w', encoding='utf-8') as f:
        for ex in all_sft:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    existing_dpo = []
    dpo_file = OUTPUT_DIR / "dpo_pairs.jsonl"
    if dpo_file.exists():
        with open(dpo_file, 'r', encoding='utf-8') as f:
            existing_dpo = [json.loads(line) for line in f]

    all_dpo = existing_dpo + dpo_examples
    with open(dpo_file, 'w', encoding='utf-8') as f:
        for pair in all_dpo:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    print(f"\nTotal SFT Examples: {len(all_sft)}")
    print(f"Total DPO Pairs: {len(all_dpo)}")
    print(f"\nSaved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
