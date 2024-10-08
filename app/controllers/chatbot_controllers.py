# app/controllers/chatbot_controllers.py

from fastapi import Request, Depends
from app.services.chatbot_services import ChatbotService
from app.services.user_services import UserService
from app.models.chatbot_models import  MessageInfo
from app.schemas import ApiResponse
import uuid 
async def get_chatbot_service(request: Request) -> ChatbotService:
    return ChatbotService(request.app.mongodb)

async def get_user_service(request: Request) -> UserService:
    return UserService(request.app.mongodb)

async def create_chat(
    request: Request, 
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    __: UserService = Depends(get_user_service)
) -> ApiResponse:
    try:
        # Create a chat with the chatbot ID
        user_id = request.state.user_id
        chat = await chatbot_service.create_chat("4b3c9f32-bfee-426f-ba09-4810da0930f1",user_id)  # chatbot id
        
        if not chat:
            return ApiResponse(type="error", message="Failed to create chat")

        # Get the populated chat details
        populated_chat = await chatbot_service.get_chat(chat.chat_id)
        
        # Return the response with the chat data inside a 'chats' list
        return ApiResponse(
            type="success", 
            data={
                "chats": [populated_chat.model_dump()],
                "chat_id":chat.chat_id
            }
        )
    except Exception as e:
        return ApiResponse(type="error", message=str(e))
    
async def get_all_chat_messages(
    request: Request,
    chat_id: str,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
) -> ApiResponse:
    try:
        body= await request.json()

        user_id = request.state.user_id
        
        if not user_id:
            return ApiResponse(type="error", message="User not authenticated")
        
        user_result = await user_service.get_user(uuid.UUID(user_id))
        
        if user_result.type == "error":
            return user_result
        
        if not user_result.data:
            return ApiResponse(type="error", message="User not found")
        
        result = await chatbot_service.get_all_chat_messages(chat_id,context=body.get("context"))
        
        return result
    except Exception as e:
        return ApiResponse(type="error", message=str(e))


async def get_chatbot_response(
    request: Request,
    chat_id: str,
    context: str,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
) -> ApiResponse:
    try:
        user_id = request.state.user_id
        chatbot_user_result = await user_service.get_chatbot_user()
        
        if chatbot_user_result.type == "error":
            return chatbot_user_result
        
        if not chatbot_user_result.data:
            return ApiResponse(type="error", message="Chatbot user not found")
        
        chatbot_user_id = str(chatbot_user_result.data["user_id"])
    
        result = await chatbot_service.get_chatbot_response(chat_id, context, chatbot_user_id,user_id)

        return result
    except Exception as e:
        return ApiResponse(type="error", message=str(e))
    
async def add_chat_message(
    request: Request,
    chat_id: str,
    message: MessageInfo,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
) -> ApiResponse:
    try:
        body = await request.json()
        context = body.get("context")
        from_message_id = body.get("from_message_id")
        user_id = request.state.user_id
        
        if not user_id:
            return ApiResponse(type="error", message="User not authenticated")
        
        user_result = await user_service.get_user(uuid.UUID(user_id))
        
        if user_result.type == "error":
            return user_result
        
        if not user_result.data:
            return ApiResponse(type="error", message="User not found")
        
        result = await chatbot_service.add_chat_message(chat_id, message, str(user_id), context, from_message_id)
        
        return result
    except Exception as e:
        return ApiResponse(type="error", message=str(e))

async def delete_chat_message(
    request: Request,
    chat_id: str,
    message_id: str,
    context: str,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
) -> ApiResponse:
    try:
        user_id = request.state.user_id
        
        if not user_id:
            return ApiResponse(type="error", message="User not authenticated")
        
        user_result = await user_service.get_user(uuid.UUID(user_id))
        
        if user_result.type == "error":
            return user_result
        
        if not user_result.data:
            return ApiResponse(type="error", message="User not found")
        
        return await chatbot_service.delete_chat_message(chat_id, message_id, context, user_id)
        
        
    except Exception as e:
        return ApiResponse(type="error", message=str(e))
    
async def update_chat_message(
    request: Request,
    chat_id: str,
    message_id: str,
    context: str,
    message: MessageInfo,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
) -> ApiResponse:
    try:
        user_id = request.state.user_id
        
        if not user_id:
            return ApiResponse(type="error", message="User not authenticated")
        
        user_result = await user_service.get_user(uuid.UUID(user_id))
        
        if user_result.type == "error":
            return user_result
        
        if not user_result.data:
            return ApiResponse(type="error", message="User not found")
        
        result = await chatbot_service.update_chat_message(chat_id, message_id, context, message, str(user_id))
        
        return result
    except Exception as e:
        return ApiResponse(type="error", message=str(e))
    

async def get_user_chats(
    request: Request,
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
    user_service: UserService = Depends(get_user_service)
) -> ApiResponse:
    try:
        user_id = request.state.user_id
        
        if not user_id:
            return ApiResponse(type="error", message="User not authenticated")
        
        user_result = await user_service.get_user(uuid.UUID(user_id))
        
        if user_result.type == "error":
            return user_result
        
        if not user_result.data:
            return ApiResponse(type="error", message="User not found")
        
        result = await chatbot_service.get_user_chats(user_id)
        
        return result
    except Exception as e:
        return ApiResponse(type="error", message=str(e))