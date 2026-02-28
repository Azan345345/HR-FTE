"""
Create a test user in the database.

Usage:
    cd backend
    python scripts/create_test_user.py

Works with both SQLite (local dev) and Supabase PostgreSQL.
Credentials: test@gmail.com / Test@12345
"""

import asyncio
import sys
import os

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import init_db, AsyncSessionLocal
from app.db.models import User
from app.core.security import get_password_hash
from sqlalchemy import select

TEST_EMAIL = "test@gmail.com"
TEST_PASSWORD = "Test@12345"
TEST_NAME = "Test User"


async def create_test_user():
    print("Initialising database …")
    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.email == TEST_EMAIL))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Test user already exists: {TEST_EMAIL}")
            print("  → Login with: test@gmail.com / Test@12345")
            return

        user = User(
            name=TEST_NAME,
            email=TEST_EMAIL,
            hashed_password=get_password_hash(TEST_PASSWORD),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    print("Test user created successfully!")
    print(f"  Email:    {TEST_EMAIL}")
    print(f"  Password: {TEST_PASSWORD}")
    print(f"  User ID:  {user.id}")
    print("\nYou can now log in at http://localhost:5173")


if __name__ == "__main__":
    asyncio.run(create_test_user())
