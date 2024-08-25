# app/services/chatbot_services.py

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.chatbot_models import ChatI, PopulatedChatI, ChatbotMessageTracking, MessageInfo, ChatActionI
from app.models.user_models import UserInDB
from bson import ObjectId
from uuid import UUID
import json
from typing import List, Dict, Any

class ChatbotService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.chatbot_messages = self.db['chatbot_messages']
        self.chatbot_messages_history = self.db['chatbot_messages_history']
        self.users = self.db['users']
        self.chatbot_data = self.load_chatbot_data()

    def load_chatbot_data(self) -> Dict[str, Any]:
        with open('chatbot.json', 'r') as f:
            return json.load(f)

    def get_step_data(self, context: str, step: str) -> Dict[str, Any]:
        return self.chatbot_data.get(context, {}).get(step, {})

    async def create_chat(self, user_id: UUID) -> ChatI:
        step_data = self.get_step_data("ONBOARDING", "STEP_1")
        
        message = MessageInfo(
            type="string",
            value=step_data.get("message", "Welcome")
        )
        
        actions = [ChatActionI(**action) for action in step_data.get("actions", [])]
        
        chat = ChatI(
            from_user=user_id,
            message=message,
            actions=actions
        )
        
        chat_dict = chat.model_dump(by_alias=True)
        chat_dict['from_user'] = str(chat_dict['from_user'])  # Convert UUID to string for MongoDB
        await self.chatbot_messages.insert_one(chat_dict)
        return chat

    async def update_chat_history(self, chat_id: str, onboarding_key: str) -> None:
        tracking = ChatbotMessageTracking(chat_id=chat_id, ONBOARDING=onboarding_key)
        tracking_dict = tracking.model_dump()
        await self.chatbot_messages_history.insert_one(tracking_dict)

    async def get_chat(self, chat_id: str) -> PopulatedChatI:
        chat = await self.chatbot_messages.find_one({"chat_id": chat_id})
        if chat:
            user = await self.users.find_one({"user_id": UUID(chat['from_user'])})
            if user:
                chat['from_user'] = UserInDB(**user)
            return PopulatedChatI(**chat)
        return None

    async def get_all_chats(self) -> List[PopulatedChatI]:
        cursor = self.chatbot_messages.find()
        chats = []
        async for chat in cursor:
            user = await self.users.find_one({"user_id": UUID(chat['from_user'])})
            if user:
                chat['from_user'] = UserInDB(**user)
            chats.append(PopulatedChatI(**chat))
        return chats