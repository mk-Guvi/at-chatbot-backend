from fastapi import APIRouter, Depends, Request
from app.controllers.user_controllers import (
    get_user_service,
    create_user,
    get_all_users,
    get_user,
    get_chatbot_user
)
from app.models.user_models import UserCreate
from app.schemas import ApiResponse
from uuid import UUID
from typing import Dict, Any, List

router = APIRouter()

@router.post("/", response_model=ApiResponse[Dict[str, Any]])
async def create_new_user(user: UserCreate, user_service=Depends(get_user_service)):
    return await create_user(user, user_service)

@router.get("/", response_model=ApiResponse[Dict[str, List[Dict[str, Any]]]])
async def list_all_users(user_service=Depends(get_user_service)):
    return await get_all_users(user_service)

@router.get("/{user_id}", response_model=ApiResponse[Dict[str, Any]])
async def retrieve_user(user_id: UUID, user_service=Depends(get_user_service)):
    return await get_user(str(user_id), user_service)

@router.get("/chatbot", response_model=ApiResponse[Dict[str, Any]])
async def retrieve_chatbot_user(user_service=Depends(get_user_service)):
    return await get_chatbot_user(user_service)