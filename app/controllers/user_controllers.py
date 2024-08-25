from fastapi import Request, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.user_services import UserService
from app.models.user_models import UserCreate, UserResponse
from app.schemas import ApiResponse
from typing import List
from uuid import UUID

async def get_user_service(request: Request) -> UserService:
    db_client: AsyncIOMotorClient = request.app.mongodb_client
    return UserService(db_client)

async def create_user(user: UserCreate, user_service: UserService = Depends(get_user_service)) -> ApiResponse:
    try:
        result = await user_service.create_user(user)
        return ApiResponse(type="success", data=result.dict())
    except Exception as e:
        return ApiResponse(type="error", message=str(e))

async def get_all_users(user_service: UserService = Depends(get_user_service)) -> ApiResponse:
    try:
        result = await user_service.get_all_users()
        return ApiResponse(type="success", data={"users": [user.dict() for user in result]})
    except Exception as e:
        return ApiResponse(type="error", message=str(e))

async def get_user(user_id: UUID, user_service: UserService = Depends(get_user_service)) -> ApiResponse:
    try:
        result = await user_service.get_user(user_id)
        if result:
            return ApiResponse(type="success", data=result.dict())
        return ApiResponse(type="error", message="User not found")
    except Exception as e:
        return ApiResponse(type="error", message=str(e))