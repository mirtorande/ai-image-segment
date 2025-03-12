import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from passlib.context import CryptContext
from .tables import User
from ..authentication.auth import get_password_hash

load_dotenv()
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

async def init_db(conn: AsyncSession, pwd_context: CryptContext):
    # Check if admin user exists
    statement = text("SELECT * FROM users WHERE email = :email")
    result = await conn.execute(statement, {"email": ADMIN_EMAIL})
    user = result.fetchone()
    if not user:
        hashed_password = get_password_hash(pwd_context, ADMIN_PASSWORD)
        admin_user = User(email=ADMIN_EMAIL, password=hashed_password)
        conn.add(admin_user)
        await conn.commit()
        await conn.refresh(admin_user)
        print("Admin user created")
    else:
        print("Admin user already exists")
        