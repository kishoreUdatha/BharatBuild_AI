"""
Test script for Project Retrieval Service
Tests the complete Bolt.new-style project reconstruction flow
"""

import asyncio
import sys
from uuid import uuid4
from datetime import datetime

# Add backend to path
sys.path.insert(0, '.')

async def test_retrieval_service():
    """Test the complete retrieval flow"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, text

    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.project import Project, ProjectStatus, ProjectMode
    from app.models.project_file import ProjectFile
    from app.models.project_tree import ProjectFileTree, ProjectPlan, AgentState
    from app.models.project_message import ProjectMessage
    from app.services.project_retrieval_service import ProjectRetrievalService

    async with AsyncSessionLocal() as db:
        print("\n" + "="*60)
        print("PROJECT RETRIEVAL SERVICE TEST")
        print("="*60)

        # Step 0: Create a test user
        print("\n0. Creating test user...")
        user_id = str(uuid4())
        user = User(
            id=user_id,
            email=f"test-{user_id[:8]}@example.com",
            hashed_password="test_password_hash",
            full_name="Test User",
            role=UserRole.DEVELOPER,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        await db.commit()
        print(f"   [OK] User created: {user_id}")

        # Step 1: Create a test project
        print("\n1. Creating test project...")
        project_id = str(uuid4())

        project = Project(
            id=project_id,
            title="Test Todo App",
            description="A modern todo app for testing retrieval",
            user_id=user_id,
            status=ProjectStatus.COMPLETED,
            mode=ProjectMode.DEVELOPER,
            tech_stack=["React", "TypeScript", "Tailwind"],
            framework="vite",
            created_at=datetime.utcnow()
        )
        db.add(project)
        await db.commit()
        print(f"   [OK] Project created: {project_id}")

        # Step 2: Add project files
        print("\n2. Adding project files...")
        files = [
            ProjectFile(
                id=str(uuid4()),
                project_id=project_id,
                path="src/App.tsx",
                name="App.tsx",
                content_inline="import React from 'react';\n\nexport default function App() {\n  return <div>Hello World</div>;\n}",
                language="typescript",
                size_bytes=100,
                is_inline=True,
                created_at=datetime.utcnow()
            ),
            ProjectFile(
                id=str(uuid4()),
                project_id=project_id,
                path="src/components/TodoList.tsx",
                name="TodoList.tsx",
                content_inline="export const TodoList = () => <ul>Todo items</ul>;",
                language="typescript",
                size_bytes=50,
                is_inline=True,
                created_at=datetime.utcnow()
            ),
            ProjectFile(
                id=str(uuid4()),
                project_id=project_id,
                path="package.json",
                name="package.json",
                content_inline='{"name": "test-app", "version": "1.0.0", "dependencies": {"react": "^18.0.0"}}',
                language="json",
                size_bytes=80,
                is_inline=True,
                created_at=datetime.utcnow()
            )
        ]
        for f in files:
            db.add(f)
        await db.commit()
        print(f"   [OK] Added {len(files)} files")

        # Step 3: Add file tree
        print("\n3. Adding file tree...")
        tree = ProjectFileTree(
            id=str(uuid4()),
            project_id=project_id,
            tree_json={
                "src": {
                    "_type": "folder",
                    "App.tsx": {"_type": "file", "size": 100, "language": "typescript"},
                    "components": {
                        "_type": "folder",
                        "TodoList.tsx": {"_type": "file", "size": 50, "language": "typescript"}
                    }
                },
                "package.json": {"_type": "file", "size": 80, "language": "json"}
            },
            files_index=[
                {"path": "src/App.tsx", "size": 100, "language": "typescript"},
                {"path": "src/components/TodoList.tsx", "size": 50, "language": "typescript"},
                {"path": "package.json", "size": 80, "language": "json"}
            ],
            total_files="3",
            total_folders="2",
            total_size_bytes="230",
            created_at=datetime.utcnow()
        )
        db.add(tree)
        await db.commit()
        print("   [OK] File tree added")

        # Step 4: Add project plan
        print("\n4. Adding project plan...")
        plan = ProjectPlan(
            id=str(uuid4()),
            project_id=project_id,
            plan_json={
                "project_name": "Test Todo App",
                "description": "A modern todo application",
                "tech_stack": ["React", "TypeScript", "Tailwind"],
                "features": [
                    {"name": "Add todo", "status": "completed"},
                    {"name": "Delete todo", "status": "completed"},
                    {"name": "Mark complete", "status": "completed"}
                ],
                "files_to_generate": [
                    "src/App.tsx",
                    "src/components/TodoList.tsx",
                    "package.json"
                ]
            },
            version="1.0",
            status="completed",
            created_at=datetime.utcnow()
        )
        db.add(plan)
        await db.commit()
        print("   [OK] Project plan added")

        # Step 5: Add conversation messages
        print("\n5. Adding conversation history...")
        messages = [
            ProjectMessage(
                id=str(uuid4()),
                project_id=project_id,
                role="user",
                content="Create a todo app with React and TypeScript",
                tokens_used=15,
                created_at=datetime.utcnow()
            ),
            ProjectMessage(
                id=str(uuid4()),
                project_id=project_id,
                role="assistant",
                agent_type="planner",
                content="I'll create a todo app with the following features...",
                tokens_used=100,
                created_at=datetime.utcnow()
            ),
            ProjectMessage(
                id=str(uuid4()),
                project_id=project_id,
                role="assistant",
                agent_type="writer",
                content="Writing src/App.tsx...",
                tokens_used=200,
                created_at=datetime.utcnow()
            )
        ]
        for msg in messages:
            db.add(msg)
        await db.commit()
        print(f"   [OK] Added {len(messages)} messages")

        # Step 6: Add agent states
        print("\n6. Adding agent states...")
        agent_states = [
            AgentState(
                id=str(uuid4()),
                project_id=project_id,
                agent_type="planner",
                state_json={"phase": "completed", "files_planned": 3},
                status="completed",
                progress="100",
                created_at=datetime.utcnow()
            ),
            AgentState(
                id=str(uuid4()),
                project_id=project_id,
                agent_type="writer",
                state_json={"files_written": ["App.tsx", "TodoList.tsx", "package.json"]},
                status="completed",
                progress="100",
                created_at=datetime.utcnow()
            )
        ]
        for state in agent_states:
            db.add(state)
        await db.commit()
        print(f"   [OK] Added {len(agent_states)} agent states")

        # Step 7: Test retrieval service
        print("\n" + "="*60)
        print("TESTING RETRIEVAL SERVICE")
        print("="*60)

        service = ProjectRetrievalService(db)

        from uuid import UUID
        result = await service.retrieve_project(UUID(project_id))

        if result:
            print("\n[OK] Project retrieved successfully!")
            print(f"\n   Metadata:")
            print(f"     - Title: {result.metadata.title}")
            print(f"     - Status: {result.metadata.status}")
            print(f"     - Tech Stack: {result.metadata.tech_stack}")
            print(f"     - Framework: {result.metadata.framework}")

            print(f"\n   File Tree:")
            if result.file_tree:
                print(f"     - Total Files: {result.file_tree.total_files}")
                print(f"     - Total Folders: {result.file_tree.total_folders}")
                print(f"     - Total Size: {result.file_tree.total_size_bytes} bytes")
            else:
                print("     - (no file tree)")

            print(f"\n   Plan:")
            if result.plan:
                print(f"     - Version: {result.plan.version}")
                print(f"     - Status: {result.plan.status}")
                print(f"     - Features: {len(result.plan.plan_json.get('features', []))}")
            else:
                print("     - (no plan)")

            print(f"\n   Conversation:")
            print(f"     - Messages: {len(result.conversation.messages)}")
            print(f"     - Total Tokens: {result.conversation.total_tokens}")

            print(f"\n   Agent States:")
            print(f"     - Agents tracked: {list(result.agent_states.states.keys())}")

            print(f"\n   Retrieval Time: {result.retrieval_time_ms:.2f}ms")
        else:
            print("\n[FAIL] Failed to retrieve project!")

        # Step 8: Test lazy file loading
        print("\n" + "="*60)
        print("TESTING LAZY FILE LOADING")
        print("="*60)

        file_content = await service.get_file_content(UUID(project_id), "src/App.tsx")
        if file_content:
            print("\n[OK] File content loaded successfully!")
            print(f"   Path: {file_content['path']}")
            print(f"   Language: {file_content['language']}")
            print(f"   Size: {file_content['size']} bytes")
            print(f"   Content preview: {file_content['content'][:50]}...")
        else:
            print("\n[FAIL] Failed to load file content!")

        # Step 9: Test batch file loading
        print("\n" + "="*60)
        print("TESTING BATCH FILE LOADING")
        print("="*60)

        batch_files = await service.get_files_batch(
            UUID(project_id),
            ["src/App.tsx", "src/components/TodoList.tsx", "package.json"]
        )
        print(f"\n[OK] Batch loaded {len(batch_files)} files")
        for f in batch_files:
            print(f"   - {f['path']} ({f['size']} bytes)")

        # Cleanup
        print("\n" + "="*60)
        print("CLEANUP")
        print("="*60)

        # Delete test data (order matters due to foreign keys)
        await db.execute(text(f"DELETE FROM agent_states WHERE project_id = '{project_id}'"))
        await db.execute(text(f"DELETE FROM project_plans WHERE project_id = '{project_id}'"))
        await db.execute(text(f"DELETE FROM project_file_trees WHERE project_id = '{project_id}'"))
        await db.execute(text(f"DELETE FROM project_messages WHERE project_id = '{project_id}'"))
        await db.execute(text(f"DELETE FROM project_files WHERE project_id = '{project_id}'"))
        await db.execute(text(f"DELETE FROM projects WHERE id = '{project_id}'"))
        await db.execute(text(f"DELETE FROM users WHERE id = '{user_id}'"))
        await db.commit()
        print("[OK] Test data cleaned up")

        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_retrieval_service())
