"""
Seed Demo Users for Login

Creates the demo users that match the frontend login page credentials:
- student@college.edu / demo123 → Student role → redirects to /lab
- faculty@college.edu / demo123 → Faculty role → redirects to /faculty
- admin@bharatbuild.ai / demo123 → Admin role → redirects to /admin
- user@example.com / demo123 → Developer (Builder) role → redirects to /build

Run with: python seed_demo_users.py
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole


# Demo users matching frontend login page
DEMO_USERS = [
    {
        "email": "student@college.edu",
        "full_name": "Demo Student",
        "username": "demo_student",
        "role": UserRole.STUDENT,
        "password": "demo123",
        "organization": "Demo College",
        "roll_number": "21CS001",
        "college_name": "BharatBuild Demo College",
        "university_name": "Demo University",
        "department": "Computer Science and Engineering",
        "course": "B.Tech",
        "year_semester": "3rd Year / 5th Semester",
        "batch": "2021-2025",
    },
    {
        "email": "faculty@college.edu",
        "full_name": "Demo Faculty",
        "username": "demo_faculty",
        "role": UserRole.FACULTY,
        "password": "demo123",
        "organization": "Demo College",
    },
    {
        "email": "admin@bharatbuild.ai",
        "full_name": "Demo Admin",
        "username": "demo_admin",
        "role": UserRole.ADMIN,
        "password": "demo123",
        "organization": "BharatBuild AI",
        "is_superuser": True,
    },
    {
        "email": "user@example.com",
        "full_name": "Demo Builder",
        "username": "demo_builder",
        "role": UserRole.DEVELOPER,  # Builder maps to Developer role
        "password": "demo123",
        "organization": "Demo Company",
    },
]


async def seed_demo_users():
    """Create or update demo users"""
    print("=" * 50)
    print("Seeding Demo Users...")
    print("=" * 50)

    # Initialize database
    await init_db()

    async with AsyncSessionLocal() as db:
        created_count = 0
        updated_count = 0

        for user_data in DEMO_USERS:
            email = user_data["email"]
            password = user_data.pop("password")

            # Check if user exists
            result = await db.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                # Update existing user
                existing_user.hashed_password = get_password_hash(password)
                existing_user.full_name = user_data["full_name"]
                existing_user.username = user_data["username"]
                existing_user.role = user_data["role"]
                existing_user.is_active = True
                existing_user.is_verified = True
                existing_user.organization = user_data.get("organization")

                # Update student fields if applicable
                if user_data["role"] == UserRole.STUDENT:
                    existing_user.roll_number = user_data.get("roll_number")
                    existing_user.college_name = user_data.get("college_name")
                    existing_user.university_name = user_data.get("university_name")
                    existing_user.department = user_data.get("department")
                    existing_user.course = user_data.get("course")
                    existing_user.year_semester = user_data.get("year_semester")
                    existing_user.batch = user_data.get("batch")

                if user_data.get("is_superuser"):
                    existing_user.is_superuser = True

                updated_count += 1
                print(f"  Updated: {email} ({user_data['role'].value})")
            else:
                # Create new user
                user = User(
                    email=email,
                    hashed_password=get_password_hash(password),
                    full_name=user_data["full_name"],
                    username=user_data["username"],
                    role=user_data["role"],
                    is_active=True,
                    is_verified=True,
                    organization=user_data.get("organization"),
                    roll_number=user_data.get("roll_number"),
                    college_name=user_data.get("college_name"),
                    university_name=user_data.get("university_name"),
                    department=user_data.get("department"),
                    course=user_data.get("course"),
                    year_semester=user_data.get("year_semester"),
                    batch=user_data.get("batch"),
                    is_superuser=user_data.get("is_superuser", False),
                )
                db.add(user)
                created_count += 1
                print(f"  Created: {email} ({user_data['role'].value})")

        await db.commit()

        print("=" * 50)
        print(f"Demo Users Seeded Successfully!")
        print(f"  Created: {created_count}")
        print(f"  Updated: {updated_count}")
        print("=" * 50)
        print("\nDemo Login Credentials:")
        print("-" * 50)
        print("| Role     | Email                  | Password |")
        print("-" * 50)
        print("| Student  | student@college.edu    | demo123  |")
        print("| Faculty  | faculty@college.edu    | demo123  |")
        print("| Admin    | admin@bharatbuild.ai   | demo123  |")
        print("| Builder  | user@example.com       | demo123  |")
        print("-" * 50)


async def list_demo_users():
    """List all demo users in the database"""
    await init_db()

    async with AsyncSessionLocal() as db:
        demo_emails = [u["email"] for u in DEMO_USERS]

        result = await db.execute(
            select(User).where(User.email.in_(demo_emails))
        )
        users = result.scalars().all()

        print("\nDemo Users in Database:")
        print("-" * 70)
        print(f"{'Email':<30} {'Role':<12} {'Active':<8} {'Verified':<10}")
        print("-" * 70)

        for user in users:
            print(f"{user.email:<30} {user.role.value:<12} {str(user.is_active):<8} {str(user.is_verified):<10}")

        if not users:
            print("No demo users found. Run 'python seed_demo_users.py' to create them.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        asyncio.run(list_demo_users())
    else:
        asyncio.run(seed_demo_users())
