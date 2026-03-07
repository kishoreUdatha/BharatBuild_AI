"""
Complex Task Training Data Generator
Generates training examples for:
1. Debugging and error fixing
2. Code explanation
3. Code refactoring
4. Performance optimization
5. Security analysis
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any


# ============================================================================
# DEBUGGING EXAMPLES
# ============================================================================

DEBUGGING_EXAMPLES = [
    {
        "error": "TypeError: Cannot read properties of undefined (reading 'map')",
        "code": '''function UserList({ users }) {
  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}''',
        "explanation": "The error occurs because `users` is undefined when the component first renders.",
        "fix": '''function UserList({ users = [] }) {
  if (!users || users.length === 0) {
    return <p>No users found</p>;
  }

  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}''',
        "learning": [
            "Always provide default values for props that might be undefined",
            "Add null checks before calling array methods",
            "Consider loading states for async data"
        ]
    },
    {
        "error": "sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint",
        "code": '''@router.post("/users")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    return db_user''',
        "explanation": "The error occurs when trying to create a user with an email that already exists.",
        "fix": '''@router.post("/users")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )

    try:
        db_user = User(**user.dict())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Could not create user"
        )''',
        "learning": [
            "Always check for existing records before insert",
            "Wrap database operations in try-except",
            "Rollback on database errors",
            "Return meaningful error messages"
        ]
    },
    {
        "error": "CORS error: Access to XMLHttpRequest has been blocked",
        "code": '''from fastapi import FastAPI

app = FastAPI()

@app.get("/api/data")
async def get_data():
    return {"message": "Hello"}''',
        "explanation": "The error occurs because CORS middleware is not configured, blocking cross-origin requests.",
        "fix": '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/data")
async def get_data():
    return {"message": "Hello"}''',
        "learning": [
            "Always configure CORS for APIs consumed by web frontends",
            "Be specific about allowed origins in production",
            "allow_credentials=True is needed for cookies/auth headers"
        ]
    },
    {
        "error": "TypeError: object of type 'NoneType' has no len()",
        "code": '''def get_user_posts(user_id: int, db: Session):
    posts = db.query(Post).filter(Post.user_id == user_id).all()
    return {"count": len(posts), "posts": posts}''',
        "explanation": "The query returns None instead of an empty list when no posts are found.",
        "fix": '''def get_user_posts(user_id: int, db: Session):
    posts = db.query(Post).filter(Post.user_id == user_id).all()

    # .all() returns empty list, but let's be defensive
    if posts is None:
        posts = []

    return {
        "count": len(posts),
        "posts": posts,
        "has_posts": len(posts) > 0
    }''',
        "learning": [
            "SQLAlchemy .all() returns empty list, not None",
            "Add defensive checks for None values",
            "Return additional metadata like has_posts for better UX"
        ]
    },
    {
        "error": "React Hook useEffect has a missing dependency",
        "code": '''function SearchResults({ query }) {
  const [results, setResults] = useState([]);

  useEffect(() => {
    fetchResults(query).then(setResults);
  }, []); // Missing dependency: query

  return <ResultsList results={results} />;
}''',
        "explanation": "The useEffect hook uses `query` but doesn't include it in the dependency array, causing stale closures.",
        "fix": '''function SearchResults({ query }) {
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!query) {
      setResults([]);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchResults(query)
      .then(data => {
        if (!cancelled) {
          setResults(data);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [query]); // Include query in dependencies

  if (error) return <ErrorMessage error={error} />;
  if (isLoading) return <LoadingSpinner />;
  return <ResultsList results={results} />;
}''',
        "learning": [
            "Always include all dependencies in useEffect dependency array",
            "Use cleanup functions to prevent state updates on unmounted components",
            "Handle loading and error states properly"
        ]
    },
]


# ============================================================================
# CODE EXPLANATION EXAMPLES
# ============================================================================

CODE_EXPLANATION_EXAMPLES = [
    {
        "code": '''async function* paginatedFetch(url, pageSize = 10) {
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const response = await fetch(`${url}?page=${page}&limit=${pageSize}`);
    const data = await response.json();

    yield data.items;

    hasMore = data.items.length === pageSize;
    page++;
  }
}''',
        "explanation": '''This is an **async generator function** for paginated API fetching. Let me break it down:

## What It Does
This function fetches data from an API page by page, yielding results as they come in rather than waiting for all pages to load.

## Key Concepts

### 1. Async Generator (`async function*`)
- The `*` makes it a generator function
- `async` allows using `await` inside
- Returns an async iterator that can be consumed with `for await...of`

### 2. How It Works
```
Page 1: Fetch → Yield items → Check if more
Page 2: Fetch → Yield items → Check if more
...continues until no more data
```

### 3. The `yield` Keyword
- Pauses execution and returns `data.items`
- Resumes when consumer requests next value
- Memory efficient: doesn't load all pages at once

### 4. Termination Logic
```javascript
hasMore = data.items.length === pageSize;
```
If we get fewer items than requested, we've reached the last page.

## Usage Example
```javascript
const fetcher = paginatedFetch('/api/users');

for await (const users of fetcher) {
  console.log('Got batch:', users);
  // Process each batch as it arrives
}
```

## Benefits
1. **Memory efficient**: Only one page in memory at a time
2. **Progressive loading**: Show data as it arrives
3. **Cancellable**: Can stop iteration early
4. **Clean API**: Hides pagination complexity

## Real-World Use Case
Perfect for infinite scroll UIs, data exports, or processing large datasets.
'''
    },
    {
        "code": '''const useDebounce = (value, delay = 500) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
};''',
        "explanation": '''This is a **custom React hook for debouncing values**. Let me explain:

## What is Debouncing?
Debouncing delays executing an action until a pause in activity. Like waiting for someone to stop typing before searching.

## How This Hook Works

### Step-by-Step Flow
```
User types "h"  → Start 500ms timer
User types "e"  → Cancel timer, start new 500ms timer
User types "l"  → Cancel timer, start new 500ms timer
User types "l"  → Cancel timer, start new 500ms timer
User types "o"  → Cancel timer, start new 500ms timer
User stops      → 500ms passes → Update debouncedValue to "hello"
```

### The Code Breakdown

1. **State for debounced value**
```javascript
const [debouncedValue, setDebouncedValue] = useState(value);
```
Stores the delayed/debounced version.

2. **Effect that runs on value change**
```javascript
useEffect(() => {
  const timer = setTimeout(() => {
    setDebouncedValue(value);
  }, delay);
```
Sets a timer to update the debounced value after `delay` ms.

3. **Cleanup function (key part!)**
```javascript
  return () => clearTimeout(timer);
}, [value, delay]);
```
When `value` changes, this cleanup runs FIRST, canceling the previous timer.

## Usage Example
```jsx
function SearchInput() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery) {
      searchAPI(debouncedQuery); // Only called 300ms after typing stops
    }
  }, [debouncedQuery]);

  return <input value={query} onChange={e => setQuery(e.target.value)} />;
}
```

## Why Use This?
1. **Performance**: Reduces API calls while typing
2. **Cost**: Fewer server requests = lower costs
3. **UX**: Prevents flickering from rapid updates
'''
    },
    {
        "code": '''class Singleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance''',
        "explanation": '''This is a **thread-safe Singleton pattern** in Python. Let me explain:

## What is Singleton?
A design pattern that ensures a class has only ONE instance throughout the application.

## Why Thread-Safe?
In multi-threaded apps, two threads might try to create the instance simultaneously. Without protection, you could end up with multiple instances.

## The Double-Check Locking Pattern

### Step-by-Step
```python
def __new__(cls):
    # First check (no lock - fast path)
    if cls._instance is None:
        # Only lock if instance might need creation
        with cls._lock:
            # Second check (with lock - safe)
            if cls._instance is None:
                cls._instance = super().__new__(cls)
    return cls._instance
```

### Why Two Checks?

**First check (outside lock)**:
- Quick check without acquiring lock
- If instance exists, return immediately
- Avoids lock overhead for common case

**Second check (inside lock)**:
- Another thread might have created instance while we waited for lock
- Must check again to prevent duplicate creation

## Visual Example
```
Thread A                    Thread B
--------                    --------
Check: _instance is None
                           Check: _instance is None
Acquire lock
                           Wait for lock...
Check again: None
Create instance
Release lock
                           Acquire lock
                           Check again: NOT None!
                           Skip creation
                           Release lock
Return instance            Return instance
```

## Usage
```python
# Both variables reference the SAME object
db1 = DatabaseConnection()
db2 = DatabaseConnection()
assert db1 is db2  # True!
```

## When to Use
- Database connections
- Configuration managers
- Logging
- Caches
'''
    },
]


# ============================================================================
# REFACTORING EXAMPLES
# ============================================================================

REFACTORING_EXAMPLES = [
    {
        "before": '''def process_order(order_data):
    # Validate
    if not order_data.get('customer_id'):
        return {'error': 'Customer ID required'}
    if not order_data.get('items'):
        return {'error': 'Items required'}
    if len(order_data['items']) == 0:
        return {'error': 'At least one item required'}

    # Calculate total
    total = 0
    for item in order_data['items']:
        price = get_product_price(item['product_id'])
        total += price * item['quantity']

    # Apply discount
    if order_data.get('coupon_code'):
        discount = get_coupon_discount(order_data['coupon_code'])
        total = total - (total * discount / 100)

    # Apply tax
    tax = total * 0.1
    total = total + tax

    # Save order
    order = Order(
        customer_id=order_data['customer_id'],
        items=order_data['items'],
        subtotal=total - tax,
        tax=tax,
        total=total,
        status='pending'
    )
    db.session.add(order)
    db.session.commit()

    # Send notification
    customer = get_customer(order_data['customer_id'])
    send_email(customer.email, 'Order Confirmation', f'Order {order.id} confirmed')

    return {'order_id': order.id, 'total': total}''',
        "after": '''from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal


@dataclass
class OrderItem:
    product_id: str
    quantity: int
    unit_price: Decimal = Decimal('0')


@dataclass
class OrderRequest:
    customer_id: str
    items: List[OrderItem]
    coupon_code: Optional[str] = None


class OrderValidationError(Exception):
    pass


class OrderService:
    TAX_RATE = Decimal('0.10')

    def __init__(self, db, product_service, coupon_service, notification_service):
        self.db = db
        self.product_service = product_service
        self.coupon_service = coupon_service
        self.notification_service = notification_service

    def create_order(self, request: OrderRequest) -> Order:
        self._validate(request)

        subtotal = self._calculate_subtotal(request.items)
        discount = self._apply_discount(subtotal, request.coupon_code)
        tax = self._calculate_tax(subtotal - discount)
        total = subtotal - discount + tax

        order = self._save_order(request, subtotal, discount, tax, total)
        self._send_confirmation(request.customer_id, order)

        return order

    def _validate(self, request: OrderRequest) -> None:
        if not request.customer_id:
            raise OrderValidationError("Customer ID required")
        if not request.items:
            raise OrderValidationError("At least one item required")

    def _calculate_subtotal(self, items: List[OrderItem]) -> Decimal:
        total = Decimal('0')
        for item in items:
            price = self.product_service.get_price(item.product_id)
            item.unit_price = price
            total += price * item.quantity
        return total

    def _apply_discount(self, subtotal: Decimal, coupon_code: Optional[str]) -> Decimal:
        if not coupon_code:
            return Decimal('0')
        discount_percent = self.coupon_service.get_discount(coupon_code)
        return subtotal * discount_percent / 100

    def _calculate_tax(self, amount: Decimal) -> Decimal:
        return amount * self.TAX_RATE

    def _save_order(self, request, subtotal, discount, tax, total) -> Order:
        order = Order(
            customer_id=request.customer_id,
            items=[item.__dict__ for item in request.items],
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total,
            status='pending'
        )
        self.db.session.add(order)
        self.db.session.commit()
        return order

    def _send_confirmation(self, customer_id: str, order: Order) -> None:
        try:
            self.notification_service.send_order_confirmation(customer_id, order)
        except Exception as e:
            # Log but don't fail the order
            logger.error(f"Failed to send confirmation: {e}")''',
        "improvements": [
            "**Single Responsibility**: Each method does one thing",
            "**Dependency Injection**: Services injected, easier to test",
            "**Type Safety**: Dataclasses with type hints",
            "**Decimal for Money**: Avoids floating-point errors",
            "**Error Handling**: Custom exceptions, graceful notification failure",
            "**Testability**: Mock dependencies easily",
            "**Clean Code**: Small, focused methods with clear names"
        ]
    },
]


# ============================================================================
# GENERATOR FUNCTIONS
# ============================================================================

def generate_debugging_example(example: Dict) -> str:
    """Generate a debugging training response"""
    learning_points = '\n'.join([f"- {point}" for point in example['learning']])

    return f'''## Error Analysis

**Error Message:**
```
{example['error']}
```

**Problematic Code:**
```
{example['code']}
```

## Root Cause
{example['explanation']}

## Fixed Code
```
{example['fix']}
```

## Key Learning Points
{learning_points}

## Prevention Tips
1. Add proper error handling from the start
2. Write unit tests for edge cases
3. Use TypeScript/type hints for early error detection
4. Add defensive checks for external data
'''


def generate_explanation_example(example: Dict) -> str:
    """Generate a code explanation training response"""
    return example['explanation']


def generate_refactoring_example(example: Dict) -> str:
    """Generate a refactoring training response"""
    improvements = '\n'.join([f"{i+1}. {imp}" for i, imp in enumerate(example['improvements'])])

    return f'''## Code Review & Refactoring

### Original Code (Before)
```python
{example['before']}
```

### Problems with Original Code
1. **Too many responsibilities** - Validation, calculation, persistence, notification in one function
2. **Hard to test** - Direct dependencies, no mocking possible
3. **No type safety** - Dictionary-based, error-prone
4. **Magic numbers** - Tax rate hardcoded
5. **Poor error handling** - Returns dict instead of raising exceptions

### Refactored Code (After)
```python
{example['after']}
```

### Improvements Made
{improvements}

### How to Test the Refactored Code
```python
def test_create_order():
    # Arrange
    mock_db = Mock()
    mock_product_service = Mock()
    mock_product_service.get_price.return_value = Decimal('10.00')
    mock_coupon_service = Mock()
    mock_notification_service = Mock()

    service = OrderService(
        mock_db,
        mock_product_service,
        mock_coupon_service,
        mock_notification_service
    )

    request = OrderRequest(
        customer_id='123',
        items=[OrderItem(product_id='prod1', quantity=2)]
    )

    # Act
    order = service.create_order(request)

    # Assert
    assert order.subtotal == Decimal('20.00')
    assert order.tax == Decimal('2.00')
    mock_db.session.add.assert_called_once()
```
'''


def create_training_example(system_prompt: str, user_prompt: str, assistant_response: str) -> Dict:
    """Create a single training example"""
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ]
    }


def generate_complex_task_training_data(output_file: Path, num_examples: int = 300):
    """Generate complex task training data"""

    examples = []

    # Debugging examples
    debug_system_prompt = "You are an expert debugger. Analyze errors, identify root causes, provide fixes, and explain the solution clearly."

    debug_prompts = [
        "Debug this error: {error}\n\nCode:\n```\n{code}\n```",
        "I'm getting this error: {error}\n\nHere's my code:\n```\n{code}\n```\n\nPlease help me fix it.",
        "Fix this bug: {error}\n\n```\n{code}\n```",
    ]

    for debug_example in DEBUGGING_EXAMPLES:
        for prompt_template in debug_prompts:
            user_prompt = prompt_template.format(
                error=debug_example['error'],
                code=debug_example['code']
            )
            response = generate_debugging_example(debug_example)

            examples.append(create_training_example(
                debug_system_prompt,
                user_prompt,
                response
            ))

    # Code explanation examples
    explain_system_prompt = "You are a coding teacher. Explain code clearly with examples, analogies, and practical applications."

    explain_prompts = [
        "Explain this code:\n```\n{code}\n```",
        "What does this code do?\n```\n{code}\n```",
        "Help me understand this code:\n```\n{code}\n```",
        "Break down this code and explain how it works:\n```\n{code}\n```",
    ]

    for explain_example in CODE_EXPLANATION_EXAMPLES:
        for prompt_template in explain_prompts:
            user_prompt = prompt_template.format(code=explain_example['code'])
            response = generate_explanation_example(explain_example)

            examples.append(create_training_example(
                explain_system_prompt,
                user_prompt,
                response
            ))

    # Refactoring examples
    refactor_system_prompt = "You are a senior software engineer. Review code, identify issues, and provide clean, maintainable refactored versions."

    refactor_prompts = [
        "Refactor this code to be cleaner and more maintainable:\n```python\n{code}\n```",
        "Review and improve this code:\n```python\n{code}\n```",
        "This code works but is messy. Please refactor it:\n```python\n{code}\n```",
    ]

    for refactor_example in REFACTORING_EXAMPLES:
        for prompt_template in refactor_prompts:
            user_prompt = prompt_template.format(code=refactor_example['before'])
            response = generate_refactoring_example(refactor_example)

            examples.append(create_training_example(
                refactor_system_prompt,
                user_prompt,
                response
            ))

    # Shuffle and limit
    random.shuffle(examples)
    examples = examples[:num_examples]

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print(f"Generated {len(examples)} complex task examples")
    print(f"Saved to: {output_file}")

    return len(examples)


if __name__ == "__main__":
    output_dir = Path(__file__).parent / "complex_tasks"
    output_dir.mkdir(exist_ok=True)

    # Generate training data
    train_file = output_dir / "train.jsonl"
    num_train = generate_complex_task_training_data(train_file, num_examples=300)

    # Generate eval data
    eval_file = output_dir / "eval.jsonl"
    num_eval = generate_complex_task_training_data(eval_file, num_examples=30)

    print(f"\nTotal: {num_train} training + {num_eval} eval examples")
