# app/controllers/chatbot_controllers.py

from fastapi import Request, Depends
from app.services.chatbot_services import ChatbotService
from app.services.user_services import UserService
from app.models.chatbot_models import PopulatedChatI, ChatI
from app.schemas import ApiResponse
import uuid 

async def get_chatbot_service(request: Request) -> ChatbotService:
    return ChatbotService(request.app.mongodb)

async def get_user_service(request: Request) -> UserService:
    return UserService(request.app.mongodb)

async def create_chat(
    request: Request, 
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
) -> ApiResponse:
    try:
        
        user_result = await user_service.get_user(uuid.UUID("4b3c9f32-bfee-426f-ba09-4810da0930f1"))
        
        if user_result.type == "error":
            return user_result
        
        if not user_result.data:
            return ApiResponse(type="error", message="User not found")
        
        user_data = user_result.data
        chat = await chatbot_service.create_chat(str(user_data["user_id"]))
        
        if not chat:
            return ApiResponse(type="error", message="Failed to create chat")

        populated_chat = await chatbot_service.get_chat(chat.chat_id)
        
        return ApiResponse(type="success", data=populated_chat.model_dump())
    except Exception as e:
        return ApiResponse(type="error", message=str(e))

async def get_chatbot_response(
    _: Request,
    chat_id: str,
    context: str,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
) -> ApiResponse:
    try:
        chatbot_user_result = await user_service.get_chatbot_user()
        
        if chatbot_user_result.type == "error":
            return chatbot_user_result
        
        if not chatbot_user_result.data:
            return ApiResponse(type="error", message="Chatbot user not found")
        
        chatbot_user_id = chatbot_user_result.data["user_id"]
        
        result = await chatbot_service.get_chatbot_response(chat_id, context, chatbot_user_id)

        return result
    except Exception as e:
        return ApiResponse(type="error", message=str(e))