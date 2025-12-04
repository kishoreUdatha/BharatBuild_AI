"""Check projects in database"""
import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    async with engine.connect() as conn:
        # Check users
        print("=== USERS ===")
        users = await conn.execute(text("SELECT id, email, username FROM users"))
        user_rows = users.fetchall()
        print(f"Total users: {len(user_rows)}")
        for row in user_rows:
            print(f"  ID: {row[0]}, Email: {row[1]}, Username: {row[2]}")
        print()

        # Check projects
        print("=== PROJECTS ===")
        result = await conn.execute(text("SELECT id, user_id, title, status FROM projects"))
        rows = result.fetchall()
        print(f"Total projects in DB: {len(rows)}")
        for row in rows:
            print(f"  ID: {row[0]}")
            print(f"  User: {row[1]}")
            print(f"  Title: {row[2]}")
            print(f"  Status: {row[3]}")
            print("---")

if __name__ == "__main__":
    asyncio.run(check())
