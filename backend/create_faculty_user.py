"""Create a faculty user for testing"""
import asyncio
import uuid
from passlib.context import CryptContext
from sqlalchemy import select, update
from app.core.database import get_session_local
from app.models.user import User, UserRole
from app.models.lab_assistance import Lab

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_faculty():
    session_local = get_session_local()
    async with session_local() as db:
        # Check if faculty exists
        result = await db.execute(
            select(User).where(User.email == "faculty@test.com")
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update password
            hashed = pwd_context.hash("faculty123")
            await db.execute(
                update(User).where(User.id == existing.id).values(
                    hashed_password=hashed,
                    role=UserRole.FACULTY,
                    is_active=True,
                    is_verified=True
                )
            )
            faculty_id = str(existing.id)
            print(f"Updated existing faculty user: {existing.email}")
        else:
            # Create new faculty
            hashed = pwd_context.hash("faculty123")
            faculty = User(
                id=str(uuid.uuid4()),
                email="faculty@test.com",
                full_name="Dr. Test Faculty",
                hashed_password=hashed,
                role=UserRole.FACULTY,
                is_active=True,
                is_verified=True
            )
            db.add(faculty)
            await db.flush()
            faculty_id = str(faculty.id)
            print(f"Created faculty user: faculty@test.com")

        # Update labs to be assigned to this faculty
        await db.execute(
            update(Lab).values(faculty_id=faculty_id)
        )
        print(f"Assigned all labs to faculty")

        await db.commit()
        print("\nLogin credentials:")
        print("Email: faculty@test.com")
        print("Password: faculty123")

if __name__ == "__main__":
    asyncio.run(create_faculty())
