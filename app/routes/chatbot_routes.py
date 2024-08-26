from fastapi import APIRouter, Depends, Request
from app.controllers.chatbot_controllers import create_chat, get_chatbot_response, get_all_chat_messages,get_chatbot_service, get_user_service, add_chat_message, delete_chat_message,update_chat_message,get_user_chats
from app.services.chatbot_services import ChatbotService
from app.services.user_services import UserService
from app.schemas import ApiResponse
from app.models.chatbot_models import PopulatedChatI, ChatI, MessageInfo
from typing import List,Dict, Any

from pydantic import BaseModel

router = APIRouter()

class ChatbotResponseRequest(BaseModel):
    context: str
class UpdateChatMessageRequest(BaseModel):
    message_id: str
    context: str
    message: MessageInfo
class AddChatMessageRequest(BaseModel):
    message: MessageInfo

class DeleteChatMessageRequest(BaseModel):
    message_id: str
    context: str

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

@router.delete("/delete_chat_message/{chat_id}", response_model=ApiResponse)
async def delete_chat_message_route(
    request: Request,
    chat_id: str,
    delete_request: DeleteChatMessageRequest,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
):
    return await delete_chat_message(request, chat_id, delete_request.message_id, delete_request.context, chatbot_service, user_service)

@router.get("/chatbot/{chat_id}", response_model=ApiResponse[Dict[str, Any]])
async def get_all_chat_messages_route(
    request: Request,
    chat_id: str,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
):
    return await get_all_chat_messages(request, chat_id, chatbot_service, user_service)



@router.put("/update_chat_message/{chat_id}", response_model=ApiResponse)
async def update_chat_message_route(
    request: Request,
    chat_id: str,
    update_request: UpdateChatMessageRequest,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
):
    return await update_chat_message(request, chat_id, update_request.message_id, update_request.context, update_request.message, chatbot_service, user_service)


@router.get("/", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_user_chats_route(
    request: Request,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
):
    user_id = request.state.user_id
    if not user_id:
        return ApiResponse(type="error", message="User not authenticated")
    
    return await get_user_chats(request,chatbot_service,user_service)
