"""
Seed script for Lab Management data
Creates labs, topics, MCQs, and coding problems for testing
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.database import get_session_local
from app.models.user import User, UserRole
from app.models.lab_assistance import (
    Lab, LabTopic, LabMCQ, LabCodingProblem, LabEnrollment,
    Branch, Semester, DifficultyLevel, ProgrammingLanguage
)


async def seed_lab_data():
    session_local = get_session_local()
    async with session_local() as db:
        # Get or create a faculty user
        result = await db.execute(
            select(User).where(User.role == UserRole.FACULTY).limit(1)
        )
        faculty = result.scalar_one_or_none()

        if not faculty:
            # Create faculty user
            faculty = User(
                id=str(uuid.uuid4()),
                email="faculty@bharatbuild.com",
                full_name="Dr. Faculty User",
                role=UserRole.FACULTY,
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G5Z5Z5Z5Z5Z5Z5",  # dummy hash
                is_active=True,
                is_verified=True
            )
            db.add(faculty)
            await db.flush()
            print(f"Created faculty user: {faculty.email}")

        faculty_id = str(faculty.id)

        # Check if labs already exist
        result = await db.execute(select(Lab).limit(1))
        if result.scalar_one_or_none():
            print("Labs already exist. Skipping seed.")
            return

        # Create Labs
        labs_data = [
            {
                "name": "Data Structures Lab",
                "code": "CS301L",
                "description": "Practical implementation of data structures including arrays, linked lists, trees, and graphs",
                "branch": Branch.CSE,
                "semester": Semester.SEM_3,
                "faculty_id": faculty_id
            },
            {
                "name": "Database Management Lab",
                "code": "CS302L",
                "description": "SQL queries, normalization, and database design practicals",
                "branch": Branch.CSE,
                "semester": Semester.SEM_3,
                "faculty_id": faculty_id
            },
            {
                "name": "Operating Systems Lab",
                "code": "CS401L",
                "description": "Process scheduling, memory management, and file systems",
                "branch": Branch.CSE,
                "semester": Semester.SEM_4,
                "faculty_id": faculty_id
            },
            {
                "name": "Computer Networks Lab",
                "code": "CS402L",
                "description": "Network protocols, socket programming, and packet analysis",
                "branch": Branch.CSE,
                "semester": Semester.SEM_4,
                "faculty_id": faculty_id
            },
            {
                "name": "Machine Learning Lab",
                "code": "CS501L",
                "description": "Implementation of ML algorithms and model training",
                "branch": Branch.CSE,
                "semester": Semester.SEM_5,
                "faculty_id": faculty_id
            }
        ]

        created_labs = []
        for lab_data in labs_data:
            lab = Lab(
                id=str(uuid.uuid4()),
                **lab_data,
                is_active=True
            )
            db.add(lab)
            created_labs.append(lab)
            print(f"Created lab: {lab.name}")

        await db.flush()

        # Create Topics for Data Structures Lab
        ds_lab = created_labs[0]
        ds_topics = [
            {
                "title": "Implement Stack using Arrays",
                "description": "Implement a stack data structure using arrays with push, pop, peek operations",
                "week_number": 1,
                "concept_content": "A stack is a LIFO data structure...",
                "difficulty": "easy"
            },
            {
                "title": "Implement Queue using Linked List",
                "description": "Implement a queue using linked list with enqueue and dequeue operations",
                "week_number": 2,
                "concept_content": "A queue is a FIFO data structure...",
                "difficulty": "easy"
            },
            {
                "title": "Binary Search Tree Operations",
                "description": "Implement BST with insert, delete, search, and traversal operations",
                "week_number": 3,
                "concept_content": "A BST is a tree where left child < parent < right child...",
                "difficulty": "medium"
            },
            {
                "title": "Graph Traversal - BFS and DFS",
                "description": "Implement breadth-first and depth-first search algorithms",
                "week_number": 4,
                "concept_content": "Graph traversal explores all vertices...",
                "difficulty": "medium"
            },
            {
                "title": "Shortest Path - Dijkstra's Algorithm",
                "description": "Find shortest path in weighted graph using Dijkstra's algorithm",
                "week_number": 5,
                "concept_content": "Dijkstra's algorithm finds shortest path from source to all vertices...",
                "difficulty": "hard"
            },
            {
                "title": "Dynamic Programming - Knapsack Problem",
                "description": "Solve 0/1 Knapsack problem using dynamic programming",
                "week_number": 6,
                "concept_content": "DP breaks problems into overlapping subproblems...",
                "difficulty": "hard"
            }
        ]

        created_topics = []
        for i, topic_data in enumerate(ds_topics):
            difficulty = topic_data.pop("difficulty")
            topic = LabTopic(
                id=str(uuid.uuid4()),
                lab_id=ds_lab.id,
                order_index=i + 1,
                **topic_data,
                is_active=True
            )
            db.add(topic)
            created_topics.append((topic, difficulty))
            print(f"Created topic: {topic.title}")

        await db.flush()

        # Create MCQs for each topic
        mcq_templates = [
            ("What is the time complexity of push operation in stack?", ["O(1)", "O(n)", "O(log n)", "O(n²)"], 0),
            ("Which data structure uses LIFO principle?", ["Queue", "Stack", "Array", "Tree"], 1),
            ("What happens when we try to pop from an empty stack?", ["Returns null", "Underflow", "Overflow", "Nothing"], 1),
        ]

        for topic, difficulty in created_topics:
            for q_text, options, correct in mcq_templates:
                mcq = LabMCQ(
                    id=str(uuid.uuid4()),
                    topic_id=topic.id,
                    question_text=f"[{topic.title}] {q_text}",
                    options=options,
                    correct_option=correct,
                    explanation="This is the correct answer because...",
                    difficulty=DifficultyLevel.EASY if difficulty == "easy" else DifficultyLevel.MEDIUM if difficulty == "medium" else DifficultyLevel.HARD,
                    marks=5,
                    time_limit_seconds=60,
                    is_active=True
                )
                db.add(mcq)

        print("Created MCQs for all topics")

        # Create Coding Problems for each topic
        for topic, difficulty in created_topics:
            problem = LabCodingProblem(
                id=str(uuid.uuid4()),
                topic_id=topic.id,
                title=f"Implement {topic.title}",
                description=f"Write a program to {topic.description.lower()}",
                difficulty=DifficultyLevel.EASY if difficulty == "easy" else DifficultyLevel.MEDIUM if difficulty == "medium" else DifficultyLevel.HARD,
                max_score=100,
                supported_languages=[ProgrammingLanguage.PYTHON, ProgrammingLanguage.CPP, ProgrammingLanguage.JAVA],
                starter_code={
                    "python": "# Write your solution here\n\ndef solution():\n    pass",
                    "cpp": "// Write your solution here\n#include <iostream>\nusing namespace std;\n\nint main() {\n    return 0;\n}",
                    "java": "// Write your solution here\npublic class Solution {\n    public static void main(String[] args) {\n    }\n}"
                },
                test_cases=[
                    {"input": "5", "expected_output": "25", "is_hidden": False},
                    {"input": "10", "expected_output": "100", "is_hidden": True}
                ],
                time_limit_ms=2000,
                memory_limit_mb=256,
                is_active=True
            )
            db.add(problem)

        print("Created coding problems for all topics")

        # Get some students to enroll
        result = await db.execute(
            select(User).where(User.role == UserRole.STUDENT).limit(10)
        )
        students = result.scalars().all()

        # Create enrollments for students
        for student in students:
            enrollment = LabEnrollment(
                id=str(uuid.uuid4()),
                lab_id=ds_lab.id,
                user_id=str(student.id),
                section="A",
                overall_progress=50.0,
                mcq_score=75.0,
                coding_score=65.0,
                total_score=70.0,
                topics_completed=3,
                mcqs_attempted=9,
                mcqs_correct=7,
                problems_solved=3
            )
            db.add(enrollment)

        print(f"Created enrollments for {len(students)} students")

        await db.commit()
        print("\n✅ Lab data seeded successfully!")
        print(f"   - {len(created_labs)} Labs")
        print(f"   - {len(created_topics)} Topics")
        print(f"   - {len(created_topics) * 3} MCQs")
        print(f"   - {len(created_topics)} Coding Problems")


if __name__ == "__main__":
    asyncio.run(seed_lab_data())
