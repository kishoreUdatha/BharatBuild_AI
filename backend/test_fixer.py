"""
Test: BharatBuild Fixer Agent
1. Take a generated file with a deliberate error
2. Let the Fixer Agent detect and fix it
3. Show before/after
"""
import sys, os, asyncio
os.chdir('D:/Smartgrow Projects/BharatBuild_AI/backend')
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('D:/Smartgrow Projects/BharatBuild_AI/backend/.env', override=True)

async def main():
    print("=" * 60)
    print("  BharatBuild AI - Fixer Agent Test")
    print("=" * 60)

    from app.utils.claude_client import claude_client

    # =====================================================
    # Broken code (deliberate errors)
    # =====================================================
    broken_code = '''from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.todo import TodoCreate, TodoUpdate, TodoResponse
from services.todo_service import todo_service

router = APIRouter(prefix="/api/todos", tags=["todos"])

@router.get("", response_model=list[TodoResponse])
def get_todos(db: Session = Depends(get_db)):
    # BUG 1: Calling wrong method name (get_all_todos doesn't exist)
    return todo_service.get_all_todos(db)

@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(data: TodoCreate, db: Session = Depends(get_db)):
    # BUG 2: Missing 'db' argument
    return todo_service.create(data)

@router.get("/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int, db: Session = Depends(get_db)):
    todo = todo_service.get_by_id(db, todo_id)
    if todo is None:
        # BUG 3: Wrong status code variable name
        raise HTTPException(status_code=status.NOT_FOUND, detail="Not found")
    return todo

@router.delete("/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    # BUG 4: Wrong method name
    todo_service.remove(db, todo_id)
    return {"message": "Deleted"}
'''

    # The correct service file (for context)
    service_code = '''from sqlalchemy.orm import Session
from models.todo import Todo
from schemas.todo import TodoCreate, TodoUpdate, TodoResponse

class TodoService:
    def get_all(self, db: Session) -> list[Todo]:
        return db.query(Todo).all()

    def get_by_id(self, db: Session, todo_id: int):
        return db.query(Todo).filter(Todo.id == todo_id).first()

    def create(self, db: Session, data: TodoCreate) -> Todo:
        todo = Todo(**data.model_dump())
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return todo

    def delete(self, db: Session, todo_id: int) -> bool:
        todo = self.get_by_id(db, todo_id)
        if todo:
            db.delete(todo)
            db.commit()
            return True
        return False

todo_service = TodoService()
'''

    print("\n[1/3] Broken code with 4 deliberate bugs:")
    print("-" * 40)
    print("  BUG 1: todo_service.get_all_todos() - method doesn't exist (should be get_all)")
    print("  BUG 2: todo_service.create(data) - missing 'db' argument")
    print("  BUG 3: status.NOT_FOUND - doesn't exist (should be HTTP_404_NOT_FOUND)")
    print("  BUG 4: todo_service.remove() - method doesn't exist (should be delete)")

    # =====================================================
    # Ask Fixer Agent to fix it
    # =====================================================
    print("\n[2/3] Sending to Fixer Agent...")

    error_message = """Build errors in backend/api/todos.py:
1. AttributeError: 'TodoService' object has no attribute 'get_all_todos'. Available methods: get_all, get_by_id, create, delete
2. TypeError: TodoService.create() missing 1 required positional argument: 'db'
3. AttributeError: module 'starlette.status' has no attribute 'NOT_FOUND'. Use HTTP_404_NOT_FOUND
4. AttributeError: 'TodoService' object has no attribute 'remove'. Did you mean: 'delete'?"""

    fix_prompt = f"""Fix ALL errors in this file.

ERROR MESSAGE:
{error_message}

BROKEN FILE (backend/api/todos.py):
```python
{broken_code}
```

REFERENCE - The actual service (backend/services/todo_service.py):
```python
{service_code}
```

Output the COMPLETE fixed file inside <file path="backend/api/todos.py"> tags.
Fix ALL 4 bugs. Use EXACT method names from the service file."""

    response = await claude_client.generate(
        prompt=fix_prompt,
        system_prompt="You are a code fixer. Fix all errors. Output complete fixed file in <file path=\"...\">code</file> format. No explanations.",
        model="sonnet",
        max_tokens=2000,
        temperature=0.1
    )

    content = response["content"]

    # Extract fixed code
    import re
    match = re.search(r'<file path="[^"]*">(.*?)</file>', content, re.DOTALL)
    fixed_code = match.group(1).strip() if match else content.strip()

    # =====================================================
    # Show results
    # =====================================================
    print(f"  Tokens used: {response['total_tokens']}")

    print(f"\n[3/3] Fixed code:")
    print("=" * 60)
    print(fixed_code)
    print("=" * 60)

    # Verify fixes
    print("\n  VERIFICATION:")
    checks = [
        ("get_all_todos fixed to get_all", "get_all_todos" not in fixed_code and "get_all" in fixed_code),
        ("create(db, data) has db argument", "create(db" in fixed_code or "create(db," in fixed_code),
        ("HTTP_404_NOT_FOUND used", "HTTP_404_NOT_FOUND" in fixed_code),
        ("remove fixed to delete", "remove" not in fixed_code and ".delete(" in fixed_code),
    ]

    all_pass = True
    for check_name, passed in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"    [{status}] {check_name}")

    print(f"\n  Result: {'ALL BUGS FIXED!' if all_pass else 'Some bugs remain'}")

asyncio.run(main())
