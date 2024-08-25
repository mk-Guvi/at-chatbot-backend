from fastapi import APIRouter, Depends, Request
from app.controllers.chatbot_controllers import create_chat, get_chatbot_service, get_user_service
from app.services.chatbot_services import ChatbotService
from app.services.user_services import UserService
from app.schemas import ApiResponse
from app.models.chatbot_models import PopulatedChatI
from typing import Dict, Any

router = APIRouter()

@router.post("/create_chat", response_model=ApiResponse[Dict[str, Any]])
async def create_new_chat(
    request: Request,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
):
    return await create_chat(request, chatbot_service, user_service)