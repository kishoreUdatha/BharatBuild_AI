#!/usr/bin/env python3
"""
Generate Claude-Style Training Data - Minimal Version
"""

import json
from pathlib import Path
from typing import List, Dict

OUTPUT_DIR = Path(__file__).parent / "claude_style_data"

SYSTEM_PROMPT = """You are an expert software engineer. Respond with this structure:

PLAN:
1) First step
2) Second step

FILES:
- path/to/file.py

PATCH:
*** Begin Patch
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -1,3 +1,5 @@
 context
-removed
+added
*** End Patch

COMMANDS:
- pytest tests/

NOTES:
- Important notes"""


def load_examples_from_file(filepath: str) -> List[Dict]:
    """Load examples from a JSON file."""
    examples = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
    return examples


# Inline examples as data structures instead of complex f-strings
SFT_EXAMPLES = [
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Implement JWT authentication with FastAPI."},
            {"role": "assistant", "content": """PLAN:
1) Create User model with password hashing
2) Implement JWT token generation
3) Create auth endpoints

FILES:
- backend/app/models/user.py
- backend/app/core/security.py
- backend/app/api/auth.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/models/user.py
@@ -0,0 +1,20 @@
+from sqlalchemy import Column, Integer, String, Boolean
+from passlib.context import CryptContext
+from app.db.base import Base
+
+pwd_context = CryptContext(schemes=["bcrypt"])
+
+class User(Base):
+    __tablename__ = "users"
+    id = Column(Integer, primary_key=True)
+    email = Column(String, unique=True)
+    password_hash = Column(String)
+    is_active = Column(Boolean, default=True)
+
+    def set_password(self, password: str):
+        self.password_hash = pwd_context.hash(password)
+
+    def verify_password(self, password: str) -> bool:
+        return pwd_context.verify(password, self.password_hash)
*** End Patch

COMMANDS:
- cd backend && alembic upgrade head
- cd backend && pytest tests/test_auth.py -v

NOTES:
- SECRET_KEY must be set in environment
- Add rate limiting for production"""}
        ],
        "category": "spec_to_implementation"
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Create a REST API for blog posts with pagination."},
            {"role": "assistant", "content": """PLAN:
1) Create Post model
2) Implement CRUD endpoints
3) Add pagination

FILES:
- backend/app/models/post.py
- backend/app/api/posts.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/app/api/posts.py
@@ -0,0 +1,35 @@
+from fastapi import APIRouter, Depends, Query
+from sqlalchemy.orm import Session
+from typing import Optional
+
+router = APIRouter(prefix="/api/posts")
+
+@router.get("/")
+async def list_posts(
+    page: int = Query(1, ge=1),
+    per_page: int = Query(20, ge=1, le=100),
+    search: Optional[str] = None,
+    db: Session = Depends(get_db)
+):
+    query = db.query(Post)
+    if search:
+        query = query.filter(Post.title.ilike(f"%{search}%"))
+
+    total = query.count()
+    posts = query.offset((page-1)*per_page).limit(per_page).all()
+
+    return {"items": posts, "total": total, "page": page}
+
+@router.post("/", status_code=201)
+async def create_post(data: PostCreate, user=Depends(get_current_user), db=Depends(get_db)):
+    post = Post(**data.dict(), author_id=user.id)
+    db.add(post)
+    db.commit()
+    return post
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_posts.py -v

NOTES:
- Add full-text search for large datasets"""}
        ],
        "category": "spec_to_implementation"
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Fix database connection pool exhaustion error."},
            {"role": "assistant", "content": """PLAN:
1) Add context manager for session cleanup
2) Configure connection pool
3) Create FastAPI dependency

FILES:
- backend/app/db/session.py

PATCH:
*** Begin Patch
--- a/backend/app/db/session.py
+++ b/backend/app/db/session.py
@@ -1,8 +1,25 @@
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
 SessionLocal = sessionmaker(bind=engine)

-def get_user(user_id):
-    session = SessionLocal()
-    return session.query(User).get(user_id)
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
- pool_pre_ping checks connection health"""}
        ],
        "category": "bug_fix"
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Fix SQL injection vulnerability in search endpoint."},
            {"role": "assistant", "content": """PLAN:
1) Use parameterized queries
2) Add input validation
3) Use ORM instead of raw SQL

FILES:
- backend/app/api/search.py

PATCH:
*** Begin Patch
--- a/backend/app/api/search.py
+++ b/backend/app/api/search.py
@@ -1,5 +1,15 @@
+from fastapi import Query
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
- cd backend && pytest tests/test_search_security.py -v

NOTES:
- ORM escapes parameters automatically
- Always validate input length"""}
        ],
        "category": "bug_fix"
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Fix N+1 query problem in posts endpoint."},
            {"role": "assistant", "content": """PLAN:
1) Use eager loading with joinedload
2) Optimize query

FILES:
- backend/app/api/posts.py

PATCH:
*** Begin Patch
--- a/backend/app/api/posts.py
+++ b/backend/app/api/posts.py
@@ -1,5 +1,10 @@
+from sqlalchemy.orm import joinedload
+
 @app.get("/posts")
 def get_posts(db=Depends(get_db)):
-    posts = db.query(Post).all()
-    return [{"title": p.title, "author": p.author.name} for p in posts]
+    posts = db.query(Post).options(
+        joinedload(Post.author)
+    ).all()
+    return [{"title": p.title, "author": p.author.name} for p in posts]
*** End Patch

COMMANDS:
- cd backend && SQLALCHEMY_ECHO=1 pytest tests/test_posts.py -v

NOTES:
- joinedload for many-to-one relations
- selectinload for one-to-many"""}
        ],
        "category": "bug_fix"
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Fix race condition in purchase endpoint."},
            {"role": "assistant", "content": """PLAN:
1) Add row-level locking
2) Use atomic database update
3) Add idempotency key

FILES:
- backend/app/api/purchase.py

PATCH:
*** Begin Patch
--- a/backend/app/api/purchase.py
+++ b/backend/app/api/purchase.py
@@ -1,10 +1,25 @@
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
+    order = Order(user_id=user.id, product_id=product_id)
+    db.add(order)
+    db.commit()
*** End Patch

COMMANDS:
- cd backend && pytest tests/test_purchase_concurrent.py -v

NOTES:
- Atomic UPDATE prevents race condition
- Add idempotency key to prevent duplicates"""}
        ],
        "category": "bug_fix"
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Add unit tests for payment service."},
            {"role": "assistant", "content": """PLAN:
1) Create test fixtures
2) Add unit tests with mocks
3) Add error case tests

FILES:
- backend/tests/test_payment.py
- backend/tests/conftest.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/backend/tests/test_payment.py
@@ -0,0 +1,40 @@
+import pytest
+from decimal import Decimal
+from unittest.mock import MagicMock
+
+class TestPaymentService:
+    def test_process_payment_success(self, db_session, mock_stripe):
+        user = User(id=1, email="test@example.com")
+        db_session.add(user)
+        db_session.commit()
+
+        service = PaymentService(mock_stripe, db_session)
+        result = service.process_payment(user_id=1, amount=Decimal("99.99"))
+
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
+    @pytest.mark.parametrize("amount,cents", [
+        (Decimal("1.00"), 100),
+        (Decimal("99.99"), 9999),
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
- cd backend && pytest tests/test_payment.py -v --cov

NOTES:
- Use fixtures for common setup
- Mock external services"""}
        ],
        "category": "add_tests"
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Implement RBAC for API endpoints."},
            {"role": "assistant", "content": """PLAN:
1) Create Role and Permission models
2) Implement permission checker
3) Create FastAPI dependency

FILES:
- backend/app/models/rbac.py
- backend/app/core/permissions.py

PATCH:
*** Begin Patch
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
+        return f"{resource}:{action}" in perms
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
- cd backend && pytest tests/test_permissions.py -v

NOTES:
- Redis caching for performance
- Invalidate cache on role changes"""}
        ],
        "category": "security"
    },
]

DPO_PAIRS = [
    {
        "prompt": "Write a function to read a file",
        "rejected": "def read_file(f):\n    return open(f).read()",
        "chosen": "def read_file(path: str) -> str:\n    with open(path, 'r') as f:\n        return f.read()"
    },
    {
        "prompt": "Create a login endpoint",
        "rejected": "@app.post('/login')\ndef login(u, p):\n    if db.get(u).password == p:\n        return {'ok': True}",
        "chosen": "@app.post('/login')\nasync def login(form: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):\n    user = db.query(User).filter(User.email == form.username).first()\n    if not user or not pwd_context.verify(form.password, user.password_hash):\n        raise HTTPException(401)\n    return {'access_token': create_token(user.id)}"
    },
    {
        "prompt": "Query users with posts",
        "rejected": "users = db.query(User).all()\nfor u in users:\n    u.posts = db.query(Post).filter(Post.user_id == u.id).all()",
        "chosen": "users = db.query(User).options(joinedload(User.posts)).all()"
    },
    {
        "prompt": "Validate email",
        "rejected": "def valid(e): return '@' in e",
        "chosen": "import re\nEMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$')\ndef validate_email(email: str) -> bool:\n    return bool(EMAIL_RE.match(email))"
    },
    {
        "prompt": "Hash password",
        "rejected": "import hashlib\ndef hash_pw(p): return hashlib.md5(p.encode()).hexdigest()",
        "chosen": "from passlib.context import CryptContext\npwd = CryptContext(schemes=['bcrypt'])\ndef hash_password(password: str) -> str:\n    return pwd.hash(password)"
    },
]


def main():
    print("=" * 60)
    print("GENERATING CLAUDE-STYLE TRAINING DATA")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Count categories
    categories = {}
    for ex in SFT_EXAMPLES:
        cat = ex.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nSFT Examples: {len(SFT_EXAMPLES)}")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    # Save SFT
    sft_file = OUTPUT_DIR / "claude_style_sft.jsonl"
    with open(sft_file, 'w', encoding='utf-8') as f:
        for ex in SFT_EXAMPLES:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')
    print(f"\nSaved SFT to: {sft_file}")

    # Save DPO
    print(f"\nDPO Pairs: {len(DPO_PAIRS)}")
    dpo_file = OUTPUT_DIR / "claude_style_dpo.jsonl"
    with open(dpo_file, 'w', encoding='utf-8') as f:
        for pair in DPO_PAIRS:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')
    print(f"Saved DPO to: {dpo_file}")

    # Config
    config = {
        "version": "claude_style_v1",
        "sft_examples": len(SFT_EXAMPLES),
        "dpo_pairs": len(DPO_PAIRS),
        "categories": categories,
        "output_format": ["PLAN", "FILES", "PATCH", "COMMANDS", "NOTES"]
    }
    with open(OUTPUT_DIR / "config.json", 'w') as f:
        json.dump(config, f, indent=2)

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
