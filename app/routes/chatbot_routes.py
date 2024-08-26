from fastapi import APIRouter, Depends, Request
from app.controllers.chatbot_controllers import create_chat, get_chatbot_response, get_chatbot_service, get_user_service, add_chat_message
from app.services.chatbot_services import ChatbotService
from app.services.user_services import UserService
from app.schemas import ApiResponse
from app.models.chatbot_models import PopulatedChatI, ChatI, MessageInfo
from typing import Dict, Any
from pydantic import BaseModel

router = APIRouter()

class ChatbotResponseRequest(BaseModel):
    context: str

class AddChatMessageRequest(BaseModel):
    message: MessageInfo

@router.post("/create_chat", response_model=ApiResponse[Dict[str, Any]])
async def create_new_chat(
    request: Request,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
):
    return await create_chat(request, chatbot_service, user_service)

@router.post("/get_response/{chat_id}", response_model=ApiResponse[Dict[str, Any]])
async def get_response(
    request: Request,
    chat_id: str,
    chatbot_request: ChatbotResponseRequest,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
):
    return await get_chatbot_response(request, chat_id, chatbot_request.context, chatbot_service, user_service)

@router.post("/add_chat/{chat_id}", response_model=ApiResponse[ChatI])
async def add_chat_message_route(
    request: Request,
    chat_id: str,
    message_request: AddChatMessageRequest,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
):
    return await add_chat_message(request, chat_id, message_request.message, chatbot_service, user_service)