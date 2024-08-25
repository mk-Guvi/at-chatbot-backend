from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.user_models import UserInDB, UserCreate, UserResponse
from app.schemas import ApiResponse
from typing import List
from uuid import UUID

class UserService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db['users']

    async def create_user(self, user: UserCreate) -> ApiResponse:
        try:
            user_in_db = UserInDB(**user.model_dump())
            result = await self.collection.insert_one(user_in_db.model_dump())
            created_user = await self.collection.find_one({"_id": result.inserted_id})
            return ApiResponse(type="success", data=UserResponse.from_db_model(UserInDB(**created_user)).model_dump())
        except Exception as e:
            return ApiResponse(type="error", message=str(e))

    async def get_user(self, user_id: UUID) -> ApiResponse:
        try:
            user = await self.collection.find_one({"user_id": user_id})
            if user:
                return ApiResponse(type="success", data=UserResponse.from_db_model(UserInDB(**user)).model_dump())
            else:
                return ApiResponse(type="error", message="User not found")
        except Exception as e:
            return ApiResponse(type="error", message=str(e))

    async def get_all_users(self) -> ApiResponse:
        try:
            users = await self.collection.find().to_list(length=None)
            user_responses = [UserResponse.from_db_model(UserInDB(**user)).model_dump() for user in users]
            return ApiResponse(type="success", data={"users": user_responses})
        except Exception as e:
            return ApiResponse(type="error", message=str(e))