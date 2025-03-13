import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, APIRouter, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from passlib.context import CryptContext
from .database.db import get_session, create_tables, AsyncSessionLocal
from .database.init_database import init_db
from .authentication.schema import UserLoginRequest, UserLoginResponse
from .authentication.auth import verify_access_token, authenticate_user, generate_access_token, generate_refresh_token

load_dotenv()
origins = [
    "http://localhost:3000",  # Adjust based on where your frontend is served
    "frontend",  # If you're using Docker containers, this could be the frontend's container name
]
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await create_tables()
        async with AsyncSessionLocal() as conn:
            print("Initializing database")
            await init_db(conn, pwd_context)
        yield
    finally:
        print("Cleaning up")

private_router = APIRouter(dependencies=[Depends(verify_access_token)])
@private_router.get("/")
async def private_route():
    return {"message": "You are authorized"}

login_router = APIRouter()
@login_router.post("/token")
async def login(payload: UserLoginRequest):
    user = await authenticate_user(payload.username, payload.password, pwd_context)
    if not user:
        return {"message": "Invalid credentials"}
    access_token = generate_access_token({"sub": user.email})
    refresh_token = generate_refresh_token({"sub": user.email})
    return UserLoginResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows all origins listed in the origins variable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    print("Hello")
    return {"message": "Hello World"}

@app.get("/test")
async def test(request: Request):
    print(f"Request details: {request.headers}")
    response_data = {"message": "This is the backend's answer"}  # Response data
    print(f"Response: {response_data}")  # Log the response data
    return response_data    

app.include_router(login_router)
app.include_router(private_router, prefix="/private")
