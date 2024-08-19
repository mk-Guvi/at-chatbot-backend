from fastapi import Request, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.user_services import UserService
from app.models.user_models import UserCreate, UserResponse
from typing import Dict, Any, List
from uuid import UUID

async def get_user_service(request: Request) -> UserService:
    db_client: AsyncIOMotorClient = request.app.mongodb_client
    return UserService(db_client)

async def create_user(user: UserCreate, user_service: UserService = Depends(get_user_service)) -> UserResponse:
    result = await user_service.create_user(user)
    if result['type'] == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result['data']

async def get_all_users(user_service: UserService = Depends(get_user_service)) -> List[UserResponse]:
    result = await user_service.get_all_users()
    if result['type'] == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result['data']

async def get_user(user_id: UUID, user_service: UserService = Depends(get_user_service)) -> UserResponse:
    result = await user_service.get_user(user_id)
    if result['type'] == 'error':
        raise HTTPException(status_code=404, detail=result['message'])
    return result['data']