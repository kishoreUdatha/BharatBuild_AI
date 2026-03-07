#!/usr/bin/env python3
"""
Generate Claude-Style Training Data for Qwen Fine-tuning

Output Contract:
- PLAN: Short numbered steps
- FILES: Explicit file paths
- PATCH: Unified diff format
- COMMANDS: Build/test commands
- NOTES: Assumptions and caveats

Target: 500-2000 gold samples covering:
1. Spec -> Multi-file implementation
2. Bug -> Fix with error logs
3. Add tests + make tests pass
4. Refactor to best practices
5. Security patterns (JWT, RBAC, validation)
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent / "claude_style_data"

# ============================================================================
# OUTPUT CONTRACT TEMPLATE
# ============================================================================

OUTPUT_TEMPLATE = """PLAN:
{plan}

FILES:
{files}

PATCH:
*** Begin Patch
{patch}
*** End Patch

COMMANDS:
{commands}

NOTES:
{notes}"""

# ============================================================================
# SYSTEM PROMPT FOR CLAUDE-STYLE RESPONSES
# ============================================================================

SYSTEM_PROMPT = """You are an expert software engineer. When given a task, you MUST respond with this exact structure:

PLAN:
1) First step
2) Second step
...

FILES:
- path/to/file1.py
- path/to/file2.ts
...

PATCH:
*** Begin Patch
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -line,count +line,count @@
 context
-removed line
+added line
 context
*** End Patch

COMMANDS:
- command1
- command2

NOTES:
- Important assumption or caveat

Always use unified diff format. Be precise with file paths. Include all necessary changes."""

# ============================================================================
# 1. SPEC -> MULTI-FILE IMPLEMENTATION
# ============================================================================

SPEC_TO_IMPLEMENTATION = [
    # FastAPI + React Auth System
    {
        "category": "spec_to_implementation",
        "user": """Implement a complete authentication system with:
- FastAPI backend with JWT authentication
- React frontend with login/register forms
- PostgreSQL database with SQLAlchemy
- Password reset via email""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Create User model with password hashing
2) Implement JWT token generation and validation
3) Create auth endpoints (register, login, refresh, reset)
4) Build React auth context and protected routes
5) Add email service for password reset""",
            files="""- backend/app/models/user.py
- backend/app/api/auth.py
- backend/app/core/security.py
- backend/app/services/email.py
- frontend/src/contexts/AuthContext.tsx
- frontend/src/pages/Login.tsx
- frontend/src/pages/Register.tsx""",
            patch="""--- /dev/null
+++ b/backend/app/models/user.py
@@ -0,0 +1,35 @@
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
+    name = Column(String, nullable=False)
+    is_active = Column(Boolean, default=True)
+    is_verified = Column(Boolean, default=False)
+    created_at = Column(DateTime(timezone=True), server_default=func.now())
+    reset_token = Column(String, nullable=True)
+    reset_token_expires = Column(DateTime, nullable=True)
+
+    def set_password(self, password: str):
+        self.password_hash = pwd_context.hash(password)
+
+    def verify_password(self, password: str) -> bool:
+        return pwd_context.verify(password, self.password_hash)
+
+--- /dev/null
+++ b/backend/app/core/security.py
@@ -0,0 +1,45 @@
+from datetime import datetime, timedelta
+from typing import Optional
+from jose import JWTError, jwt
+from fastapi import HTTPException, status, Depends
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
+        {"sub": str(user_id), "exp": expire},
+        settings.SECRET_KEY,
+        algorithm="HS256"
+    )
+
+def create_refresh_token(user_id: int) -> str:
+    expire = datetime.utcnow() + timedelta(days=7)
+    return jwt.encode(
+        {"sub": str(user_id), "exp": expire, "type": "refresh"},
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
+        detail="Could not validate credentials",
+        headers={"WWW-Authenticate": "Bearer"},
+    )
+    try:
+        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
+        user_id = int(payload.get("sub"))
+    except JWTError:
+        raise credentials_exception
+
+    user = db.query(User).filter(User.id == user_id).first()
+    if not user or not user.is_active:
+        raise credentials_exception
+    return user

--- /dev/null
+++ b/backend/app/api/auth.py
@@ -0,0 +1,95 @@
+from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
+from fastapi.security import OAuth2PasswordRequestForm
+from sqlalchemy.orm import Session
+from pydantic import BaseModel, EmailStr
+from datetime import datetime, timedelta
+import secrets
+
+from app.db.session import get_db
+from app.models.user import User
+from app.core.security import create_access_token, create_refresh_token, get_current_user
+from app.services.email import send_reset_email
+
+router = APIRouter(prefix="/api/auth", tags=["Authentication"])
+
+class UserCreate(BaseModel):
+    email: EmailStr
+    password: str
+    name: str
+
+class TokenResponse(BaseModel):
+    access_token: str
+    refresh_token: str
+    token_type: str = "bearer"
+
+class PasswordReset(BaseModel):
+    email: EmailStr
+
+class PasswordResetConfirm(BaseModel):
+    token: str
+    new_password: str
+
+@router.post("/register", status_code=201)
+async def register(data: UserCreate, db: Session = Depends(get_db)):
+    if db.query(User).filter(User.email == data.email).first():
+        raise HTTPException(status_code=400, detail="Email already registered")
+
+    user = User(email=data.email, name=data.name)
+    user.set_password(data.password)
+    db.add(user)
+    db.commit()
+    return {"message": "User created successfully"}
+
+@router.post("/login", response_model=TokenResponse)
+async def login(
+    form: OAuth2PasswordRequestForm = Depends(),
+    db: Session = Depends(get_db)
+):
+    user = db.query(User).filter(User.email == form.username).first()
+    if not user or not user.verify_password(form.password):
+        raise HTTPException(status_code=401, detail="Invalid credentials")
+
+    return TokenResponse(
+        access_token=create_access_token(user.id),
+        refresh_token=create_refresh_token(user.id)
+    )
+
+@router.post("/reset-password")
+async def request_reset(
+    data: PasswordReset,
+    background_tasks: BackgroundTasks,
+    db: Session = Depends(get_db)
+):
+    user = db.query(User).filter(User.email == data.email).first()
+    if user:
+        token = secrets.token_urlsafe(32)
+        user.reset_token = token
+        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
+        db.commit()
+        background_tasks.add_task(send_reset_email, user.email, token)
+    return {"message": "If email exists, reset link sent"}
+
+@router.post("/reset-password/confirm")
+async def confirm_reset(data: PasswordResetConfirm, db: Session = Depends(get_db)):
+    user = db.query(User).filter(
+        User.reset_token == data.token,
+        User.reset_token_expires > datetime.utcnow()
+    ).first()
+
+    if not user:
+        raise HTTPException(status_code=400, detail="Invalid or expired token")
+
+    user.set_password(data.new_password)
+    user.reset_token = None
+    user.reset_token_expires = None
+    db.commit()
+    return {"message": "Password reset successful"}

--- /dev/null
+++ b/frontend/src/contexts/AuthContext.tsx
@@ -0,0 +1,65 @@
+import React, { createContext, useContext, useState, useEffect } from 'react';
+import { api } from '../lib/api';
+
+interface User {
+  id: number;
+  email: string;
+  name: string;
+}
+
+interface AuthContextType {
+  user: User | null;
+  loading: boolean;
+  login: (email: string, password: string) => Promise<void>;
+  logout: () => void;
+  register: (email: string, password: string, name: string) => Promise<void>;
+}
+
+const AuthContext = createContext<AuthContextType | undefined>(undefined);
+
+export function AuthProvider({ children }: { children: React.ReactNode }) {
+  const [user, setUser] = useState<User | null>(null);
+  const [loading, setLoading] = useState(true);
+
+  useEffect(() => {
+    const token = localStorage.getItem('access_token');
+    if (token) {
+      api.get('/auth/me')
+        .then(res => setUser(res.data))
+        .catch(() => localStorage.removeItem('access_token'))
+        .finally(() => setLoading(false));
+    } else {
+      setLoading(false);
+    }
+  }, []);
+
+  const login = async (email: string, password: string) => {
+    const formData = new FormData();
+    formData.append('username', email);
+    formData.append('password', password);
+
+    const { data } = await api.post('/auth/login', formData);
+    localStorage.setItem('access_token', data.access_token);
+    localStorage.setItem('refresh_token', data.refresh_token);
+
+    const userRes = await api.get('/auth/me');
+    setUser(userRes.data);
+  };
+
+  const logout = () => {
+    localStorage.removeItem('access_token');
+    localStorage.removeItem('refresh_token');
+    setUser(null);
+  };
+
+  const register = async (email: string, password: string, name: string) => {
+    await api.post('/auth/register', { email, password, name });
+  };
+
+  return (
+    <AuthContext.Provider value={{ user, loading, login, logout, register }}>
+      {children}
+    </AuthContext.Provider>
+  );
+}
+
+export const useAuth = () => {
+  const context = useContext(AuthContext);
+  if (!context) throw new Error('useAuth must be used within AuthProvider');
+  return context;
+};""",
            commands="""- cd backend && alembic upgrade head
- cd backend && pytest tests/test_auth.py -v
- cd frontend && npm test
- cd frontend && npm run build""",
            notes="""- SECRET_KEY must be set in environment
- Email service requires SMTP configuration
- Add rate limiting to login endpoint for production
- Consider adding OAuth providers (Google, GitHub)"""
        )
    },

    # E-commerce Order System
    {
        "category": "spec_to_implementation",
        "user": """Build an order management system with:
- Order creation with inventory check
- Payment integration (Stripe)
- Order status webhooks
- Admin dashboard API""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Create Order and OrderItem models
2) Implement inventory check with locking
3) Integrate Stripe payment intent
4) Set up webhook handler for payment events
5) Build admin endpoints with filtering""",
            files="""- backend/app/models/order.py
- backend/app/api/orders.py
- backend/app/services/payment.py
- backend/app/api/webhooks.py
- backend/app/api/admin/orders.py""",
            patch="""--- /dev/null
+++ b/backend/app/models/order.py
@@ -0,0 +1,45 @@
+from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Enum
+from sqlalchemy.orm import relationship
+from sqlalchemy.sql import func
+import enum
+from app.db.base import Base
+
+class OrderStatus(enum.Enum):
+    PENDING = "pending"
+    PAID = "paid"
+    PROCESSING = "processing"
+    SHIPPED = "shipped"
+    DELIVERED = "delivered"
+    CANCELLED = "cancelled"
+
+class Order(Base):
+    __tablename__ = "orders"
+
+    id = Column(Integer, primary_key=True)
+    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
+    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
+    total = Column(Numeric(10, 2), nullable=False)
+    stripe_payment_intent = Column(String, nullable=True)
+    shipping_address = Column(String, nullable=False)
+    created_at = Column(DateTime(timezone=True), server_default=func.now())
+    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
+
+    items = relationship("OrderItem", back_populates="order")
+    user = relationship("User")
+
+class OrderItem(Base):
+    __tablename__ = "order_items"
+
+    id = Column(Integer, primary_key=True)
+    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
+    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
+    quantity = Column(Integer, nullable=False)
+    unit_price = Column(Numeric(10, 2), nullable=False)
+
+    order = relationship("Order", back_populates="items")
+    product = relationship("Product")

--- /dev/null
+++ b/backend/app/services/payment.py
@@ -0,0 +1,55 @@
+import stripe
+from decimal import Decimal
+from app.core.config import settings
+from app.models.order import Order, OrderStatus
+
+stripe.api_key = settings.STRIPE_SECRET_KEY
+
+class PaymentService:
+    @staticmethod
+    def create_payment_intent(order: Order) -> dict:
+        intent = stripe.PaymentIntent.create(
+            amount=int(order.total * 100),  # cents
+            currency="usd",
+            metadata={"order_id": order.id},
+            automatic_payment_methods={"enabled": True}
+        )
+        return {
+            "client_secret": intent.client_secret,
+            "payment_intent_id": intent.id
+        }
+
+    @staticmethod
+    def handle_webhook(payload: bytes, signature: str) -> dict:
+        try:
+            event = stripe.Webhook.construct_event(
+                payload, signature, settings.STRIPE_WEBHOOK_SECRET
+            )
+        except stripe.error.SignatureVerificationError:
+            raise ValueError("Invalid signature")
+
+        return {
+            "type": event.type,
+            "data": event.data.object
+        }
+
+    @staticmethod
+    def process_payment_success(db, payment_intent_id: str):
+        order = db.query(Order).filter(
+            Order.stripe_payment_intent == payment_intent_id
+        ).first()
+
+        if order:
+            order.status = OrderStatus.PAID
+            db.commit()
+            return order
+        return None
+
+    @staticmethod
+    def refund_payment(payment_intent_id: str, amount: int = None):
+        refund_params = {"payment_intent": payment_intent_id}
+        if amount:
+            refund_params["amount"] = amount
+        return stripe.Refund.create(**refund_params)

--- /dev/null
+++ b/backend/app/api/orders.py
@@ -0,0 +1,75 @@
+from fastapi import APIRouter, Depends, HTTPException
+from sqlalchemy.orm import Session
+from sqlalchemy import select
+from typing import List
+from pydantic import BaseModel
+from decimal import Decimal
+
+from app.db.session import get_db
+from app.models.order import Order, OrderItem, OrderStatus
+from app.models.product import Product
+from app.core.security import get_current_user
+from app.services.payment import PaymentService
+
+router = APIRouter(prefix="/api/orders", tags=["Orders"])
+
+class OrderItemCreate(BaseModel):
+    product_id: int
+    quantity: int
+
+class OrderCreate(BaseModel):
+    items: List[OrderItemCreate]
+    shipping_address: str
+
+@router.post("/", status_code=201)
+async def create_order(
+    data: OrderCreate,
+    user = Depends(get_current_user),
+    db: Session = Depends(get_db)
+):
+    # Lock products for update to prevent race conditions
+    product_ids = [item.product_id for item in data.items]
+    products = db.execute(
+        select(Product)
+        .where(Product.id.in_(product_ids))
+        .with_for_update()
+    ).scalars().all()
+
+    product_map = {p.id: p for p in products}
+
+    # Validate inventory
+    total = Decimal("0")
+    order_items = []
+
+    for item in data.items:
+        product = product_map.get(item.product_id)
+        if not product:
+            raise HTTPException(404, f"Product {item.product_id} not found")
+        if product.stock < item.quantity:
+            raise HTTPException(400, f"Insufficient stock for {product.name}")
+
+        product.stock -= item.quantity
+        subtotal = product.price * item.quantity
+        total += subtotal
+        order_items.append({
+            "product_id": item.product_id,
+            "quantity": item.quantity,
+            "unit_price": product.price
+        })
+
+    # Create order
+    order = Order(
+        user_id=user.id,
+        total=total,
+        shipping_address=data.shipping_address
+    )
+    db.add(order)
+    db.flush()
+
+    for item_data in order_items:
+        db.add(OrderItem(order_id=order.id, **item_data))
+
+    # Create payment intent
+    payment = PaymentService.create_payment_intent(order)
+    order.stripe_payment_intent = payment["payment_intent_id"]
+
+    db.commit()
+
+    return {"order_id": order.id, "client_secret": payment["client_secret"]}""",
            commands="""- cd backend && alembic upgrade head
- cd backend && pytest tests/test_orders.py -v
- stripe listen --forward-to localhost:8000/api/webhooks/stripe""",
            notes="""- Uses database-level locking to prevent overselling
- Stripe webhook requires endpoint verification
- Consider adding idempotency keys for order creation
- Add background job for order confirmation emails"""
        )
    },

    # Microservices API Gateway
    {
        "category": "spec_to_implementation",
        "user": """Create an API Gateway with:
- Rate limiting per user/IP
- Request routing to microservices
- Circuit breaker pattern
- Request/response logging""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Set up FastAPI gateway with service registry
2) Implement Redis-based rate limiting
3) Add circuit breaker with failure tracking
4) Create request routing middleware
5) Add structured logging with correlation IDs""",
            files="""- gateway/app/main.py
- gateway/app/middleware/rate_limiter.py
- gateway/app/middleware/circuit_breaker.py
- gateway/app/services/router.py
- gateway/app/core/logging.py""",
            patch="""--- /dev/null
+++ b/gateway/app/middleware/rate_limiter.py
@@ -0,0 +1,65 @@
+import time
+import redis
+from fastapi import Request, HTTPException
+from starlette.middleware.base import BaseHTTPMiddleware
+from typing import Optional
+
+redis_client = redis.Redis(host="localhost", port=6379, db=0)
+
+class RateLimiter:
+    def __init__(
+        self,
+        requests_per_minute: int = 60,
+        requests_per_hour: int = 1000
+    ):
+        self.rpm = requests_per_minute
+        self.rph = requests_per_hour
+
+    def get_identifier(self, request: Request) -> str:
+        # Try user ID from JWT
+        if hasattr(request.state, "user_id"):
+            return f"user:{request.state.user_id}"
+        # Fall back to IP
+        forwarded = request.headers.get("X-Forwarded-For")
+        ip = forwarded.split(",")[0] if forwarded else request.client.host
+        return f"ip:{ip}"
+
+    def check_limit(self, identifier: str) -> tuple[bool, dict]:
+        now = int(time.time())
+        pipe = redis_client.pipeline()
+
+        # Minute window
+        minute_key = f"rate:{identifier}:m:{now // 60}"
+        pipe.incr(minute_key)
+        pipe.expire(minute_key, 120)
+
+        # Hour window
+        hour_key = f"rate:{identifier}:h:{now // 3600}"
+        pipe.incr(hour_key)
+        pipe.expire(hour_key, 7200)
+
+        results = pipe.execute()
+        minute_count = results[0]
+        hour_count = results[2]
+
+        headers = {
+            "X-RateLimit-Limit": str(self.rpm),
+            "X-RateLimit-Remaining": str(max(0, self.rpm - minute_count)),
+            "X-RateLimit-Reset": str((now // 60 + 1) * 60)
+        }
+
+        if minute_count > self.rpm or hour_count > self.rph:
+            return False, headers
+        return True, headers
+
+class RateLimitMiddleware(BaseHTTPMiddleware):
+    def __init__(self, app, limiter: RateLimiter):
+        super().__init__(app)
+        self.limiter = limiter
+
+    async def dispatch(self, request: Request, call_next):
+        identifier = self.limiter.get_identifier(request)
+        allowed, headers = self.limiter.check_limit(identifier)
+
+        if not allowed:
+            raise HTTPException(429, "Rate limit exceeded", headers=headers)
+
+        response = await call_next(request)
+        for key, value in headers.items():
+            response.headers[key] = value
+        return response

--- /dev/null
+++ b/gateway/app/middleware/circuit_breaker.py
@@ -0,0 +1,85 @@
+import time
+import asyncio
+from enum import Enum
+from typing import Dict, Callable
+from dataclasses import dataclass
+import logging
+
+logger = logging.getLogger(__name__)
+
+class CircuitState(Enum):
+    CLOSED = "closed"      # Normal operation
+    OPEN = "open"          # Failing, reject requests
+    HALF_OPEN = "half_open"  # Testing recovery
+
+@dataclass
+class CircuitStats:
+    failures: int = 0
+    successes: int = 0
+    last_failure_time: float = 0
+    state: CircuitState = CircuitState.CLOSED
+
+class CircuitBreaker:
+    def __init__(
+        self,
+        failure_threshold: int = 5,
+        recovery_timeout: int = 30,
+        half_open_requests: int = 3
+    ):
+        self.failure_threshold = failure_threshold
+        self.recovery_timeout = recovery_timeout
+        self.half_open_requests = half_open_requests
+        self.circuits: Dict[str, CircuitStats] = {}
+
+    def get_circuit(self, service: str) -> CircuitStats:
+        if service not in self.circuits:
+            self.circuits[service] = CircuitStats()
+        return self.circuits[service]
+
+    def is_available(self, service: str) -> bool:
+        circuit = self.get_circuit(service)
+
+        if circuit.state == CircuitState.CLOSED:
+            return True
+
+        if circuit.state == CircuitState.OPEN:
+            if time.time() - circuit.last_failure_time > self.recovery_timeout:
+                circuit.state = CircuitState.HALF_OPEN
+                circuit.successes = 0
+                logger.info(f"Circuit {service} entering half-open state")
+                return True
+            return False
+
+        # HALF_OPEN: allow limited requests
+        return circuit.successes < self.half_open_requests
+
+    def record_success(self, service: str):
+        circuit = self.get_circuit(service)
+        circuit.successes += 1
+
+        if circuit.state == CircuitState.HALF_OPEN:
+            if circuit.successes >= self.half_open_requests:
+                circuit.state = CircuitState.CLOSED
+                circuit.failures = 0
+                logger.info(f"Circuit {service} closed (recovered)")
+
+    def record_failure(self, service: str):
+        circuit = self.get_circuit(service)
+        circuit.failures += 1
+        circuit.last_failure_time = time.time()
+
+        if circuit.state == CircuitState.HALF_OPEN:
+            circuit.state = CircuitState.OPEN
+            logger.warning(f"Circuit {service} reopened after failure")
+        elif circuit.failures >= self.failure_threshold:
+            circuit.state = CircuitState.OPEN
+            logger.warning(f"Circuit {service} opened after {circuit.failures} failures")
+
+    async def call(self, service: str, func: Callable, *args, **kwargs):
+        if not self.is_available(service):
+            raise Exception(f"Service {service} unavailable (circuit open)")
+
+        try:
+            result = await func(*args, **kwargs)
+            self.record_success(service)
+            return result
+        except Exception as e:
+            self.record_failure(service)
+            raise""",
            commands="""- cd gateway && pip install -r requirements.txt
- cd gateway && pytest tests/ -v
- docker-compose up redis
- cd gateway && uvicorn app.main:app --reload""",
            notes="""- Circuit breaker state is in-memory; use Redis for distributed
- Rate limit headers follow standard conventions
- Add service health checks for proactive circuit management
- Consider adding request retries with backoff"""
        )
    },

    # GraphQL with DataLoader
    {
        "category": "spec_to_implementation",
        "user": """Implement a GraphQL API with:
- User, Post, Comment types
- N+1 query prevention with DataLoader
- Subscription for new comments
- Field-level permissions""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Define GraphQL types with Strawberry
2) Implement DataLoaders for batch loading
3) Add subscription for real-time comments
4) Create permission classes for field access
5) Set up WebSocket for subscriptions""",
            files="""- backend/app/graphql/types.py
- backend/app/graphql/dataloaders.py
- backend/app/graphql/subscriptions.py
- backend/app/graphql/permissions.py
- backend/app/graphql/schema.py""",
            patch="""--- /dev/null
+++ b/backend/app/graphql/dataloaders.py
@@ -0,0 +1,55 @@
+from typing import List, Dict
+from collections import defaultdict
+from strawberry.dataloader import DataLoader
+from sqlalchemy.orm import Session
+from app.models import User, Post, Comment
+
+class Loaders:
+    def __init__(self, db: Session):
+        self.db = db
+        self._user_loader = None
+        self._posts_by_user_loader = None
+        self._comments_by_post_loader = None
+
+    @property
+    def user_loader(self) -> DataLoader:
+        if not self._user_loader:
+            async def load_users(ids: List[int]) -> List[User]:
+                users = self.db.query(User).filter(User.id.in_(ids)).all()
+                user_map = {u.id: u for u in users}
+                return [user_map.get(id) for id in ids]
+            self._user_loader = DataLoader(load_fn=load_users)
+        return self._user_loader
+
+    @property
+    def posts_by_user_loader(self) -> DataLoader:
+        if not self._posts_by_user_loader:
+            async def load_posts(user_ids: List[int]) -> List[List[Post]]:
+                posts = self.db.query(Post).filter(Post.author_id.in_(user_ids)).all()
+                posts_by_user: Dict[int, List[Post]] = defaultdict(list)
+                for post in posts:
+                    posts_by_user[post.author_id].append(post)
+                return [posts_by_user.get(uid, []) for uid in user_ids]
+            self._posts_by_user_loader = DataLoader(load_fn=load_posts)
+        return self._posts_by_user_loader
+
+    @property
+    def comments_by_post_loader(self) -> DataLoader:
+        if not self._comments_by_post_loader:
+            async def load_comments(post_ids: List[int]) -> List[List[Comment]]:
+                comments = self.db.query(Comment).filter(
+                    Comment.post_id.in_(post_ids)
+                ).order_by(Comment.created_at.desc()).all()
+                comments_by_post: Dict[int, List[Comment]] = defaultdict(list)
+                for comment in comments:
+                    comments_by_post[comment.post_id].append(comment)
+                return [comments_by_post.get(pid, []) for pid in post_ids]
+            self._comments_by_post_loader = DataLoader(load_fn=load_comments)
+        return self._comments_by_post_loader

--- /dev/null
+++ b/backend/app/graphql/permissions.py
@@ -0,0 +1,40 @@
+from strawberry.permission import BasePermission
+from strawberry.types import Info
+from typing import Any
+
+class IsAuthenticated(BasePermission):
+    message = "User is not authenticated"
+
+    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
+        return info.context.get("user") is not None
+
+class IsOwner(BasePermission):
+    message = "You don't have permission to access this resource"
+
+    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
+        user = info.context.get("user")
+        if not user:
+            return False
+        # Check if user owns the resource
+        if hasattr(source, "author_id"):
+            return source.author_id == user.id
+        if hasattr(source, "user_id"):
+            return source.user_id == user.id
+        return False
+
+class IsAdmin(BasePermission):
+    message = "Admin access required"
+
+    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
+        user = info.context.get("user")
+        return user and user.is_admin
+
+class FieldPermission(BasePermission):
+    def __init__(self, roles: list):
+        self.roles = roles
+
+    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
+        user = info.context.get("user")
+        if not user:
+            return False
+        return any(role in user.roles for role in self.roles)

--- /dev/null
+++ b/backend/app/graphql/subscriptions.py
@@ -0,0 +1,35 @@
+import strawberry
+from typing import AsyncGenerator
+import asyncio
+from collections import defaultdict
+
+# In-memory pubsub (use Redis for production)
+subscribers = defaultdict(list)
+
+async def publish(channel: str, message: any):
+    for queue in subscribers[channel]:
+        await queue.put(message)
+
+@strawberry.type
+class Subscription:
+    @strawberry.subscription
+    async def comment_added(self, post_id: int) -> AsyncGenerator["CommentType", None]:
+        queue = asyncio.Queue()
+        channel = f"post:{post_id}:comments"
+        subscribers[channel].append(queue)
+
+        try:
+            while True:
+                comment = await queue.get()
+                yield comment
+        finally:
+            subscribers[channel].remove(queue)
+
+    @strawberry.subscription
+    async def post_updated(self, info) -> AsyncGenerator["PostType", None]:
+        user = info.context.get("user")
+        if not user:
+            raise Exception("Authentication required")
+
+        queue = asyncio.Queue()
+        subscribers[f"user:{user.id}:posts"].append(queue)
+
+        try:
+            while True:
+                post = await queue.get()
+                yield post
+        finally:
+            subscribers[f"user:{user.id}:posts"].remove(queue)""",
            commands="""- cd backend && pip install strawberry-graphql[fastapi]
- cd backend && pytest tests/test_graphql.py -v
- cd backend && uvicorn app.main:app --reload""",
            notes="""- DataLoaders prevent N+1 queries by batching
- Use Redis PubSub for distributed subscriptions
- Field permissions checked at resolver level
- Consider adding query complexity limits"""
        )
    },
]

# ============================================================================
# 2. BUG -> FIX WITH ERROR LOGS
# ============================================================================

BUG_TO_FIX = [
    {
        "category": "bug_fix",
        "user": """Fix this production error:

```
ERROR 2024-01-15 14:23:45 - Connection pool exhausted
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached,
connection timed out, timeout 30.00
```

Code:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def get_user(user_id):
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    return user

@app.get("/api/users/{user_id}")
async def get_user_endpoint(user_id: int):
    return get_user(user_id)
```""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Add context manager to ensure session cleanup
2) Configure connection pool with proper limits
3) Add pool health checks
4) Create FastAPI dependency for session management
5) Add monitoring for connection usage""",
            files="""- backend/app/db/session.py
- backend/app/api/users.py
- backend/app/core/config.py""",
            patch="""--- a/backend/app/db/session.py
+++ b/backend/app/db/session.py
@@ -1,8 +1,35 @@
 from sqlalchemy import create_engine
-from sqlalchemy.orm import sessionmaker
+from sqlalchemy.orm import sessionmaker, Session
+from sqlalchemy.pool import QueuePool
+from contextlib import contextmanager
+from typing import Generator
+import logging
+
+logger = logging.getLogger(__name__)

-engine = create_engine(DATABASE_URL)
+engine = create_engine(
+    DATABASE_URL,
+    poolclass=QueuePool,
+    pool_size=20,           # Base connections
+    max_overflow=30,        # Extra connections under load
+    pool_timeout=30,        # Wait time for connection
+    pool_recycle=1800,      # Recycle connections after 30 min
+    pool_pre_ping=True,     # Check connection health
+    echo_pool=True          # Log pool events
+)
 Session = sessionmaker(bind=engine)

-def get_user(user_id):
-    session = Session()
-    user = session.query(User).filter(User.id == user_id).first()
-    return user
+@contextmanager
+def get_session() -> Generator[Session, None, None]:
+    session = Session()
+    try:
+        yield session
+        session.commit()
+    except Exception:
+        session.rollback()
+        raise
+    finally:
+        session.close()
+
+# FastAPI dependency
+def get_db() -> Generator[Session, None, None]:
+    session = Session()
+    try:
+        yield session
+    finally:
+        session.close()

--- a/backend/app/api/users.py
+++ b/backend/app/api/users.py
@@ -1,6 +1,12 @@
+from fastapi import Depends, HTTPException
+from sqlalchemy.orm import Session
+from app.db.session import get_db
+
 @app.get("/api/users/{user_id}")
-async def get_user_endpoint(user_id: int):
-    return get_user(user_id)
+async def get_user_endpoint(
+    user_id: int,
+    db: Session = Depends(get_db)
+):
+    user = db.query(User).filter(User.id == user_id).first()
+    if not user:
+        raise HTTPException(status_code=404, detail="User not found")
+    return user""",
            commands="""- cd backend && pytest tests/test_db.py -v
- cd backend && python -c "from app.db.session import engine; print(engine.pool.status())"
- ab -n 1000 -c 50 http://localhost:8000/api/users/1""",
            notes="""- Root cause: Sessions never closed, exhausting pool
- pool_pre_ping prevents stale connection errors
- Monitor pool status with engine.pool.status()
- Consider adding connection pool metrics to monitoring"""
        )
    },

    {
        "category": "bug_fix",
        "user": """Fix this race condition bug:

Users report their account balance going negative after concurrent purchases.

```
Error: Negative balance detected for user 12345
Current balance: -50.00
Last transaction: Purchase $150.00
Previous balance before transaction: $100.00
```

Code:
```python
@app.post("/api/purchase")
async def purchase(product_id: int, user = Depends(get_current_user), db = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if user.balance >= product.price:
        user.balance -= product.price
        db.add(Order(user_id=user.id, product_id=product_id, amount=product.price))
        db.commit()
        return {"success": True}

    return {"error": "Insufficient balance"}
```""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Add database-level row locking with FOR UPDATE
2) Implement optimistic locking with version column
3) Use atomic UPDATE with balance check
4) Add idempotency key to prevent duplicate orders
5) Add retry logic for lock contention""",
            files="""- backend/app/api/purchase.py
- backend/app/models/user.py
- backend/app/services/purchase.py""",
            patch="""--- a/backend/app/models/user.py
+++ b/backend/app/models/user.py
@@ -5,6 +5,7 @@ class User(Base):
     id = Column(Integer, primary_key=True)
     email = Column(String, unique=True)
     balance = Column(Numeric(10, 2), default=0)
+    balance_version = Column(Integer, default=0)  # Optimistic locking

--- /dev/null
+++ b/backend/app/services/purchase.py
@@ -0,0 +1,65 @@
+from sqlalchemy import text
+from sqlalchemy.orm import Session
+from decimal import Decimal
+from typing import Optional
+import logging
+
+logger = logging.getLogger(__name__)
+
+class PurchaseService:
+    def __init__(self, db: Session):
+        self.db = db
+
+    def purchase_with_lock(
+        self,
+        user_id: int,
+        product_id: int,
+        idempotency_key: str
+    ) -> dict:
+        # Check for duplicate order
+        existing = self.db.execute(
+            text("SELECT id FROM orders WHERE idempotency_key = :key"),
+            {"key": idempotency_key}
+        ).first()
+
+        if existing:
+            return {"success": True, "order_id": existing.id, "duplicate": True}
+
+        # Lock user row for update
+        result = self.db.execute(
+            text('''
+                SELECT id, balance, balance_version
+                FROM users
+                WHERE id = :user_id
+                FOR UPDATE NOWAIT
+            '''),
+            {"user_id": user_id}
+        ).first()
+
+        if not result:
+            return {"error": "User not found"}
+
+        user_balance = Decimal(str(result.balance))
+        version = result.balance_version
+
+        # Get product price
+        product = self.db.execute(
+            text("SELECT price FROM products WHERE id = :id"),
+            {"id": product_id}
+        ).first()
+
+        if not product:
+            return {"error": "Product not found"}
+
+        price = Decimal(str(product.price))
+
+        if user_balance < price:
+            return {"error": "Insufficient balance"}
+
+        # Atomic update with version check (optimistic lock)
+        updated = self.db.execute(
+            text('''
+                UPDATE users
+                SET balance = balance - :price,
+                    balance_version = balance_version + 1
+                WHERE id = :user_id
+                AND balance_version = :version
+                AND balance >= :price
+                RETURNING id
+            '''),
+            {"user_id": user_id, "price": price, "version": version}
+        ).first()
+
+        if not updated:
+            self.db.rollback()
+            return {"error": "Concurrent modification, please retry"}
+
+        # Create order
+        order_result = self.db.execute(
+            text('''
+                INSERT INTO orders (user_id, product_id, amount, idempotency_key)
+                VALUES (:user_id, :product_id, :amount, :key)
+                RETURNING id
+            '''),
+            {
+                "user_id": user_id,
+                "product_id": product_id,
+                "amount": price,
+                "key": idempotency_key
+            }
+        ).first()
+
+        self.db.commit()
+        return {"success": True, "order_id": order_result.id}

--- a/backend/app/api/purchase.py
+++ b/backend/app/api/purchase.py
@@ -1,13 +1,35 @@
+from fastapi import APIRouter, Depends, HTTPException, Header
+from sqlalchemy.orm import Session
+from sqlalchemy.exc import OperationalError
+from app.db.session import get_db
+from app.services.purchase import PurchaseService
+import time
+
+router = APIRouter()
+
 @app.post("/api/purchase")
 async def purchase(
     product_id: int,
+    idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
     user = Depends(get_current_user),
     db = Depends(get_db)
 ):
-    product = db.query(Product).filter(Product.id == product_id).first()
+    service = PurchaseService(db)
+    max_retries = 3

-    if user.balance >= product.price:
-        user.balance -= product.price
-        db.add(Order(user_id=user.id, product_id=product_id, amount=product.price))
-        db.commit()
-        return {"success": True}
+    for attempt in range(max_retries):
+        try:
+            result = service.purchase_with_lock(
+                user_id=user.id,
+                product_id=product_id,
+                idempotency_key=idempotency_key
+            )
+
+            if "error" in result:
+                if "retry" in result["error"].lower():
+                    time.sleep(0.1 * (attempt + 1))
+                    continue
+                raise HTTPException(status_code=400, detail=result["error"])
+
+            return result
+
+        except OperationalError:
+            db.rollback()
+            time.sleep(0.1 * (attempt + 1))

-    return {"error": "Insufficient balance"}
+    raise HTTPException(status_code=409, detail="Transaction failed after retries")""",
            commands="""- cd backend && alembic revision --autogenerate -m "add balance version"
- cd backend && alembic upgrade head
- cd backend && pytest tests/test_purchase.py -v
- cd backend && pytest tests/test_purchase_concurrent.py -v""",
            notes="""- Uses both pessimistic (FOR UPDATE) and optimistic (version) locking
- Idempotency key prevents duplicate orders from retries
- NOWAIT throws error immediately if locked (can use SKIP LOCKED for queue)
- Retry with exponential backoff for transient failures"""
        )
    },

    {
        "category": "bug_fix",
        "user": """Memory leak causing container OOM kills:

```
2024-01-15 10:00:00 - Container memory: 512MB
2024-01-15 11:00:00 - Container memory: 1.2GB
2024-01-15 12:00:00 - Container memory: 2.1GB
2024-01-15 12:15:00 - OOMKilled
```

Code handling file uploads:
```python
uploaded_files = []

@app.post("/api/upload")
async def upload_file(file: UploadFile):
    content = await file.read()
    uploaded_files.append({
        "name": file.filename,
        "content": content,
        "size": len(content)
    })
    # Process file...
    return {"filename": file.filename}
```""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Remove global file storage accumulating in memory
2) Stream file to disk/S3 instead of loading in memory
3) Add file size limits
4) Use background tasks for processing
5) Add memory monitoring""",
            files="""- backend/app/api/upload.py
- backend/app/services/storage.py
- backend/app/core/config.py""",
            patch="""--- a/backend/app/api/upload.py
+++ b/backend/app/api/upload.py
@@ -1,13 +1,65 @@
-uploaded_files = []
+from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks, Depends
+from app.services.storage import StorageService
+from app.core.config import settings
+import logging

-@app.post("/api/upload")
-async def upload_file(file: UploadFile):
-    content = await file.read()
-    uploaded_files.append({
-        "name": file.filename,
-        "content": content,
-        "size": len(content)
-    })
-    # Process file...
-    return {"filename": file.filename}
+logger = logging.getLogger(__name__)
+router = APIRouter()
+
+MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
+
+@router.post("/api/upload")
+async def upload_file(
+    file: UploadFile,
+    background_tasks: BackgroundTasks,
+    storage: StorageService = Depends()
+):
+    # Validate content type
+    allowed_types = {"image/jpeg", "image/png", "application/pdf"}
+    if file.content_type not in allowed_types:
+        raise HTTPException(400, f"File type {file.content_type} not allowed")
+
+    # Check file size without loading entire file
+    file.file.seek(0, 2)  # Seek to end
+    size = file.file.tell()
+    file.file.seek(0)     # Reset to start
+
+    if size > MAX_FILE_SIZE:
+        raise HTTPException(400, f"File too large. Max: {MAX_FILE_SIZE // 1024 // 1024}MB")
+
+    # Stream to storage (S3/disk) instead of memory
+    try:
+        file_key = await storage.upload_stream(
+            file.file,
+            filename=file.filename,
+            content_type=file.content_type
+        )
+    except Exception as e:
+        logger.error(f"Upload failed: {e}")
+        raise HTTPException(500, "Upload failed")
+
+    # Process in background
+    background_tasks.add_task(process_uploaded_file, file_key)
+
+    return {"file_key": file_key, "size": size}
+
+async def process_uploaded_file(file_key: str):
+    """Process file in background to avoid blocking."""
+    logger.info(f"Processing file: {file_key}")
+    # Process without loading entire file in memory
+    # Use streaming/chunked processing

--- /dev/null
+++ b/backend/app/services/storage.py
@@ -0,0 +1,50 @@
+import boto3
+from botocore.config import Config
+from typing import BinaryIO
+import hashlib
+import uuid
+from app.core.config import settings
+
+class StorageService:
+    def __init__(self):
+        self.s3 = boto3.client(
+            's3',
+            config=Config(
+                max_pool_connections=50,
+                retries={'max_attempts': 3}
+            )
+        )
+        self.bucket = settings.S3_BUCKET
+
+    async def upload_stream(
+        self,
+        file_obj: BinaryIO,
+        filename: str,
+        content_type: str,
+        chunk_size: int = 8 * 1024 * 1024  # 8MB chunks
+    ) -> str:
+        file_key = f"uploads/{uuid.uuid4().hex}/{filename}"
+
+        # Use multipart upload for large files
+        mpu = self.s3.create_multipart_upload(
+            Bucket=self.bucket,
+            Key=file_key,
+            ContentType=content_type
+        )
+
+        parts = []
+        part_number = 1
+
+        while True:
+            chunk = file_obj.read(chunk_size)
+            if not chunk:
+                break
+
+            part = self.s3.upload_part(
+                Bucket=self.bucket,
+                Key=file_key,
+                UploadId=mpu['UploadId'],
+                PartNumber=part_number,
+                Body=chunk
+            )
+            parts.append({'PartNumber': part_number, 'ETag': part['ETag']})
+            part_number += 1
+
+        self.s3.complete_multipart_upload(
+            Bucket=self.bucket,
+            Key=file_key,
+            UploadId=mpu['UploadId'],
+            MultipartUpload={'Parts': parts}
+        )
+
+        return file_key""",
            commands="""- cd backend && pytest tests/test_upload.py -v
- cd backend && python -c "import tracemalloc; tracemalloc.start(); # test memory"
- docker stats backend --no-stream""",
            notes="""- Root cause: Global list accumulating file contents
- Streaming upload prevents loading entire file in memory
- Multipart upload for files > 5MB (S3 requirement)
- Background processing prevents request timeout
- Add memory profiling to catch leaks early"""
        )
    },
]

# ============================================================================
# 3. ADD TESTS + MAKE TESTS PASS
# ============================================================================

ADD_TESTS = [
    {
        "category": "add_tests",
        "user": """Add comprehensive tests for this payment service:

```python
class PaymentService:
    def __init__(self, stripe_client, db):
        self.stripe = stripe_client
        self.db = db

    def process_payment(self, user_id: int, amount: Decimal, currency: str = "usd"):
        user = self.db.query(User).get(user_id)
        if not user:
            raise ValueError("User not found")

        intent = self.stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=currency,
            customer=user.stripe_customer_id
        )

        payment = Payment(
            user_id=user_id,
            amount=amount,
            stripe_intent_id=intent.id,
            status="pending"
        )
        self.db.add(payment)
        self.db.commit()

        return payment
```""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Create pytest fixtures for mocking
2) Add unit tests for success cases
3) Add tests for error handling
4) Add integration tests with test database
5) Add tests for edge cases (negative amounts, invalid currency)""",
            files="""- backend/tests/test_payment_service.py
- backend/tests/conftest.py
- backend/tests/fixtures/stripe_mock.py""",
            patch="""--- /dev/null
+++ b/backend/tests/conftest.py
@@ -0,0 +1,45 @@
+import pytest
+from sqlalchemy import create_engine
+from sqlalchemy.orm import sessionmaker
+from unittest.mock import MagicMock
+from app.db.base import Base
+from app.models import User, Payment
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
+    stripe.PaymentIntent.create.return_value = MagicMock(
+        id="pi_test_123",
+        client_secret="secret_123",
+        status="requires_payment_method"
+    )
+    return stripe
+
+@pytest.fixture
+def test_user(db_session):
+    user = User(
+        id=1,
+        email="test@example.com",
+        stripe_customer_id="cus_test_123"
+    )
+    db_session.add(user)
+    db_session.commit()
+    return user
+
+@pytest.fixture
+def payment_service(mock_stripe, db_session):
+    from app.services.payment import PaymentService
+    return PaymentService(mock_stripe, db_session)

--- /dev/null
+++ b/backend/tests/test_payment_service.py
@@ -0,0 +1,120 @@
+import pytest
+from decimal import Decimal
+from unittest.mock import MagicMock, patch
+from app.services.payment import PaymentService
+from app.models import Payment
+import stripe
+
+class TestPaymentService:
+    """Unit tests for PaymentService."""
+
+    def test_process_payment_success(self, payment_service, test_user, mock_stripe):
+        """Test successful payment processing."""
+        result = payment_service.process_payment(
+            user_id=test_user.id,
+            amount=Decimal("99.99"),
+            currency="usd"
+        )
+
+        assert result.user_id == test_user.id
+        assert result.amount == Decimal("99.99")
+        assert result.stripe_intent_id == "pi_test_123"
+        assert result.status == "pending"
+
+        mock_stripe.PaymentIntent.create.assert_called_once_with(
+            amount=9999,  # cents
+            currency="usd",
+            customer="cus_test_123"
+        )
+
+    def test_process_payment_user_not_found(self, payment_service):
+        """Test payment fails for non-existent user."""
+        with pytest.raises(ValueError, match="User not found"):
+            payment_service.process_payment(
+                user_id=999,
+                amount=Decimal("50.00")
+            )
+
+    def test_process_payment_negative_amount(self, payment_service, test_user):
+        """Test payment rejects negative amounts."""
+        with pytest.raises(ValueError, match="Amount must be positive"):
+            payment_service.process_payment(
+                user_id=test_user.id,
+                amount=Decimal("-10.00")
+            )
+
+    def test_process_payment_zero_amount(self, payment_service, test_user):
+        """Test payment rejects zero amount."""
+        with pytest.raises(ValueError, match="Amount must be positive"):
+            payment_service.process_payment(
+                user_id=test_user.id,
+                amount=Decimal("0.00")
+            )
+
+    def test_process_payment_invalid_currency(self, payment_service, test_user):
+        """Test payment rejects invalid currency."""
+        with pytest.raises(ValueError, match="Invalid currency"):
+            payment_service.process_payment(
+                user_id=test_user.id,
+                amount=Decimal("50.00"),
+                currency="invalid"
+            )
+
+    def test_process_payment_stripe_error(self, payment_service, test_user, mock_stripe):
+        """Test handling of Stripe API errors."""
+        mock_stripe.PaymentIntent.create.side_effect = stripe.error.CardError(
+            "Card declined", "card_declined", "card_error"
+        )
+
+        with pytest.raises(stripe.error.CardError):
+            payment_service.process_payment(
+                user_id=test_user.id,
+                amount=Decimal("50.00")
+            )
+
+    def test_process_payment_db_rollback_on_stripe_error(
+        self, payment_service, test_user, mock_stripe, db_session
+    ):
+        """Test database rollback when Stripe fails."""
+        mock_stripe.PaymentIntent.create.side_effect = Exception("Stripe error")
+
+        with pytest.raises(Exception):
+            payment_service.process_payment(
+                user_id=test_user.id,
+                amount=Decimal("50.00")
+            )
+
+        # Verify no payment was created
+        payments = db_session.query(Payment).filter(
+            Payment.user_id == test_user.id
+        ).all()
+        assert len(payments) == 0
+
+    @pytest.mark.parametrize("amount,expected_cents", [
+        (Decimal("1.00"), 100),
+        (Decimal("99.99"), 9999),
+        (Decimal("1000.00"), 100000),
+        (Decimal("0.50"), 50),
+    ])
+    def test_amount_conversion_to_cents(
+        self, payment_service, test_user, mock_stripe, amount, expected_cents
+    ):
+        """Test correct conversion of decimal amounts to cents."""
+        payment_service.process_payment(
+            user_id=test_user.id,
+            amount=amount
+        )
+
+        call_args = mock_stripe.PaymentIntent.create.call_args
+        assert call_args.kwargs["amount"] == expected_cents
+
+
+class TestPaymentServiceIntegration:
+    """Integration tests with real database."""
+
+    @pytest.mark.integration
+    def test_payment_persisted_to_database(self, payment_service, test_user, db_session):
+        """Test payment record is persisted."""
+        result = payment_service.process_payment(
+            user_id=test_user.id,
+            amount=Decimal("50.00")
+        )
+
+        db_payment = db_session.query(Payment).get(result.id)
+        assert db_payment is not None
+        assert db_payment.amount == Decimal("50.00")
+        assert db_payment.status == "pending\"""",
            commands="""- cd backend && pytest tests/test_payment_service.py -v
- cd backend && pytest tests/test_payment_service.py -v --cov=app/services/payment
- cd backend && pytest tests/test_payment_service.py -v -m integration""",
            notes="""- Unit tests use mocked Stripe client
- Integration tests use SQLite in-memory database
- Parameterized tests cover edge cases efficiently
- Add fixtures for common test data
- Consider property-based testing with Hypothesis"""
        )
    },
]

# ============================================================================
# 4. REFACTOR TO BEST PRACTICES
# ============================================================================

REFACTOR_EXAMPLES = [
    {
        "category": "refactor",
        "user": """Refactor this god class into clean architecture:

```python
class UserManager:
    def __init__(self, db, email_service, payment_service, analytics):
        self.db = db
        self.email = email_service
        self.payment = payment_service
        self.analytics = analytics

    def register_user(self, email, password, plan):
        # Validate
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email")
        if len(password) < 8:
            raise ValueError("Password too short")

        # Create user
        user = User(email=email)
        user.password = hashlib.md5(password.encode()).hexdigest()
        self.db.add(user)
        self.db.commit()

        # Create subscription
        if plan == "premium":
            customer = self.payment.create_customer(email)
            subscription = self.payment.create_subscription(customer.id, "premium")
            user.stripe_customer_id = customer.id
            user.subscription_id = subscription.id
            self.db.commit()

        # Send welcome email
        self.email.send(email, "Welcome!", f"Hello {email}!")

        # Track analytics
        self.analytics.track("user_registered", {"email": email, "plan": plan})

        return user
```""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Extract validation to separate validator class
2) Create UserRepository for data access
3) Create UserService for business logic
4) Use events for side effects (email, analytics)
5) Add proper password hashing with bcrypt""",
            files="""- backend/app/services/user_service.py
- backend/app/repositories/user_repository.py
- backend/app/validators/user_validator.py
- backend/app/events/user_events.py
- backend/app/domain/user.py""",
            patch="""--- /dev/null
+++ b/backend/app/validators/user_validator.py
@@ -0,0 +1,35 @@
+import re
+from dataclasses import dataclass
+from typing import List, Optional
+
+@dataclass
+class ValidationResult:
+    is_valid: bool
+    errors: List[str]
+
+class UserValidator:
+    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
+    MIN_PASSWORD_LENGTH = 8
+
+    def validate_registration(
+        self,
+        email: str,
+        password: str
+    ) -> ValidationResult:
+        errors = []
+
+        if not email or not self.EMAIL_REGEX.match(email):
+            errors.append("Invalid email format")
+
+        if not password or len(password) < self.MIN_PASSWORD_LENGTH:
+            errors.append(f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters")
+
+        if password and not re.search(r"[A-Z]", password):
+            errors.append("Password must contain uppercase letter")
+
+        if password and not re.search(r"[0-9]", password):
+            errors.append("Password must contain a digit")
+
+        return ValidationResult(
+            is_valid=len(errors) == 0,
+            errors=errors
+        )

--- /dev/null
+++ b/backend/app/repositories/user_repository.py
@@ -0,0 +1,40 @@
+from typing import Optional
+from sqlalchemy.orm import Session
+from app.models import User
+
+class UserRepository:
+    def __init__(self, db: Session):
+        self.db = db
+
+    def find_by_email(self, email: str) -> Optional[User]:
+        return self.db.query(User).filter(User.email == email).first()
+
+    def find_by_id(self, user_id: int) -> Optional[User]:
+        return self.db.query(User).filter(User.id == user_id).first()
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
+    def save(self) -> None:
+        self.db.commit()
+
+    def rollback(self) -> None:
+        self.db.rollback()

--- /dev/null
+++ b/backend/app/events/user_events.py
@@ -0,0 +1,45 @@
+from dataclasses import dataclass
+from typing import List, Callable
+from abc import ABC, abstractmethod
+
+@dataclass
+class UserRegisteredEvent:
+    user_id: int
+    email: str
+    plan: str
+
+class EventHandler(ABC):
+    @abstractmethod
+    async def handle(self, event) -> None:
+        pass
+
+class SendWelcomeEmailHandler(EventHandler):
+    def __init__(self, email_service):
+        self.email_service = email_service
+
+    async def handle(self, event: UserRegisteredEvent) -> None:
+        await self.email_service.send(
+            to=event.email,
+            subject="Welcome!",
+            template="welcome",
+            context={"email": event.email}
+        )
+
+class TrackRegistrationHandler(EventHandler):
+    def __init__(self, analytics):
+        self.analytics = analytics
+
+    async def handle(self, event: UserRegisteredEvent) -> None:
+        self.analytics.track("user_registered", {
+            "user_id": event.user_id,
+            "email": event.email,
+            "plan": event.plan
+        })
+
+class EventBus:
+    def __init__(self):
+        self.handlers: List[EventHandler] = []
+
+    def subscribe(self, handler: EventHandler):
+        self.handlers.append(handler)
+
+    async def publish(self, event) -> None:
+        for handler in self.handlers:
+            await handler.handle(event)

--- /dev/null
+++ b/backend/app/services/user_service.py
@@ -0,0 +1,70 @@
+from dataclasses import dataclass
+from typing import Optional
+from passlib.context import CryptContext
+
+from app.repositories.user_repository import UserRepository
+from app.validators.user_validator import UserValidator
+from app.events.user_events import EventBus, UserRegisteredEvent
+from app.models import User
+
+pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
+
+@dataclass
+class RegistrationResult:
+    success: bool
+    user: Optional[User] = None
+    errors: list = None
+
+class UserService:
+    def __init__(
+        self,
+        repository: UserRepository,
+        validator: UserValidator,
+        payment_service,
+        event_bus: EventBus
+    ):
+        self.repository = repository
+        self.validator = validator
+        self.payment = payment_service
+        self.events = event_bus
+
+    async def register_user(
+        self,
+        email: str,
+        password: str,
+        plan: str = "free"
+    ) -> RegistrationResult:
+        # Validate input
+        validation = self.validator.validate_registration(email, password)
+        if not validation.is_valid:
+            return RegistrationResult(success=False, errors=validation.errors)
+
+        # Check for existing user
+        if self.repository.find_by_email(email):
+            return RegistrationResult(
+                success=False,
+                errors=["Email already registered"]
+            )
+
+        try:
+            # Create user with proper password hashing
+            user = User(email=email)
+            user.password_hash = pwd_context.hash(password)
+            self.repository.create(user)
+
+            # Handle subscription if premium
+            if plan == "premium":
+                await self._setup_premium_subscription(user)
+
+            self.repository.save()
+
+            # Publish event for side effects
+            await self.events.publish(UserRegisteredEvent(
+                user_id=user.id,
+                email=email,
+                plan=plan
+            ))
+
+            return RegistrationResult(success=True, user=user)
+
+        except Exception as e:
+            self.repository.rollback()
+            return RegistrationResult(success=False, errors=[str(e)])
+
+    async def _setup_premium_subscription(self, user: User):
+        customer = await self.payment.create_customer(user.email)
+        subscription = await self.payment.create_subscription(customer.id, "premium")
+        user.stripe_customer_id = customer.id
+        user.subscription_id = subscription.id""",
            commands="""- cd backend && pytest tests/test_user_service.py -v
- cd backend && pytest tests/test_user_validator.py -v
- cd backend && python -m mypy app/services/user_service.py""",
            notes="""- Single Responsibility: Each class has one job
- Dependency Injection: Services receive dependencies
- Event-driven: Side effects decoupled from core logic
- MD5 replaced with bcrypt for security
- Repository pattern for data access
- Validation separated from business logic"""
        )
    },
]

# ============================================================================
# 5. SECURITY PATTERNS
# ============================================================================

SECURITY_PATTERNS = [
    {
        "category": "security",
        "user": """Implement RBAC (Role-Based Access Control) with:
- Multiple roles (admin, manager, user)
- Resource-level permissions
- API endpoint protection""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Create Role and Permission models
2) Implement permission checker
3) Create FastAPI dependencies for auth
4) Add role decorators for endpoints
5) Set up permission caching""",
            files="""- backend/app/models/rbac.py
- backend/app/core/permissions.py
- backend/app/api/deps.py""",
            patch="""--- /dev/null
+++ b/backend/app/models/rbac.py
@@ -0,0 +1,50 @@
+from sqlalchemy import Column, Integer, String, ForeignKey, Table
+from sqlalchemy.orm import relationship
+from app.db.base import Base
+
+# Association tables
+user_roles = Table(
+    "user_roles",
+    Base.metadata,
+    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
+    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
+)
+
+role_permissions = Table(
+    "role_permissions",
+    Base.metadata,
+    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
+    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
+)
+
+class Role(Base):
+    __tablename__ = "roles"
+
+    id = Column(Integer, primary_key=True)
+    name = Column(String, unique=True, nullable=False)
+    description = Column(String)
+
+    permissions = relationship("Permission", secondary=role_permissions)
+
+class Permission(Base):
+    __tablename__ = "permissions"
+
+    id = Column(Integer, primary_key=True)
+    resource = Column(String, nullable=False)  # e.g., "users", "orders"
+    action = Column(String, nullable=False)    # e.g., "read", "write", "delete"
+
+    class Config:
+        unique_together = [["resource", "action"]]

--- /dev/null
+++ b/backend/app/core/permissions.py
@@ -0,0 +1,85 @@
+from functools import wraps
+from typing import List, Optional, Set
+from fastapi import HTTPException, Depends
+from sqlalchemy.orm import Session
+import redis
+import json
+
+from app.db.session import get_db
+from app.core.security import get_current_user
+from app.models import User
+from app.models.rbac import Permission
+
+redis_client = redis.Redis(host="localhost", port=6379, db=1)
+CACHE_TTL = 300  # 5 minutes
+
+class PermissionChecker:
+    def __init__(self, db: Session):
+        self.db = db
+
+    def get_user_permissions(self, user_id: int) -> Set[str]:
+        # Check cache first
+        cache_key = f"permissions:{user_id}"
+        cached = redis_client.get(cache_key)
+        if cached:
+            return set(json.loads(cached))
+
+        # Query database
+        user = self.db.query(User).get(user_id)
+        if not user:
+            return set()
+
+        permissions = set()
+        for role in user.roles:
+            for perm in role.permissions:
+                permissions.add(f"{perm.resource}:{perm.action}")
+
+        # Cache permissions
+        redis_client.setex(cache_key, CACHE_TTL, json.dumps(list(permissions)))
+        return permissions
+
+    def has_permission(self, user_id: int, resource: str, action: str) -> bool:
+        permissions = self.get_user_permissions(user_id)
+
+        # Check specific permission
+        if f"{resource}:{action}" in permissions:
+            return True
+
+        # Check wildcard permissions
+        if f"{resource}:*" in permissions:
+            return True
+        if f"*:{action}" in permissions:
+            return True
+        if "*:*" in permissions:
+            return True
+
+        return False
+
+    @staticmethod
+    def invalidate_cache(user_id: int):
+        redis_client.delete(f"permissions:{user_id}")
+
+def require_permission(resource: str, action: str):
+    """Decorator for permission-protected endpoints."""
+    def decorator(func):
+        @wraps(func)
+        async def wrapper(
+            *args,
+            current_user: User = Depends(get_current_user),
+            db: Session = Depends(get_db),
+            **kwargs
+        ):
+            checker = PermissionChecker(db)
+
+            if not checker.has_permission(current_user.id, resource, action):
+                raise HTTPException(
+                    status_code=403,
+                    detail=f"Permission denied: {resource}:{action}"
+                )
+
+            return await func(*args, current_user=current_user, db=db, **kwargs)
+        return wrapper
+    return decorator
+
+# Convenience decorators
+def admin_only(func):
+    return require_permission("admin", "*")(func)
+
+def manager_or_admin(func):
+    return require_permission("management", "access")(func)

--- /dev/null
+++ b/backend/app/api/deps.py
@@ -0,0 +1,40 @@
+from fastapi import Depends, HTTPException
+from sqlalchemy.orm import Session
+from typing import List
+
+from app.db.session import get_db
+from app.core.security import get_current_user
+from app.core.permissions import PermissionChecker
+from app.models import User
+
+class PermissionDep:
+    def __init__(self, resource: str, action: str):
+        self.resource = resource
+        self.action = action
+
+    async def __call__(
+        self,
+        current_user: User = Depends(get_current_user),
+        db: Session = Depends(get_db)
+    ) -> User:
+        checker = PermissionChecker(db)
+
+        if not checker.has_permission(current_user.id, self.resource, self.action):
+            raise HTTPException(403, "Permission denied")
+
+        return current_user
+
+# Usage in routes:
+# @router.get("/users")
+# async def list_users(user: User = Depends(PermissionDep("users", "read"))):
+#     ...
+
+# @router.delete("/users/{id}")
+# async def delete_user(
+#     id: int,
+#     user: User = Depends(PermissionDep("users", "delete"))
+# ):
+#     ...
+
+# @router.post("/admin/settings")
+# async def admin_settings(user: User = Depends(PermissionDep("admin", "*"))):
+#     ...""",
            commands="""- cd backend && alembic revision --autogenerate -m "add rbac tables"
- cd backend && alembic upgrade head
- cd backend && python scripts/seed_permissions.py
- cd backend && pytest tests/test_permissions.py -v""",
            notes="""- Wildcard permissions (*) for admin access
- Redis caching for performance
- Invalidate cache on role changes
- Consider attribute-based access control (ABAC) for complex rules
- Log permission denials for security monitoring"""
        )
    },

    {
        "category": "security",
        "user": """Add input validation and sanitization for a comment system to prevent XSS and injection attacks.""",
        "assistant": OUTPUT_TEMPLATE.format(
            plan="""1) Add Pydantic validators for input
2) Implement HTML sanitization with bleach
3) Add rate limiting for comment creation
4) Implement content security headers
5) Add audit logging""",
            files="""- backend/app/schemas/comment.py
- backend/app/services/sanitizer.py
- backend/app/api/comments.py
- backend/app/middleware/security.py""",
            patch="""--- /dev/null
+++ b/backend/app/schemas/comment.py
@@ -0,0 +1,45 @@
+from pydantic import BaseModel, validator, Field
+from typing import Optional
+import re
+
+class CommentCreate(BaseModel):
+    content: str = Field(..., min_length=1, max_length=10000)
+    parent_id: Optional[int] = None
+
+    @validator("content")
+    def validate_content(cls, v):
+        # Remove null bytes
+        v = v.replace("\\x00", "")
+
+        # Check for empty content after stripping
+        if not v.strip():
+            raise ValueError("Content cannot be empty")
+
+        # Check for excessive whitespace (spam indicator)
+        if len(v) - len(v.replace(" ", "")) > len(v) * 0.5:
+            raise ValueError("Content contains too much whitespace")
+
+        # Check for repeated characters (spam indicator)
+        if re.search(r"(.)\1{10,}", v):
+            raise ValueError("Content contains excessive repeated characters")
+
+        return v
+
+    @validator("parent_id")
+    def validate_parent_id(cls, v):
+        if v is not None and v < 1:
+            raise ValueError("Invalid parent comment ID")
+        return v

--- /dev/null
+++ b/backend/app/services/sanitizer.py
@@ -0,0 +1,60 @@
+import bleach
+from typing import List
+import html
+import re
+
+# Allowed HTML tags and attributes for rich text
+ALLOWED_TAGS = ["b", "i", "u", "em", "strong", "a", "code", "pre", "br"]
+ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}
+ALLOWED_PROTOCOLS = ["http", "https", "mailto"]
+
+class ContentSanitizer:
+    @staticmethod
+    def sanitize_html(content: str, allow_tags: bool = False) -> str:
+        if allow_tags:
+            # Allow limited HTML formatting
+            return bleach.clean(
+                content,
+                tags=ALLOWED_TAGS,
+                attributes=ALLOWED_ATTRIBUTES,
+                protocols=ALLOWED_PROTOCOLS,
+                strip=True
+            )
+        else:
+            # Strip all HTML
+            return bleach.clean(content, tags=[], strip=True)
+
+    @staticmethod
+    def sanitize_plain_text(content: str) -> str:
+        # Escape HTML entities
+        content = html.escape(content)
+
+        # Remove control characters except newlines
+        content = re.sub(r"[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]", "", content)
+
+        return content
+
+    @staticmethod
+    def sanitize_url(url: str) -> str:
+        # Only allow safe protocols
+        if not re.match(r"^https?://", url, re.IGNORECASE):
+            return ""
+
+        # Remove javascript: and data: URLs that might be encoded
+        decoded = html.unescape(url.lower())
+        if "javascript:" in decoded or "data:" in decoded:
+            return ""
+
+        return bleach.clean(url)
+
+    @staticmethod
+    def linkify_urls(content: str) -> str:
+        return bleach.linkify(
+            content,
+            callbacks=[lambda attrs, new: {**attrs, ("rel", "noopener nofollow")}],
+            parse_email=False
+        )

--- /dev/null
+++ b/backend/app/api/comments.py
@@ -0,0 +1,55 @@
+from fastapi import APIRouter, Depends, HTTPException
+from sqlalchemy.orm import Session
+from app.db.session import get_db
+from app.schemas.comment import CommentCreate
+from app.services.sanitizer import ContentSanitizer
+from app.models import Comment, Post
+from app.core.security import get_current_user
+from app.core.rate_limit import rate_limit
+import logging
+
+router = APIRouter(prefix="/api/comments", tags=["Comments"])
+logger = logging.getLogger(__name__)
+
+@router.post("/{post_id}")
+@rate_limit(requests=10, window=60)  # 10 comments per minute
+async def create_comment(
+    post_id: int,
+    data: CommentCreate,
+    user = Depends(get_current_user),
+    db: Session = Depends(get_db)
+):
+    # Verify post exists
+    post = db.query(Post).filter(Post.id == post_id).first()
+    if not post:
+        raise HTTPException(404, "Post not found")
+
+    # Verify parent comment if provided
+    if data.parent_id:
+        parent = db.query(Comment).filter(
+            Comment.id == data.parent_id,
+            Comment.post_id == post_id
+        ).first()
+        if not parent:
+            raise HTTPException(400, "Invalid parent comment")
+
+    # Sanitize content
+    sanitized_content = ContentSanitizer.sanitize_html(
+        data.content,
+        allow_tags=True  # Allow basic formatting
+    )
+
+    # Create comment
+    comment = Comment(
+        post_id=post_id,
+        user_id=user.id,
+        content=sanitized_content,
+        parent_id=data.parent_id
+    )
+    db.add(comment)
+    db.commit()
+
+    # Audit log
+    logger.info(f"Comment created: user={user.id}, post={post_id}, id={comment.id}")
+
+    return {
+        "id": comment.id,
+        "content": comment.content,
+        "created_at": comment.created_at
+    }""",
            commands="""- cd backend && pip install bleach
- cd backend && pytest tests/test_sanitizer.py -v
- cd backend && pytest tests/test_comments.py -v""",
            notes="""- Bleach handles HTML sanitization safely
- Rate limiting prevents spam
- Audit logging for security monitoring
- Content-Security-Policy headers prevent inline scripts
- Consider adding CAPTCHA for anonymous comments"""
        )
    },
]


def format_example(item: dict) -> dict:
    """Format example for training."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": item["user"]},
            {"role": "assistant", "content": item["assistant"]}
        ],
        "category": item.get("category", "general")
    }


def generate_all_examples() -> List[dict]:
    """Generate all training examples."""
    all_examples = []

    # Combine all categories
    categories = [
        ("spec_to_implementation", SPEC_TO_IMPLEMENTATION),
        ("bug_fix", BUG_TO_FIX),
        ("add_tests", ADD_TESTS),
        ("refactor", REFACTOR_EXAMPLES),
        ("security", SECURITY_PATTERNS),
    ]

    for category_name, examples in categories:
        for item in examples:
            item["category"] = category_name
            all_examples.append(format_example(item))

    return all_examples


def main():
    print("=" * 70)
    print("GENERATING CLAUDE-STYLE TRAINING DATA")
    print("=" * 70)

    OUTPUT_DIR.mkdir(exist_ok=True)

    examples = generate_all_examples()

    # Count by category
    categories = {}
    for ex in examples:
        cat = ex.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nTotal Examples: {len(examples)}")
    print("\nBy Category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    # Save examples
    output_file = OUTPUT_DIR / "claude_style_sft.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"\nSaved to: {output_file}")

    # Create config
    config = {
        "version": "claude_style_v1",
        "total_examples": len(examples),
        "categories": categories,
        "output_format": {
            "sections": ["PLAN", "FILES", "PATCH", "COMMANDS", "NOTES"],
            "patch_format": "unified_diff"
        },
        "system_prompt": SYSTEM_PROMPT[:200] + "..."
    }

    with open(OUTPUT_DIR / "config.json", 'w') as f:
        json.dump(config, f, indent=2)

    print("\n" + "=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
