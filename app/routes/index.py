from fastapi import APIRouter
from app.routes.user_routes import router as user_router
from app.routes.chatbot_routes import router as chatbot_router

router = APIRouter()

router.include_router(user_router, prefix="/user", tags=["users"])
router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])