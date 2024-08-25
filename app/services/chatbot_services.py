from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.chatbot_models import ChatI, PopulatedChatI, ChatbotMessageTracking, MessageInfo, ChatActionI
from app.models.user_models import UserInDB
from bson import ObjectId
from uuid import UUID
import json
from typing import List, Dict, Any
from app.schemas import ApiResponse
from datetime import datetime, timezone

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

    async def create_chat(self, user_id: str) -> ChatI:
        step_data = self.get_step_data("ONBOARDING", "STEP_1")
        
        message = MessageInfo(
            type="string",
            value=step_data.get("message", "Welcome")
        )
        
        actions = [ChatActionI(**action) for action in step_data.get("actions", [])]
        
        chat = ChatI(
            from_user=UUID(user_id),
            message=message,
            actions=actions
        )
        
        chat_dict = chat.model_dump(by_alias=True)
        chat_dict['from_user'] = str(chat_dict['from_user'])  # Convert UUID to string for MongoDB
        await self.chatbot_messages.insert_one(chat_dict)
        
        # Initialize chat history
        await self.update_chat_history(chat.chat_id, "ONBOARDING", "STEP_1")
        
        return chat

    async def get_chatbot_response(self, chat_id: str, context: str, chatbot_user_id: UUID) -> ApiResponse:
        last_message = await self.chatbot_messages.find_one(
            {"chat_id": chat_id},
            sort=[("updated_at", -1)]
        )

        if not last_message:
            return ApiResponse(type="error", message="Chat not found")

        user = await self.users.find_one({"user_id": UUID(last_message['from_user'])})
        if not user:
            return ApiResponse(type="error", message="User not found")
        
        if user.get('is_bot') is True:
            chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
            last_step = chat_history[context] if chat_history else None
            context_data = self.chatbot_data.get(context, {})
            has_next = last_step != list(context_data.keys())[-1] if last_step else True
            return ApiResponse(type="success", data=None, has_next=has_next)
        else:
            action_id = last_message['message'].get('action_id')
            if action_id:
                await self.responseByActionId[action_id](self, chat_id, context, chatbot_user_id)
                return await self.get_latest_chat_message(chat_id)
            
            chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
            current_step = chat_history[context] if chat_history else None
            if current_step:
                step_data = self.get_step_data(context, current_step)
                chat = ChatI(
                    from_user=chatbot_user_id,
                    message=MessageInfo(type="string", value=step_data.get("message", "")),
                    actions=[ChatActionI(**action) for action in step_data.get("actions", [])]
                )
                return ApiResponse(type="success", data=chat.model_dump())

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

    async def create_chat_message(self, chat_id: str, content: str, chatbot_user_id: UUID):
        message = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            message=MessageInfo(type="string", value=content),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.chatbot_messages.insert_one(message.model_dump(by_alias=True))

    async def update_chat_history(self, chat_id: str, context: str, step: str):
        await self.chatbot_messages_history.update_one(
            {"chat_id": chat_id},
            {"$set": {context: step}},
            upsert=True
        )

    async def get_latest_chat_message(self, chat_id: str) -> ApiResponse:
        latest_message = await self.chatbot_messages.find_one(
            {"chat_id": chat_id},
            sort=[("updated_at", -1)]
        )
        if latest_message:
            return ApiResponse(type="success", data=ChatI(**latest_message).model_dump())
        return ApiResponse(type="error", message="No messages found")

    responseByActionId = {
        "action_step_1_1": lambda self, chat_id, context, chatbot_user_id: self.handle_action_step_1_1(chat_id, context, chatbot_user_id),
        "action_step_1_2": lambda self, chat_id, context, chatbot_user_id: self.handle_action_step_1_2(chat_id, context, chatbot_user_id),
        "action_step_2_1": lambda self, chat_id, context, chatbot_user_id: self.handle_action_step_2_1(chat_id, context, chatbot_user_id),
        "action_step_2_2": lambda self, chat_id, context, chatbot_user_id: self.handle_action_step_2_2(chat_id, context, chatbot_user_id),
    }

    async def handle_action_step_1_1(self, chat_id: str, context: str, chatbot_user_id: UUID):
        await self.create_chat_message(chat_id, "We have mailed the report to your mail", chatbot_user_id)
        await self.update_chat_history(chat_id, context, "STEP_2")

    async def handle_action_step_1_2(self, chat_id: str, context: str, chatbot_user_id: UUID):
        await self.create_chat_message(chat_id, "We have assigned an agent and you will receive the mail", chatbot_user_id)
        await self.update_chat_history(chat_id, context, "STEP_2")

    async def handle_action_step_2_1(self, chat_id: str, context: str, chatbot_user_id: UUID):
        step_data = self.get_step_data(context, "STEP_1")
        message = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            message=MessageInfo(type="string", value=step_data.get("message", "")),
            actions=[ChatActionI(**action) for action in step_data.get("actions", [])],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.chatbot_messages.insert_one(message.model_dump(by_alias=True))
        await self.update_chat_history(chat_id, context, "STEP_1")

    async def handle_action_step_2_2(self, chat_id: str, context: str, chatbot_user_id: UUID):
        step_data = self.get_step_data(context, "STEP_3")
        message = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            message=MessageInfo(type="string", value=step_data.get("message", "")),
            actions=[ChatActionI(**action) for action in step_data.get("actions", [])],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.chatbot_messages.insert_one(message.model_dump(by_alias=True))
        await self.update_chat_history(chat_id, context, "STEP_3")