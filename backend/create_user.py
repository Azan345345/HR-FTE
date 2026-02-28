import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.config import settings

from app.db.database import engine

async def create_user():
    print(f"Using DB: {settings.DATABASE_URL}")
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Check if user exists
        result = await session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "azanmian123123@gmail.com"}
        )
        user = result.fetchone()
        
        if not user:
            from app.core.security import hash_password
            import uuid
            
            user_id = str(uuid.uuid4())
            pwd = hash_password("Azan@5678")
            
            await session.execute(
                text("INSERT INTO users (id, name, email, password_hash) VALUES (:id, :name, :email, :pwd)"),
                {"id": user_id, "name": "Azan", "email": "azanmian123123@gmail.com", "pwd": pwd}
            )
            await session.commit()
            print("User created successfully.")
        else:
            print("User already exists.")

if __name__ == "__main__":
    asyncio.run(create_user())
