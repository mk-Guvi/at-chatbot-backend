from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from app.models.user_models import UserInDB, UserCreate, UserResponse
from bson import Binary
from typing import Dict, Union, List
from datetime import datetime
from uuid import UUID

class UserService:
    def __init__(self, db_client: AsyncIOMotorClient):
        self.collection: AsyncIOMotorCollection = db_client['artisan']['users']

    async def create_user(self, user: UserCreate) -> Dict[str, Union[str, UserResponse]]:
        try:
            user_in_db = UserInDB(**user.model_dump())
            result = await self.collection.insert_one(user_in_db.model_dump())
            created_user = await self.collection.find_one({"_id": result.inserted_id})
            return {"type": "success", "data": UserResponse.from_db_model(UserInDB(**created_user))}
        except Exception as e:
            return {"type": "error", "data": None, "message": str(e)}

    async def get_user(self, user_id: UUID) -> Dict[str, Union[str, UserResponse, None]]:
        try:
            user = await self.collection.find_one({"user_id": Binary.from_uuid(user_id)})
            if user:
                return {"type": "success", "data": UserResponse.from_db_model(UserInDB(**user))}
            else:
                return {"type": "error", "data": None, "message": "User not found"}
        except Exception as e:
            return {"type": "error", "data": None, "message": str(e)}

    async def get_all_users(self) -> Dict[str, Union[str, List[UserResponse], None]]:
        try:
            users = await self.collection.find().to_list(length=None)
            user_responses = [UserResponse.from_db_model(UserInDB(**user)) for user in users]
            return {"type": "success", "data": user_responses}
        except Exception as e:
            return {"type": "error", "data": None, "message": str(e)}