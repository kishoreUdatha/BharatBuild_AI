#!/usr/bin/env python3
"""
Generate Training Data for Coding Agent Fine-tuning

Strategy:
1. Spec → Implementation examples
2. Bug → Fix examples
3. Test-driven development examples
4. DPO preference pairs (bad vs good solutions)
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Tuple

OUTPUT_DIR = Path(__file__).parent / "coding_agent_data"

# ============================================================================
# 1. SPEC → IMPLEMENTATION EXAMPLES
# ============================================================================

SPEC_IMPLEMENTATIONS = [
    {
        "spec": """## Feature: User Authentication API

### Requirements:
1. POST /api/auth/register - Register new user with email/password
2. POST /api/auth/login - Login and return JWT token
3. GET /api/auth/me - Get current user (protected)
4. POST /api/auth/logout - Invalidate token

### Constraints:
- Password must be hashed with bcrypt
- JWT expires in 24 hours
- Email must be unique
- Validate email format""",
        "implementation": '''I'll implement the User Authentication API with FastAPI.

## auth/router.py

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
import os

from database import get_db
from models import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# Routes
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if email exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        name=user_data.name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # In a real app, you'd blacklist the token in Redis
    return {"message": "Successfully logged out"}
```

## models.py

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

## tests/test_auth.py

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register():
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "name": "Test User"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"

def test_login():
    response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_get_me():
    # Login first
    login_response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    token = login_response.json()["access_token"]

    # Get current user
    response = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
```
'''
    },
    {
        "spec": """## Feature: Shopping Cart API

### Requirements:
1. GET /api/cart - Get current user's cart
2. POST /api/cart/items - Add item to cart
3. PUT /api/cart/items/:id - Update item quantity
4. DELETE /api/cart/items/:id - Remove item from cart
5. POST /api/cart/checkout - Process checkout

### Business Rules:
- Cart persists across sessions
- Cannot add more than available stock
- Apply discounts at checkout
- Calculate totals with tax""",
        "implementation": '''I'll implement the Shopping Cart API.

## cart/router.py

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from decimal import Decimal

from database import get_db
from auth.router import get_current_user
from models import User, Cart, CartItem, Product

router = APIRouter(prefix="/api/cart", tags=["Cart"])

# Schemas
class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemUpdate(BaseModel):
    quantity: int

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    total: Decimal

class CheckoutRequest(BaseModel):
    discount_code: str = None

# Helper
def get_or_create_cart(user: User, db: Session) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user.id, Cart.status == "active").first()
    if not cart:
        cart = Cart(user_id=user.id, status="active")
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart

def calculate_cart_totals(cart: Cart, discount_code: str = None) -> dict:
    subtotal = sum(item.quantity * item.product.price for item in cart.items)

    # Apply discount
    discount = Decimal("0")
    if discount_code:
        if discount_code == "SAVE10":
            discount = subtotal * Decimal("0.10")
        elif discount_code == "SAVE20":
            discount = subtotal * Decimal("0.20")

    # Calculate tax (10%)
    taxable = subtotal - discount
    tax = taxable * Decimal("0.10")
    total = taxable + tax

    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": total
    }

# Routes
@router.get("/", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cart = get_or_create_cart(current_user, db)
    totals = calculate_cart_totals(cart)

    return {
        "id": cart.id,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": item.product.price,
                "subtotal": item.quantity * item.product.price
            }
            for item in cart.items
        ],
        **totals
    }

@router.post("/items", status_code=201)
async def add_item(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cart = get_or_create_cart(current_user, db)

    # Check product exists and has stock
    product = db.query(Product).filter(Product.id == item_data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.stock < item_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    # Check if item already in cart
    existing = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == item_data.product_id
    ).first()

    if existing:
        new_qty = existing.quantity + item_data.quantity
        if product.stock < new_qty:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        existing.quantity = new_qty
        db.commit()
        return {"message": "Item quantity updated", "quantity": new_qty}

    # Add new item
    cart_item = CartItem(
        cart_id=cart.id,
        product_id=item_data.product_id,
        quantity=item_data.quantity
    )
    db.add(cart_item)
    db.commit()

    return {"message": "Item added to cart"}

@router.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item_data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cart = get_or_create_cart(current_user, db)

    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if item_data.quantity <= 0:
        db.delete(item)
        db.commit()
        return {"message": "Item removed from cart"}

    if item.product.stock < item_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    item.quantity = item_data.quantity
    db.commit()

    return {"message": "Item updated"}

@router.delete("/items/{item_id}")
async def remove_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cart = get_or_create_cart(current_user, db)

    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(item)
    db.commit()

    return {"message": "Item removed"}

@router.post("/checkout")
async def checkout(
    checkout_data: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cart = get_or_create_cart(current_user, db)

    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Verify stock for all items
    for item in cart.items:
        if item.product.stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {item.product.name}"
            )

    # Calculate totals
    totals = calculate_cart_totals(cart, checkout_data.discount_code)

    # Create order (simplified)
    # In real app: create Order, OrderItems, process payment, update stock

    # Update stock
    for item in cart.items:
        item.product.stock -= item.quantity

    # Mark cart as completed
    cart.status = "completed"
    db.commit()

    return {
        "message": "Checkout successful",
        "order_total": totals["total"]
    }
```
'''
    },
]

# ============================================================================
# 2. BUG → FIX EXAMPLES
# ============================================================================

BUG_FIXES = [
    {
        "bug_report": """## Bug Report

**Title:** Memory leak in WebSocket connection handler

**Description:** The application memory keeps growing when clients connect/disconnect from WebSocket.

**Steps to reproduce:**
1. Connect 100 WebSocket clients
2. Disconnect all clients
3. Memory usage doesn't decrease

**Code:**
```python
class WebSocketManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
```""",
        "fix": '''## Bug Analysis

The memory leak occurs because disconnected WebSocket connections are never removed from `active_connections`. The list keeps growing with stale connection references.

## Fix

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove disconnected client from active connections."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Broadcast message to all clients, removing dead connections."""
        dead_connections = []

        async with self._lock:
            connections = self.active_connections.copy()

        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for conn in dead_connections:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
            logger.info(f"Cleaned up {len(dead_connections)} dead connections")

# Usage in endpoint
manager = WebSocketManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)
```

## Changes Made:

1. **Added `disconnect()` method** - Properly removes connections when clients disconnect
2. **Added thread-safe lock** - Prevents race conditions when modifying the list
3. **Added dead connection cleanup in `broadcast()`** - Catches and removes failed connections
4. **Used `try/except` in endpoint** - Ensures cleanup happens on any error
5. **Added logging** - For monitoring connection count

## Test:

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_memory_cleanup():
    manager = WebSocketManager()

    # Simulate 100 connections
    mock_websockets = [MockWebSocket() for _ in range(100)]
    for ws in mock_websockets:
        await manager.connect(ws)

    assert len(manager.active_connections) == 100

    # Disconnect all
    for ws in mock_websockets:
        await manager.disconnect(ws)

    assert len(manager.active_connections) == 0  # Memory freed
```
'''
    },
    {
        "bug_report": """## Bug Report

**Title:** SQL Injection vulnerability in search endpoint

**Description:** The search endpoint is vulnerable to SQL injection attacks.

**Code:**
```python
@app.get("/api/search")
async def search(query: str, db: Session = Depends(get_db)):
    sql = f"SELECT * FROM products WHERE name LIKE '%{query}%'"
    results = db.execute(sql).fetchall()
    return results
```

**Attack example:**
```
GET /api/search?query=' OR '1'='1
```""",
        "fix": '''## Security Analysis

This is a critical SQL injection vulnerability. The user input is directly concatenated into the SQL query without any sanitization, allowing attackers to:
- Extract all data from the database
- Modify or delete data
- Bypass authentication

## Fix

```python
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query
from typing import List
from pydantic import BaseModel
import re

router = APIRouter()

class ProductResponse(BaseModel):
    id: int
    name: str
    price: float

    class Config:
        from_attributes = True

# Option 1: Use ORM (Recommended)
@app.get("/api/search", response_model=List[ProductResponse])
async def search_safe(
    query: str = Query(..., min_length=1, max_length=100),
    db: Session = Depends(get_db)
):
    # SQLAlchemy ORM automatically parameterizes queries
    results = db.query(Product).filter(
        Product.name.ilike(f"%{query}%")
    ).limit(100).all()
    return results

# Option 2: Use parameterized queries if raw SQL needed
@app.get("/api/search/v2")
async def search_parameterized(
    query: str = Query(..., min_length=1, max_length=100),
    db: Session = Depends(get_db)
):
    # Use parameterized query with :param syntax
    sql = text("SELECT * FROM products WHERE name ILIKE :search LIMIT 100")
    results = db.execute(sql, {"search": f"%{query}%"}).fetchall()
    return [dict(row._mapping) for row in results]

# Option 3: Additional input validation
def sanitize_search_query(query: str) -> str:
    """Remove potentially dangerous characters."""
    # Only allow alphanumeric, spaces, and basic punctuation
    return re.sub(r"[^\\w\\s\\-\\.]", "", query)

@app.get("/api/search/v3")
async def search_sanitized(
    query: str = Query(..., min_length=1, max_length=100),
    db: Session = Depends(get_db)
):
    clean_query = sanitize_search_query(query)
    results = db.query(Product).filter(
        Product.name.ilike(f"%{clean_query}%")
    ).limit(100).all()
    return results
```

## Security Measures Applied:

1. **Use ORM queries** - SQLAlchemy automatically escapes parameters
2. **Parameterized queries** - Never concatenate user input into SQL
3. **Input validation** - Limit length, validate format with Pydantic
4. **Result limiting** - Prevent data extraction with LIMIT
5. **Input sanitization** - Remove special characters if needed

## Test:

```python
def test_sql_injection_prevented():
    # These malicious inputs should NOT affect the query
    malicious_inputs = [
        "' OR '1'='1",
        "'; DROP TABLE products; --",
        "' UNION SELECT * FROM users --",
    ]

    for payload in malicious_inputs:
        response = client.get(f"/api/search?query={payload}")
        assert response.status_code == 200
        # Should return empty or only matching products, not all data
        assert len(response.json()) < 100
```
'''
    },
    {
        "bug_report": """## Bug Report

**Title:** Race condition in inventory update

**Description:** When multiple users purchase the same product simultaneously, the inventory count goes negative.

**Code:**
```python
@app.post("/api/orders")
async def create_order(product_id: int, quantity: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if product.stock >= quantity:
        product.stock -= quantity
        order = Order(product_id=product_id, quantity=quantity)
        db.add(order)
        db.commit()
        return {"success": True}

    return {"error": "Insufficient stock"}
```""",
        "fix": '''## Bug Analysis

This is a classic race condition. Between checking `product.stock >= quantity` and updating `product.stock -= quantity`, another request can read the same stock value, leading to overselling.

**Timeline of race condition:**
1. Request A reads stock = 5
2. Request B reads stock = 5
3. Request A: 5 >= 3? Yes, stock = 5 - 3 = 2
4. Request B: 5 >= 4? Yes, stock = 5 - 4 = 1
5. Both orders succeed, but actual stock should be -2

## Fix

```python
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
import asyncio

# Option 1: Database-level locking (FOR UPDATE)
@app.post("/api/orders")
async def create_order_with_lock(
    product_id: int,
    quantity: int,
    db: Session = Depends(get_db)
):
    try:
        # Lock the row for update - prevents other transactions from reading
        product = db.query(Product).filter(
            Product.id == product_id
        ).with_for_update().first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        if product.stock < quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")

        product.stock -= quantity
        order = Order(product_id=product_id, quantity=quantity)
        db.add(order)
        db.commit()

        return {"success": True, "remaining_stock": product.stock}

    except Exception as e:
        db.rollback()
        raise

# Option 2: Atomic update with condition (Optimistic locking)
@app.post("/api/orders/v2")
async def create_order_atomic(
    product_id: int,
    quantity: int,
    db: Session = Depends(get_db)
):
    # Atomic update - only succeeds if stock >= quantity
    result = db.execute(
        text("""
            UPDATE products
            SET stock = stock - :quantity
            WHERE id = :product_id AND stock >= :quantity
            RETURNING stock
        """),
        {"product_id": product_id, "quantity": quantity}
    )

    row = result.fetchone()

    if not row:
        db.rollback()
        raise HTTPException(status_code=400, detail="Insufficient stock")

    order = Order(product_id=product_id, quantity=quantity)
    db.add(order)
    db.commit()

    return {"success": True, "remaining_stock": row[0]}

# Option 3: Optimistic locking with version
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    stock = Column(Integer, default=0)
    version = Column(Integer, default=0)  # Version for optimistic locking

@app.post("/api/orders/v3")
async def create_order_optimistic(
    product_id: int,
    quantity: int,
    db: Session = Depends(get_db),
    max_retries: int = 3
):
    for attempt in range(max_retries):
        product = db.query(Product).filter(Product.id == product_id).first()

        if product.stock < quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")

        # Try to update with version check
        result = db.execute(
            text("""
                UPDATE products
                SET stock = stock - :quantity, version = version + 1
                WHERE id = :product_id AND version = :version AND stock >= :quantity
            """),
            {
                "product_id": product_id,
                "quantity": quantity,
                "version": product.version
            }
        )

        if result.rowcount > 0:
            order = Order(product_id=product_id, quantity=quantity)
            db.add(order)
            db.commit()
            return {"success": True}

        db.rollback()
        await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

    raise HTTPException(status_code=409, detail="Concurrent update conflict")
```

## Test:

```python
import asyncio
import pytest

@pytest.mark.asyncio
async def test_concurrent_orders():
    # Set stock to 10
    product = create_product(stock=10)

    # Try to order 3 units 5 times concurrently (15 total, only 10 available)
    tasks = [
        create_order_async(product.id, quantity=3)
        for _ in range(5)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count successes
    successes = sum(1 for r in results if not isinstance(r, Exception))

    # Only 3 orders should succeed (3 * 3 = 9 <= 10)
    assert successes == 3

    # Stock should never be negative
    product = get_product(product.id)
    assert product.stock >= 0
```
'''
    },
]

# ============================================================================
# 3. TEST-DRIVEN DEVELOPMENT EXAMPLES
# ============================================================================

TDD_EXAMPLES = [
    {
        "test_first": """## TDD: Password Validator

Write tests first, then implement.

### Requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*)

### Tests:

```python
import pytest
from password_validator import validate_password, PasswordValidationError

class TestPasswordValidator:
    def test_valid_password(self):
        assert validate_password("SecurePass1!") == True

    def test_too_short(self):
        with pytest.raises(PasswordValidationError) as exc:
            validate_password("Short1!")
        assert "at least 8 characters" in str(exc.value)

    def test_no_uppercase(self):
        with pytest.raises(PasswordValidationError) as exc:
            validate_password("lowercase1!")
        assert "uppercase" in str(exc.value)

    def test_no_lowercase(self):
        with pytest.raises(PasswordValidationError) as exc:
            validate_password("UPPERCASE1!")
        assert "lowercase" in str(exc.value)

    def test_no_digit(self):
        with pytest.raises(PasswordValidationError) as exc:
            validate_password("NoDigits!")
        assert "digit" in str(exc.value)

    def test_no_special_char(self):
        with pytest.raises(PasswordValidationError) as exc:
            validate_password("NoSpecial1")
        assert "special character" in str(exc.value)

    def test_multiple_errors(self):
        with pytest.raises(PasswordValidationError) as exc:
            validate_password("weak")
        # Should report all issues
        errors = str(exc.value)
        assert "8 characters" in errors
        assert "uppercase" in errors
        assert "digit" in errors
        assert "special" in errors
```""",
        "implementation": '''## Implementation to pass all tests:

```python
import re
from typing import List

class PasswordValidationError(Exception):
    """Raised when password validation fails."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))

def validate_password(password: str) -> bool:
    """
    Validate password against security requirements.

    Args:
        password: The password to validate

    Returns:
        True if valid

    Raises:
        PasswordValidationError: If validation fails
    """
    errors = []

    # Check minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")

    # Check for uppercase
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    # Check for lowercase
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    # Check for digit
    if not re.search(r"\\d", password):
        errors.append("Password must contain at least one digit")

    # Check for special character
    if not re.search(r"[!@#$%^&*]", password):
        errors.append("Password must contain at least one special character (!@#$%^&*)")

    if errors:
        raise PasswordValidationError(errors)

    return True


# Additional utility functions

def get_password_strength(password: str) -> str:
    """Get password strength rating."""
    score = 0

    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1

    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"\\d", password):
        score += 1
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1

    if score <= 3:
        return "weak"
    elif score <= 5:
        return "medium"
    else:
        return "strong"


def suggest_improvements(password: str) -> List[str]:
    """Suggest ways to improve password."""
    suggestions = []

    if len(password) < 12:
        suggestions.append("Consider using at least 12 characters")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        suggestions.append("Add special characters for extra security")

    if re.search(r"(.)\\1{2,}", password):
        suggestions.append("Avoid repeating characters")

    common_patterns = ["123", "abc", "qwerty", "password"]
    if any(p in password.lower() for p in common_patterns):
        suggestions.append("Avoid common patterns")

    return suggestions
```

## Running tests:

```bash
$ pytest test_password_validator.py -v

test_password_validator.py::TestPasswordValidator::test_valid_password PASSED
test_password_validator.py::TestPasswordValidator::test_too_short PASSED
test_password_validator.py::TestPasswordValidator::test_no_uppercase PASSED
test_password_validator.py::TestPasswordValidator::test_no_lowercase PASSED
test_password_validator.py::TestPasswordValidator::test_no_digit PASSED
test_password_validator.py::TestPasswordValidator::test_no_special_char PASSED
test_password_validator.py::TestPasswordValidator::test_multiple_errors PASSED

7 passed in 0.05s
```
'''
    },
]

# ============================================================================
# 4. DPO PREFERENCE PAIRS (Bad vs Good)
# ============================================================================

DPO_PAIRS = [
    {
        "prompt": "Write a function to read a file and return its contents",
        "rejected": '''```python
def read_file(filename):
    f = open(filename)
    content = f.read()
    return content
```''',
        "chosen": '''```python
from pathlib import Path
from typing import Optional

def read_file(filename: str, encoding: str = "utf-8") -> Optional[str]:
    """
    Read and return file contents.

    Args:
        filename: Path to the file
        encoding: File encoding (default: utf-8)

    Returns:
        File contents as string, or None if file doesn't exist

    Raises:
        IOError: If file cannot be read
    """
    path = Path(filename)

    if not path.exists():
        return None

    try:
        with open(path, "r", encoding=encoding) as f:
            return f.read()
    except IOError as e:
        raise IOError(f"Failed to read file {filename}: {e}")
```

**Why this is better:**
- Uses context manager (`with`) to ensure file is closed
- Has type hints for clarity
- Handles missing files gracefully
- Proper error handling
- Docstring explains usage
- Uses Path for cross-platform compatibility
'''
    },
    {
        "prompt": "Create a REST API endpoint to get user by ID",
        "rejected": '''```python
@app.get("/user")
def get_user(id):
    user = db.execute(f"SELECT * FROM users WHERE id = {id}")
    return user
```''',
        "chosen": '''```python
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int = Path(..., gt=0, description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get user by ID.

    - **user_id**: The unique identifier of the user

    Returns user details or 404 if not found.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )

    return user
```

**Why this is better:**
- RESTful URL with path parameter (`/users/{id}`)
- SQL injection safe (uses ORM)
- Proper HTTP status codes (404 for not found)
- Input validation (id must be > 0)
- Response model for serialization
- Async for better performance
- API documentation with docstring
'''
    },
    {
        "prompt": "Write a function to hash a password",
        "rejected": '''```python
import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
```''',
        "chosen": '''```python
import bcrypt
from typing import Tuple

def hash_password(password: str, rounds: int = 12) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password
        rounds: Work factor (default 12, higher = slower but more secure)

    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        hashed: Previously hashed password

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed.encode("utf-8")
    )
```

**Why this is better:**
- Uses bcrypt (industry standard for password hashing)
- MD5 is cryptographically broken and unsuitable for passwords
- Includes automatic salting (prevents rainbow table attacks)
- Configurable work factor for security tuning
- Includes verification function
- Type hints and documentation
'''
    },
    {
        "prompt": "Handle errors in an async function",
        "rejected": '''```python
async def fetch_data(url):
    response = await httpx.get(url)
    return response.json()
```''',
        "chosen": '''```python
import httpx
import asyncio
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

class FetchError(Exception):
    """Custom exception for fetch failures."""
    pass

async def fetch_data(
    url: str,
    timeout: float = 30.0,
    retries: int = 3,
    backoff: float = 1.0
) -> Optional[Any]:
    """
    Fetch JSON data from URL with retry logic.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        backoff: Initial backoff delay (doubles each retry)

    Returns:
        Parsed JSON response

    Raises:
        FetchError: If all retries fail
    """
    last_error = None

    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException as e:
            last_error = e
            logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{retries})")

        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                # Retry on server errors
                last_error = e
                logger.warning(f"Server error {e.response.status_code} (attempt {attempt + 1})")
            else:
                # Don't retry on client errors (4xx)
                raise FetchError(f"HTTP {e.response.status_code}: {e.response.text}")

        except httpx.RequestError as e:
            last_error = e
            logger.warning(f"Request error: {e} (attempt {attempt + 1})")

        # Exponential backoff before retry
        if attempt < retries - 1:
            delay = backoff * (2 ** attempt)
            await asyncio.sleep(delay)

    raise FetchError(f"Failed after {retries} attempts: {last_error}")
```

**Why this is better:**
- Retry logic with exponential backoff
- Proper timeout handling
- Distinguishes between retryable and non-retryable errors
- Logging for debugging
- Custom exception for clear error handling
- Type hints and documentation
- Uses context manager for client
'''
    },
]


def generate_spec_implementation_examples() -> List[Dict]:
    """Generate Spec → Implementation training examples."""
    examples = []

    for item in SPEC_IMPLEMENTATIONS:
        examples.append({
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert software engineer. Given a specification, implement production-ready code with proper error handling, validation, and tests."
                },
                {
                    "role": "user",
                    "content": f"Implement the following specification:\n\n{item['spec']}"
                },
                {
                    "role": "assistant",
                    "content": item['implementation']
                }
            ]
        })

    return examples


def generate_bug_fix_examples() -> List[Dict]:
    """Generate Bug → Fix training examples."""
    examples = []

    for item in BUG_FIXES:
        examples.append({
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert debugger. Analyze the bug, explain the root cause, and provide a comprehensive fix with tests."
                },
                {
                    "role": "user",
                    "content": item['bug_report']
                },
                {
                    "role": "assistant",
                    "content": item['fix']
                }
            ]
        })

    return examples


def generate_tdd_examples() -> List[Dict]:
    """Generate TDD training examples."""
    examples = []

    for item in TDD_EXAMPLES:
        examples.append({
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert TDD practitioner. Given tests, implement code that makes all tests pass."
                },
                {
                    "role": "user",
                    "content": item['test_first']
                },
                {
                    "role": "assistant",
                    "content": item['implementation']
                }
            ]
        })

    return examples


def generate_dpo_pairs() -> List[Dict]:
    """Generate DPO preference pairs for preference tuning."""
    examples = []

    for item in DPO_PAIRS:
        # DPO format: prompt, chosen, rejected
        examples.append({
            "prompt": item['prompt'],
            "chosen": item['chosen'],
            "rejected": item['rejected']
        })

    return examples


def main():
    print("=" * 70)
    print("GENERATING CODING AGENT TRAINING DATA")
    print("=" * 70)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Generate SFT examples
    spec_examples = generate_spec_implementation_examples()
    bug_examples = generate_bug_fix_examples()
    tdd_examples = generate_tdd_examples()

    sft_examples = spec_examples + bug_examples + tdd_examples
    print(f"\nSFT Examples: {len(sft_examples)}")
    print(f"  - Spec to Implementation: {len(spec_examples)}")
    print(f"  - Bug to Fix: {len(bug_examples)}")
    print(f"  - TDD: {len(tdd_examples)}")

    # Save SFT data
    with open(OUTPUT_DIR / "sft_train.jsonl", 'w', encoding='utf-8') as f:
        for ex in sft_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    # Generate DPO pairs
    dpo_pairs = generate_dpo_pairs()
    print(f"\nDPO Pairs: {len(dpo_pairs)}")

    # Save DPO data
    with open(OUTPUT_DIR / "dpo_pairs.jsonl", 'w', encoding='utf-8') as f:
        for pair in dpo_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    print(f"\nSaved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
