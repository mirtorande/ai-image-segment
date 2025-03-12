import os
import jwt
from dotenv import load_dotenv
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated
from ..database.db import get_session
from ..database.tables import User

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_HOURS = int(os.getenv("REFRESH_TOKEN_EXPIRE_HOURS"))

# Get user from database

async def get_user(email: str) -> User | None:
    statement = select(User).where(User.email == email)
    async for db in get_session():
        result = (await db.execute(statement)).scalars().first()
        return result

# Local authentication functions

def verify_password(pwd_context: CryptContext, plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(pwd_context: CryptContext, password: str):
    return pwd_context.hash(password)

async def authenticate_user(email: str, password: str, pwd_context: CryptContext) -> User | None:
    user = await get_user(email)
    if not user or not verify_password(pwd_context, password, user.password):
        return None
    return user

# Remote authentication functions

def generate_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def generate_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def verify_access_token(auth: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]) -> User | None:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    jwt_token = auth.credentials
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        user = await get_user(email)
        if user is None:
            raise credentials_exception
        return user
    except jwt.ExpiredSignatureError:
        raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception


def refresh_access_token(token: str) -> str:
    """Authenticate user before calling this function"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    data = {"sub": email}
    return generate_access_token(data)