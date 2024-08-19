from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from app.routes.index import router as routes
from app.middlewares.user_middleware import  UserMiddleware
import os
from dotenv import load_dotenv
from typing import AsyncIterator

load_dotenv()

async def get_database_client() -> AsyncIOMotorClient:
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        raise ValueError("MONGODB_URL environment variable is not set")
    client = AsyncIOMotorClient(mongodb_url)
    return client

async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup event
    app.mongodb_client = await get_database_client()
    yield  # Application is now running
    # Shutdown event
    app.mongodb_client.close()


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom UserMiddleware
app.add_middleware(UserMiddleware)

@app.get('/')
def read_root():
    return {'Ping': 'Pong'}

app.include_router(routes, prefix="/api/v1")

