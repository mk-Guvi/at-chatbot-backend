from fastapi import APIRouter, Depends, Request
from app.services.user_services import UserService
from app.models.user_models import UserCreate
from app.schemas import ApiResponse
from uuid import UUID
from typing import Dict, Any, List

router = APIRouter()

async def get_user_service(request: Request) -> UserService:
    return UserService(request.app.mongodb)

@router.post("/", response_model=ApiResponse[Dict[str, Any]])
async def create_new_user(user: UserCreate, user_service: UserService = Depends(get_user_service)):
    return await user_service.create_user(user)

@router.get("/", response_model=ApiResponse[Dict[str, List[Dict[str, Any]]]])
async def list_all_users(user_service: UserService = Depends(get_user_service)):
    result = await user_service.get_all_users()
    if result.type == "success" and not result.data["users"]:
        return ApiResponse(type="success", message="No users found", data={"users": []})
    return result

@router.get("/{user_id}", response_model=ApiResponse[Dict[str, Any]])
async def retrieve_user(user_id: UUID, user_service: UserService = Depends(get_user_service)):
    return await user_service.get_user(user_id)