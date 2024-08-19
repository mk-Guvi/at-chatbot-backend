from fastapi import APIRouter, Depends, Body, HTTPException
from app.controllers.user_controllers import create_user, get_user_service, get_all_users, get_user
from app.services.user_services import UserService
from app.models.user_models import UserResponse, UserCreate
from typing import Dict, Any, List
from uuid import UUID

router = APIRouter()

@router.post("/", response_model=Dict[str, Any])
async def create_new_user(user: UserCreate, user_service: UserService = Depends(get_user_service)):
    result = await create_user(user, user_service)
    return {"type": "success", "data": result}

@router.get("/", response_model=Dict[str, Any])
async def list_all_users(user_service: UserService = Depends(get_user_service)):
    result = await get_all_users(user_service)
    return {"type": "success", "data": result}

@router.get("/{user_id}", response_model=Dict[str, Any])
async def retrieve_user(user_id: UUID, user_service: UserService = Depends(get_user_service)):
    result = await get_user(user_id, user_service)
    return {"type": "success", "data": result}