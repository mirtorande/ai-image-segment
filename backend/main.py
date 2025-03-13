import os
from io import BytesIO
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, APIRouter, Request, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from passlib.context import CryptContext
from .database.db import get_session, create_tables, AsyncSessionLocal
from .database.init_database import init_db
from .authentication.schema import UserLoginRequest, UserLoginResponse
from .authentication.auth import verify_access_token, authenticate_user, generate_access_token, generate_refresh_token
from .AI.segment import segment_image

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
UPLOAD_DIR = "./uploads"
LAST_IMAGE = None

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

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

@app.post("/upload")
async def upload_image(image: UploadFile = File(...)):
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")
    
    file_path = os.path.join(UPLOAD_DIR, image.filename)
    
    try:
        with open(file_path, "wb") as f:
            f.write(await image.read())
            global LAST_IMAGE
            LAST_IMAGE = image.filename

        return JSONResponse(
            status_code=200,
            content={"message": "Image uploaded successfully", "filename": image.filename, "file_path": str(file_path)},
        )

    except Exception as e:
        print(f"Error occurred: {e}")  # Log the error to the console for debugging
        raise HTTPException(status_code=500, detail="Failed to save image. " + str(e))

@app.post("/process-image")
async def process_image(image: UploadFile = File(...)):
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")
    
    try:
        # Read the image directly from the request body (not from the file system)
        image_data = await image.read()

        # Process the image
        processed_img = segment_image(image_data)  # Modify segment_image to accept image data instead of a filename

        # Save the processed image into a BytesIO object to send it as a response
        img_byte_arr = BytesIO()
        processed_img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return StreamingResponse(img_byte_arr, media_type="image/png")
    
    except Exception as e:
        print(f"Error occurred: {e}")  # Log the error for debugging
        raise HTTPException(status_code=500, detail="Failed to process image.")

app.include_router(login_router)
app.include_router(private_router, prefix="/private")
