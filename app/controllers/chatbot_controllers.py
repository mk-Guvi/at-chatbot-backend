from fastapi import Request, Depends
from app.services.chatbot_services import ChatbotService
from app.services.user_services import UserService
from app.models.chatbot_models import PopulatedChatI
from app.schemas import ApiResponse

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
        user_id = request.state.user_id
        user_result = await user_service.get_user(user_id)
        
        if user_result.type == "error":
            return user_result  # Return the error response directly
        
        if not user_result.data:
            return ApiResponse(type="error", message="User not found")
        
        user_data = user_result.data
        chat = await chatbot_service.create_chat(str(user_data["user_id"]))
        
        if not chat:
            return ApiResponse(type="error", message="Failed to create chat")

        await chatbot_service.update_chat_history(chat.chat_id, "STEP_1")
        populated_chat = await chatbot_service.get_chat(chat.chat_id)
        
        return ApiResponse(type="success", data=populated_chat.model_dump())
    except Exception as e:
        return ApiResponse(type="error", message=str(e))