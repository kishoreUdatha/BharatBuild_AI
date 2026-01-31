"""
Student Assignment Portal API

Endpoints for students to:
- View assigned assignments
- Submit code solutions
- View auto-grading results
- Track submission history
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_current_active_user
from app.models.user import User, UserRole
from app.services.judge0_executor import Judge0Executor

router = APIRouter(tags=["Student Assignments"])

# In-memory storage (shared with faculty.py - in production use database)
# Import from faculty module
from app.api.v1.endpoints.faculty import ASSIGNMENTS_DB, SUBMISSIONS_DB, generate_id


# ==================== Request/Response Models ====================

class CodeSubmission(BaseModel):
    code: str
    language: str = "python"


class SubmissionResult(BaseModel):
    id: str
    assignment_id: str
    status: str
    score: Optional[float] = None
    tests_passed: int = 0
    tests_total: int = 0
    execution_time_ms: Optional[float] = None
    memory_used_kb: Optional[float] = None
    test_results: Optional[List[Dict]] = None
    error_message: Optional[str] = None
    submitted_at: str
    graded_at: Optional[str] = None


# ==================== Helper Functions ====================

def get_student_batch(user: User) -> Optional[str]:
    """Get student's batch/class ID"""
    # In production, this would query the StudentSection table
    # For now, return a default batch
    return user.batch or "CSE-3A"


async def run_test_cases(code: str, language: str, test_cases: List[Dict]) -> Dict:
    """Run code against test cases using Judge0"""
    try:
        executor = Judge0Executor()
        results = []
        passed = 0
        total = len(test_cases)
        total_time = 0
        max_memory = 0

        for i, tc in enumerate(test_cases):
            try:
                result = await executor.execute(
                    code=code,
                    language=language,
                    stdin=tc.get("input", ""),
                    expected_output=tc.get("expected_output", "")
                )

                actual_output = result.get("stdout", "").strip()
                expected = tc.get("expected_output", "").strip()
                is_passed = actual_output == expected

                if is_passed:
                    passed += 1

                total_time += result.get("time", 0) or 0
                max_memory = max(max_memory, result.get("memory", 0) or 0)

                results.append({
                    "test_case": i + 1,
                    "passed": is_passed,
                    "input": tc.get("input", "") if not tc.get("is_hidden") else "[Hidden]",
                    "expected": tc.get("expected_output", "") if not tc.get("is_hidden") else "[Hidden]",
                    "actual": actual_output if not tc.get("is_hidden") else "[Hidden]",
                    "is_hidden": tc.get("is_hidden", False),
                    "execution_time": result.get("time"),
                    "error": result.get("stderr")
                })
            except Exception as e:
                results.append({
                    "test_case": i + 1,
                    "passed": False,
                    "error": str(e),
                    "is_hidden": tc.get("is_hidden", False)
                })

        # Calculate score based on test case weights
        total_weight = sum(tc.get("weight", 1) for tc in test_cases)
        earned_weight = sum(
            tc.get("weight", 1)
            for tc, r in zip(test_cases, results)
            if r.get("passed")
        )
        score = (earned_weight / total_weight * 100) if total_weight > 0 else 0

        return {
            "passed": passed,
            "total": total,
            "score": round(score, 2),
            "execution_time_ms": total_time * 1000,
            "memory_used_kb": max_memory,
            "test_results": results,
            "status": "passed" if passed == total else "partial" if passed > 0 else "failed"
        }
    except Exception as e:
        return {
            "passed": 0,
            "total": len(test_cases),
            "score": 0,
            "error_message": str(e),
            "status": "error",
            "test_results": []
        }


# ==================== Student Assignment Endpoints ====================

@router.get("/assignments")
async def get_student_assignments(
    status: Optional[str] = None,  # active, completed, overdue
    subject: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all assignments for the student's batch"""
    student_batch = get_student_batch(current_user)

    # Get assignments for student's batch
    assignments = [
        a for a in ASSIGNMENTS_DB.values()
        if a.get("batch_id") == student_batch or a.get("batch_id") == "all"
    ]

    # Add mock assignments if none exist
    if not assignments:
        mock_assignments = [
            {
                "id": "demo-1",
                "title": "Binary Search Implementation",
                "subject": "Data Structures",
                "description": "Implement binary search algorithm that finds the position of a target value in a sorted array. Return -1 if target is not found.",
                "due_date": (datetime.utcnow().replace(day=28)).isoformat(),
                "batch_id": student_batch,
                "problem_type": "coding",
                "difficulty": "easy",
                "language": "python",
                "max_score": 100,
                "test_cases": [
                    {"input": "1 2 3 4 5\n3", "expected_output": "2", "is_hidden": False, "weight": 1},
                    {"input": "1 2 3 4 5\n6", "expected_output": "-1", "is_hidden": False, "weight": 1},
                    {"input": "10 20 30 40 50\n10", "expected_output": "0", "is_hidden": True, "weight": 2},
                ],
                "starter_code": "def binary_search(arr, target):\n    # Your code here\n    pass\n\n# Read input\narr = list(map(int, input().split()))\ntarget = int(input())\nprint(binary_search(arr, target))",
                "status": "active",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": "demo-2",
                "title": "Linked List Reversal",
                "subject": "Data Structures",
                "description": "Write a function to reverse a singly linked list. Input is space-separated integers representing the linked list.",
                "due_date": (datetime.utcnow().replace(day=25)).isoformat(),
                "batch_id": student_batch,
                "problem_type": "coding",
                "difficulty": "medium",
                "language": "python",
                "max_score": 100,
                "test_cases": [
                    {"input": "1 2 3 4 5", "expected_output": "5 4 3 2 1", "is_hidden": False, "weight": 1},
                    {"input": "1", "expected_output": "1", "is_hidden": False, "weight": 1},
                    {"input": "1 2", "expected_output": "2 1", "is_hidden": True, "weight": 2},
                ],
                "starter_code": "class Node:\n    def __init__(self, val):\n        self.val = val\n        self.next = None\n\ndef reverse_list(head):\n    # Your code here\n    pass\n\n# Read input and create linked list\nvalues = list(map(int, input().split()))\n# Create and reverse list, then print",
                "status": "active",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": "demo-3",
                "title": "SQL Query - Employee Salary",
                "subject": "DBMS",
                "description": "Write a SQL query to find employees with salary greater than the average salary of their department.",
                "due_date": (datetime.utcnow().replace(day=20)).isoformat(),
                "batch_id": student_batch,
                "problem_type": "sql",
                "difficulty": "medium",
                "language": "sql",
                "max_score": 50,
                "test_cases": [],
                "starter_code": "-- Write your SQL query here\nSELECT ",
                "status": "active",
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        assignments = mock_assignments

    now = datetime.utcnow()

    # Enrich with submission status
    enriched = []
    for assignment in assignments:
        # Get student's submissions for this assignment
        submissions = [
            s for s in SUBMISSIONS_DB.values()
            if s.get("assignment_id") == assignment["id"]
            and s.get("student_id") == str(current_user.id)
        ]

        # Determine status
        due_date = datetime.fromisoformat(assignment["due_date"].replace("Z", ""))
        is_overdue = now > due_date

        best_submission = max(submissions, key=lambda s: s.get("score", 0)) if submissions else None

        assignment_status = "completed" if best_submission and best_submission.get("score", 0) >= 60 else \
                          "overdue" if is_overdue else "active"

        # Apply filter
        if status and assignment_status != status:
            continue
        if subject and assignment.get("subject", "").lower() != subject.lower():
            continue

        enriched.append({
            **assignment,
            "submission_status": assignment_status,
            "submissions_count": len(submissions),
            "best_score": best_submission.get("score") if best_submission else None,
            "last_submission": best_submission.get("submitted_at") if best_submission else None,
            "is_overdue": is_overdue,
            "time_remaining": str(due_date - now) if not is_overdue else None
        })

    # Sort by due date
    enriched.sort(key=lambda x: x["due_date"])

    return {
        "batch": student_batch,
        "total": len(enriched),
        "assignments": enriched
    }


@router.get("/assignments/{assignment_id}")
async def get_assignment_detail(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed assignment information for submission"""
    # Check in-memory storage
    assignment = ASSIGNMENTS_DB.get(assignment_id)

    # Check mock data
    if not assignment:
        # Return mock assignment for demo IDs
        mock_assignments = {
            "demo-1": {
                "id": "demo-1",
                "title": "Binary Search Implementation",
                "subject": "Data Structures",
                "description": """Implement binary search algorithm that finds the position of a target value in a sorted array.

**Requirements:**
- Return the index of the target if found
- Return -1 if target is not found
- The array is guaranteed to be sorted in ascending order

**Input Format:**
- First line: Space-separated integers (the sorted array)
- Second line: Target integer to find

**Output Format:**
- Single integer: index of target or -1

**Example:**
```
Input:
1 2 3 4 5
3

Output:
2
```""",
                "due_date": (datetime.utcnow().replace(day=28)).isoformat(),
                "problem_type": "coding",
                "difficulty": "easy",
                "language": "python",
                "max_score": 100,
                "test_cases": [
                    {"input": "1 2 3 4 5\n3", "expected_output": "2", "is_hidden": False, "weight": 1},
                    {"input": "1 2 3 4 5\n6", "expected_output": "-1", "is_hidden": False, "weight": 1},
                    {"input": "10 20 30 40 50\n10", "expected_output": "0", "is_hidden": True, "weight": 2},
                    {"input": "1 3 5 7 9 11 13\n7", "expected_output": "3", "is_hidden": True, "weight": 2},
                ],
                "starter_code": """def binary_search(arr, target):
    \"\"\"
    Find the index of target in sorted array arr.
    Return -1 if not found.
    \"\"\"
    # Your code here
    pass

# Read input
arr = list(map(int, input().split()))
target = int(input())
print(binary_search(arr, target))""",
                "allow_late_submission": True,
                "late_penalty_percent": 10,
                "status": "active"
            },
            "demo-2": {
                "id": "demo-2",
                "title": "Linked List Reversal",
                "subject": "Data Structures",
                "description": """Reverse a singly linked list.

**Input Format:**
- Space-separated integers representing linked list values

**Output Format:**
- Space-separated integers in reversed order

**Example:**
```
Input: 1 2 3 4 5
Output: 5 4 3 2 1
```""",
                "due_date": (datetime.utcnow().replace(day=25)).isoformat(),
                "problem_type": "coding",
                "difficulty": "medium",
                "language": "python",
                "max_score": 100,
                "test_cases": [
                    {"input": "1 2 3 4 5", "expected_output": "5 4 3 2 1", "is_hidden": False, "weight": 1},
                    {"input": "1", "expected_output": "1", "is_hidden": False, "weight": 1},
                    {"input": "1 2", "expected_output": "2 1", "is_hidden": True, "weight": 2},
                ],
                "starter_code": """# Reverse a linked list
values = list(map(int, input().split()))
# Reverse and print
print(' '.join(map(str, reversed(values))))""",
                "allow_late_submission": True,
                "late_penalty_percent": 10,
                "status": "active"
            },
            "demo-3": {
                "id": "demo-3",
                "title": "SQL Query - Employee Salary",
                "subject": "DBMS",
                "description": "Write a SQL query to find employees with salary greater than average.",
                "due_date": (datetime.utcnow().replace(day=20)).isoformat(),
                "problem_type": "sql",
                "difficulty": "medium",
                "language": "sql",
                "max_score": 50,
                "test_cases": [],
                "starter_code": "SELECT * FROM employees WHERE salary > (SELECT AVG(salary) FROM employees);",
                "status": "active"
            }
        }
        assignment = mock_assignments.get(assignment_id)

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Get student's submissions
    submissions = [
        s for s in SUBMISSIONS_DB.values()
        if s.get("assignment_id") == assignment_id
        and s.get("student_id") == str(current_user.id)
    ]

    # Sort by submission time
    submissions.sort(key=lambda s: s.get("submitted_at", ""), reverse=True)

    # Filter test cases - hide hidden ones for display
    visible_test_cases = [
        {
            "input": tc["input"],
            "expected_output": tc["expected_output"],
            "weight": tc.get("weight", 1)
        }
        for tc in assignment.get("test_cases", [])
        if not tc.get("is_hidden", False)
    ]

    hidden_count = len(assignment.get("test_cases", [])) - len(visible_test_cases)

    return {
        **assignment,
        "visible_test_cases": visible_test_cases,
        "hidden_test_cases_count": hidden_count,
        "total_test_cases": len(assignment.get("test_cases", [])),
        "my_submissions": submissions[:10],  # Last 10 submissions
        "best_score": max((s.get("score", 0) for s in submissions), default=None),
        "submission_count": len(submissions)
    }


@router.post("/assignments/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: str,
    submission: CodeSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit code for an assignment and get auto-grading results"""
    # Get assignment
    assignment = ASSIGNMENTS_DB.get(assignment_id)

    # Check mock assignments
    if not assignment:
        mock_test_cases = {
            "demo-1": [
                {"input": "1 2 3 4 5\n3", "expected_output": "2", "is_hidden": False, "weight": 1},
                {"input": "1 2 3 4 5\n6", "expected_output": "-1", "is_hidden": False, "weight": 1},
                {"input": "10 20 30 40 50\n10", "expected_output": "0", "is_hidden": True, "weight": 2},
                {"input": "1 3 5 7 9 11 13\n7", "expected_output": "3", "is_hidden": True, "weight": 2},
            ],
            "demo-2": [
                {"input": "1 2 3 4 5", "expected_output": "5 4 3 2 1", "is_hidden": False, "weight": 1},
                {"input": "1", "expected_output": "1", "is_hidden": False, "weight": 1},
                {"input": "1 2", "expected_output": "2 1", "is_hidden": True, "weight": 2},
            ]
        }

        if assignment_id in mock_test_cases:
            assignment = {
                "id": assignment_id,
                "test_cases": mock_test_cases[assignment_id],
                "max_score": 100,
                "allow_late_submission": True,
                "late_penalty_percent": 10,
                "due_date": (datetime.utcnow().replace(day=28)).isoformat()
            }

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check deadline
    due_date = datetime.fromisoformat(assignment["due_date"].replace("Z", ""))
    is_late = datetime.utcnow() > due_date

    if is_late and not assignment.get("allow_late_submission", True):
        raise HTTPException(status_code=400, detail="Submission deadline has passed")

    # Run test cases
    test_cases = assignment.get("test_cases", [])

    if test_cases:
        grading_result = await run_test_cases(
            code=submission.code,
            language=submission.language,
            test_cases=test_cases
        )
    else:
        # No test cases - manual grading required
        grading_result = {
            "passed": 0,
            "total": 0,
            "score": None,
            "status": "pending_review",
            "test_results": [],
            "message": "This assignment requires manual grading by faculty"
        }

    # Apply late penalty
    final_score = grading_result.get("score")
    if final_score is not None and is_late:
        penalty = assignment.get("late_penalty_percent", 10)
        final_score = max(0, final_score - penalty)
        grading_result["late_penalty_applied"] = penalty
        grading_result["original_score"] = grading_result["score"]
        grading_result["score"] = final_score

    # Create submission record
    submission_id = generate_id()
    submission_record = {
        "id": submission_id,
        "assignment_id": assignment_id,
        "student_id": str(current_user.id),
        "student_name": current_user.full_name or current_user.email,
        "code": submission.code,
        "language": submission.language,
        "status": grading_result.get("status", "pending"),
        "score": final_score,
        "tests_passed": grading_result.get("passed", 0),
        "tests_total": grading_result.get("total", 0),
        "test_results": grading_result.get("test_results", []),
        "execution_time_ms": grading_result.get("execution_time_ms"),
        "memory_used_kb": grading_result.get("memory_used_kb"),
        "error_message": grading_result.get("error_message"),
        "is_late": is_late,
        "submitted_at": datetime.utcnow().isoformat(),
        "graded_at": datetime.utcnow().isoformat() if test_cases else None
    }

    SUBMISSIONS_DB[submission_id] = submission_record

    # Filter hidden test results for response
    visible_results = [
        r for r in grading_result.get("test_results", [])
        if not r.get("is_hidden", False)
    ]
    hidden_passed = sum(
        1 for r in grading_result.get("test_results", [])
        if r.get("is_hidden", False) and r.get("passed", False)
    )
    hidden_total = sum(
        1 for r in grading_result.get("test_results", [])
        if r.get("is_hidden", False)
    )

    return {
        "submission_id": submission_id,
        "status": grading_result.get("status"),
        "score": final_score,
        "max_score": assignment.get("max_score", 100),
        "tests_passed": grading_result.get("passed", 0),
        "tests_total": grading_result.get("total", 0),
        "visible_test_results": visible_results,
        "hidden_tests": {
            "passed": hidden_passed,
            "total": hidden_total
        },
        "execution_time_ms": grading_result.get("execution_time_ms"),
        "memory_used_kb": grading_result.get("memory_used_kb"),
        "error_message": grading_result.get("error_message"),
        "is_late": is_late,
        "late_penalty": grading_result.get("late_penalty_applied"),
        "submitted_at": submission_record["submitted_at"],
        "message": "Submission successful!" if grading_result.get("status") == "passed" else
                  "Some tests failed. Try again!" if grading_result.get("status") in ["partial", "failed"] else
                  "Submitted for manual review"
    }


@router.get("/assignments/{assignment_id}/submissions")
async def get_my_submissions(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all submissions for an assignment by current student"""
    submissions = [
        s for s in SUBMISSIONS_DB.values()
        if s.get("assignment_id") == assignment_id
        and s.get("student_id") == str(current_user.id)
    ]

    # Sort by submission time (newest first)
    submissions.sort(key=lambda s: s.get("submitted_at", ""), reverse=True)

    # Calculate stats
    scores = [s.get("score") for s in submissions if s.get("score") is not None]

    return {
        "assignment_id": assignment_id,
        "total_submissions": len(submissions),
        "best_score": max(scores) if scores else None,
        "average_score": sum(scores) / len(scores) if scores else None,
        "submissions": submissions
    }


@router.get("/assignments/{assignment_id}/submissions/{submission_id}")
async def get_submission_detail(
    assignment_id: str,
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed submission with code and results"""
    submission = SUBMISSIONS_DB.get(submission_id)

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Verify ownership
    if submission.get("student_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this submission")

    # Filter hidden test results
    visible_results = [
        r for r in submission.get("test_results", [])
        if not r.get("is_hidden", False)
    ]

    return {
        **submission,
        "test_results": visible_results,
        "hidden_tests_passed": sum(
            1 for r in submission.get("test_results", [])
            if r.get("is_hidden") and r.get("passed")
        ),
        "hidden_tests_total": sum(
            1 for r in submission.get("test_results", [])
            if r.get("is_hidden")
        )
    }


@router.get("/dashboard")
async def get_student_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get student assignment dashboard summary"""
    student_batch = get_student_batch(current_user)

    # Get all assignments for student
    assignments = [
        a for a in ASSIGNMENTS_DB.values()
        if a.get("batch_id") == student_batch or a.get("batch_id") == "all"
    ]

    # Add demo assignments if empty
    if not assignments:
        assignments = [
            {"id": "demo-1", "due_date": datetime.utcnow().replace(day=28).isoformat()},
            {"id": "demo-2", "due_date": datetime.utcnow().replace(day=25).isoformat()},
            {"id": "demo-3", "due_date": datetime.utcnow().replace(day=20).isoformat()},
        ]

    # Get submissions
    my_submissions = [
        s for s in SUBMISSIONS_DB.values()
        if s.get("student_id") == str(current_user.id)
    ]

    # Calculate stats
    now = datetime.utcnow()
    completed = 0
    pending = 0
    overdue = 0

    for assignment in assignments:
        due_date = datetime.fromisoformat(assignment["due_date"].replace("Z", ""))
        submissions = [s for s in my_submissions if s.get("assignment_id") == assignment["id"]]
        best_score = max((s.get("score", 0) for s in submissions), default=0)

        if best_score >= 60:
            completed += 1
        elif now > due_date:
            overdue += 1
        else:
            pending += 1

    # Recent submissions
    recent = sorted(my_submissions, key=lambda s: s.get("submitted_at", ""), reverse=True)[:5]

    # Upcoming deadlines
    upcoming = sorted(
        [a for a in assignments if datetime.fromisoformat(a["due_date"].replace("Z", "")) > now],
        key=lambda a: a["due_date"]
    )[:5]

    return {
        "student": {
            "id": str(current_user.id),
            "name": current_user.full_name or current_user.email,
            "batch": student_batch
        },
        "stats": {
            "total_assignments": len(assignments),
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "total_submissions": len(my_submissions),
            "average_score": sum(s.get("score", 0) for s in my_submissions if s.get("score")) / len(my_submissions) if my_submissions else 0
        },
        "recent_submissions": recent,
        "upcoming_deadlines": upcoming
    }


@router.post("/assignments/{assignment_id}/run")
async def run_code(
    assignment_id: str,
    submission: CodeSubmission,
    test_input: str = Body("", embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Run code without submitting (for testing)"""
    try:
        executor = Judge0Executor()
        result = await executor.execute(
            code=submission.code,
            language=submission.language,
            stdin=test_input
        )

        return {
            "output": result.get("stdout", ""),
            "error": result.get("stderr", ""),
            "execution_time": result.get("time"),
            "memory": result.get("memory"),
            "status": "success" if not result.get("stderr") else "error"
        }
    except Exception as e:
        return {
            "output": "",
            "error": str(e),
            "status": "error"
        }
