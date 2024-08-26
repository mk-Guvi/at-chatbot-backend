from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.chatbot_models import ChatI, PopulatedChatI, ChatbotMessageTracking, MessageInfo, ChatActionI
from app.models.user_models import UserInDB
from bson import ObjectId
from uuid import UUID, uuid4
import json
from typing import List, Dict, Any, Tuple
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

    async def get_chatbot_response(self, chat_id: str, context: str, chatbot_user_id: str) -> ApiResponse:
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
            return ApiResponse(type="success", data={"chat": None, "has_next": has_next})
        else:
            action_id = last_message['message'].get('action_id')
            
            if action_id:
                await self.responseByActionId[action_id](self, chat_id, context, chatbot_user_id)
                if action_id in ["action_step_1_1", "action_step_1_2"]:
                    latest_messages = await self.get_latest_chat_message(chat_id, count=2)
                else:
                    latest_messages = await self.get_latest_chat_message(chat_id, count=1)
                if latest_messages.type=="success":
                    chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
                    current_step = chat_history[context] if chat_history else None
                    context_data = self.chatbot_data.get(context, {})
                    has_next = current_step != list(context_data.keys())[-1] if current_step else True
                
                    return ApiResponse(type="success", data={"chats": latest_messages.data['chats'], "has_next": has_next})
                return latest_messages
            
            chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
            current_step = chat_history[context] if chat_history else None
            if current_step:
                step_data = self.get_step_data(context, current_step)
                chat = ChatI(
                    from_user=chatbot_user_id,
                    chat_id=chat_id,
                    message=MessageInfo(
                        id=str(uuid4()),
                        type="string",
                        value=step_data.get("message", ""),
                        action_id=None
                    ),
                    actions=[ChatActionI(**action) for action in step_data.get("actions", [])]
                )
                context_data = self.chatbot_data.get(context, {})
                has_next = current_step != list(context_data.keys())[-1]
                return ApiResponse(type="success", data={"chat": chat.model_dump(), "has_next": has_next})

    async def create_chat(self, user_id: str) -> ChatI:
        step_data = self.get_step_data("ONBOARDING", "STEP_1")
        
        message = MessageInfo(
            id=str(uuid4()),
            type="string",
            value=step_data.get("message", "Welcome"),
            action_id=None
        )
        
        actions = [ChatActionI(**action) for action in step_data.get("actions", [])]
        
        chat = ChatI(
            from_user=str(user_id),
            message=message,
            actions=actions
        )
        
        chat_dict = chat.model_dump(by_alias=True)
        chat_dict['from_user'] = str(chat_dict['from_user'])  # Convert UUID to string for MongoDB
        await self.chatbot_messages.insert_one(chat_dict)
        
        # Initialize chat history
        await self.update_chat_history(chat.chat_id, "ONBOARDING", "STEP_1")
        
        return chat

    async def get_all_chats(self) -> List[PopulatedChatI]:
        cursor = self.chatbot_messages.find()
        chats = []
        async for chat in cursor:
            user = await self.users.find_one({"user_id": UUID(chat['from_user'])})
            if user:
                chat['from_user'] = UserInDB(**user)
            chats.append(PopulatedChatI(**chat))
        return chats

    async def delete_chat_message(self, chat_id: str, message_id: str, context: str, user_id: str) -> ApiResponse:
        try:
            # 1. Validate context
            allowed_contexts = ["ONBOARDING"]  # Add more contexts as needed
            if context not in allowed_contexts:
                return ApiResponse(type="error", message="Invalid Context")

            # 2. Check if chat has ended
            chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
            if not chat_history:
                return ApiResponse(type="error", message="Chat not found")

            current_step = chat_history.get(context)
            context_data = self.chatbot_data.get(context, {})
            last_step = list(context_data.keys())[-1]

            if current_step == last_step:
                return ApiResponse(type="error", message="Cannot delete message after chat has ended")

            # 3. Get the message to be deleted
            message_to_delete = await self.chatbot_messages.find_one({"chat_id": chat_id, "message.id": UUID(message_id)})
            if not message_to_delete:
                return ApiResponse(type="error", message="Message not found")

            # 4. Check if the message is from the bot
            if message_to_delete['from_user'] != user_id:
                return ApiResponse(type="error", message="Cannot delete bot message")

            # 5. Delete the message and all subsequent messages
            delete_result = await self.chatbot_messages.delete_many({
                "chat_id": chat_id,
                "created_at": {"$gte": message_to_delete['created_at']}
            })

            # 6. Update the context step
            previous_bot_message = await self.chatbot_messages.find_one({
                "chat_id": chat_id,
                "from_user": {"$ne": user_id},
                "created_at": {"$lt": message_to_delete['created_at']}
            }, sort=[("created_at", -1)])

            if previous_bot_message:
                previous_step = self.get_step_from_message(previous_bot_message, context)
                await self.update_chat_history(chat_id, context, previous_step)

            return ApiResponse(type="success", message="Message successfully deleted",data=delete_result)

        except Exception as e:
            return ApiResponse(type="error", message=str(e))
        
    async def update_chat_message(self, chat_id: str, message_id: str, context: str, new_message: MessageInfo, user_id: str) -> ApiResponse:
        try:
            # 1. Validate context
            allowed_contexts = ["ONBOARDING"]  # Add more contexts as needed
            if context not in allowed_contexts:
                return ApiResponse(type="error", message="Invalid Context")

            # 2. Check if chat has ended
            chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
            if not chat_history:
                return ApiResponse(type="error", message="Chat not found")

            current_step = chat_history.get(context)
            context_data = self.chatbot_data.get(context, {})
            last_step = list(context_data.keys())[-1]

            if current_step == last_step:
                return ApiResponse(type="error", message="Cannot update message after chat has ended")

            # 3. Get the message to be updated
            message_to_update = await self.chatbot_messages.find_one({"chat_id": chat_id, "message.id": message_id})
            if not message_to_update:
                return ApiResponse(type="error", message="Message not found")

            # 4. Check if the message is from the user
            if message_to_update['from_user'] != user_id:
                return ApiResponse(type="error", message="Cannot update bot message")

            # 5. Update the message
            update_result = await self.chatbot_messages.update_one(
                {"chat_id": chat_id, "message.id": message_id},
                {"$set": {
                    "message": new_message.model_dump(),
                    "updated_at": datetime.now(timezone.utc)
                }}
            )

            if update_result.modified_count == 0:
                return ApiResponse(type="error", message="Failed to update message")

            # 6. Update the context step if necessary
            new_step = self.get_step_from_user_message(new_message, context)
            if new_step:
                await self.update_chat_history(chat_id, context, new_step)

            return ApiResponse(type="success", message="Message successfully updated")

        except Exception as e:
            return ApiResponse(type="error", message=str(e))

    def get_step_from_user_message(self, message: MessageInfo, context: str) -> str:
        for step, step_data in self.chatbot_data.get(context, {}).items():
            for action in step_data.get('actions', []):
                if action.get('action_id') == message.action_id:
                    return step
        return None  # Return None if no matching step is found
    
    def get_step_from_message(self, message: Dict[str, Any], context: str) -> str:
        message_value = message['message']['value']
        for step, step_data in self.chatbot_data.get(context, {}).items():
            if step_data.get('message') == message_value:
                return step
        return "STEP_1"  # Default to STEP_1 if not found
    
    async def get_all_chat_messages(self, chat_id: str) -> ApiResponse:
        try:
            # Retrieve all messages for the given chat_id
            messages = await self.chatbot_messages.find({"chat_id": chat_id}).sort("created_at", 1).to_list(length=None)
            
            if not messages:
                return ApiResponse(type="error", message="Chat not found or no messages available")

            # Convert messages to ChatI objects
            chat_messages = [ChatI(**message) for message in messages]

            # Determine if there are more steps available
            chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
            has_next = False

            if chat_history:
                for context, current_step in chat_history.items():
                    if context != '_id' and context != 'chat_id':
                        context_data = self.chatbot_data.get(context, {})
                        steps = list(context_data.keys())
                        if current_step != steps[-1]:
                            has_next = True
                            break

            return ApiResponse(
                type="success",
                data={
                    "chats": [chat.model_dump() for chat in chat_messages],
                    "has_next": has_next
                }
            )

        except Exception as e:
            return ApiResponse(type="error", message=str(e))
    
    async def create_chat_message(self, chat_id: str, content: str, chatbot_user_id: str):
        message = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            message=MessageInfo(
                id=str(uuid4()),
                type="string",
                value=content,
                action_id=None
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.chatbot_messages.insert_one(message.model_dump(by_alias=True))

    async def add_chat_message(self, chat_id: str, message: MessageInfo, user_id: str,context:str) -> ApiResponse:
        try:
            chat_messages = await self.chatbot_messages.find({"chat_id": chat_id}).sort("created_at", -1).to_list(length=None)
            
            if not chat_messages:
                return ApiResponse(type="error", message="Chat not found")
            
            new_message = ChatI(
                from_user=str(user_id),
                chat_id=chat_id,
                message=MessageInfo(
                    id=str(uuid4()),
                    type=message.type,
                    value=message.value,
                    action_id=message.action_id
                ),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            new_message_dict = new_message.model_dump(by_alias=True)
            result = await self.chatbot_messages.insert_one(new_message_dict)
            
            if not result.inserted_id:
                return ApiResponse(type="error", message="Failed to add message to chat")            
            
            return ApiResponse(type="success", data=new_message.model_dump())

        except Exception as e:
            return ApiResponse(type="error", message=str(e))
    
    async def get_chat(self, chat_id: str) -> PopulatedChatI:
        chat = await self.chatbot_messages.find_one({"chat_id": chat_id})
        if chat:
            user = await self.users.find_one({"user_id": UUID(chat['from_user'])})
            if user:
                chat['from_user'] = UserInDB(**user)
            return PopulatedChatI(**chat)
        return None

    def get_next_step(self, current_step: str,context:str) -> Tuple[bool, Dict[str, Any]]:
        context_data = self.chatbot_data.get(context, {})
        steps = list(context_data.keys())
        current_index = steps.index(current_step) if current_step in steps else -1
        
        if current_index < len(steps) - 1:
            next_step = steps[current_index + 1]
            step_data = context_data[next_step]
            chat = ChatI(
                from_user=str(UUID(int=0)),  # Placeholder UUID for bot
                chat_id="",  # This will be set when actually creating the message
                message=MessageInfo(
                    id=str(uuid4()),
                    type="string",
                    value=step_data.get("message", ""),
                    action_id=None
                ),
                actions=[ChatActionI(**action) for action in step_data.get("actions", [])]
            )
            return True, {"step": next_step, "chat": chat}
        return False, {}

    async def update_chat_history(self, chat_id: str, context: str, step: str):
        await self.chatbot_messages_history.update_one(
            {"chat_id": chat_id},
            {"$set": {context: step}},
            upsert=True
        )

    async def get_latest_chat_message(self, chat_id: str, count: int = 1) -> ApiResponse:
        latest_messages_cursor  = self.chatbot_messages.find(
            {"chat_id": chat_id},
            sort=[("updated_at", -1)]
        ).limit(count)
        latest_messages = await latest_messages_cursor.to_list(length=count)
        if latest_messages:
            chats = [ChatI(**message).model_dump() for message in latest_messages]
            return ApiResponse(type="success", data={"chats": chats})
        else:
            return ApiResponse(type="error", message="No messages found")

    responseByActionId = {
        "action_step_1_1": lambda self, chat_id, context, chatbot_user_id: self.handle_action_step_1_1(chat_id, context, chatbot_user_id),
        "action_step_1_2": lambda self, chat_id, context, chatbot_user_id: self.handle_action_step_1_2(chat_id, context, chatbot_user_id),
        "action_step_2_1": lambda self, chat_id, context, chatbot_user_id: self.handle_action_step_2_1(chat_id, context, chatbot_user_id),
        "action_step_2_2": lambda self, chat_id, context, chatbot_user_id: self.handle_action_step_2_2(chat_id, context, chatbot_user_id),
    }

    async def handle_action_step_1_1(self, chat_id: str, context: str, chatbot_user_id: str):
        await self.create_chat_message(chat_id, "We have mailed the report to your mail", chatbot_user_id)
        has_next, result = self.get_next_step("STEP_1", context)
        if has_next:
             step_data = result.get("chat")
             if step_data.message.value:
                next_message = ChatI(
                from_user=chatbot_user_id,
                chat_id=chat_id,
                message=step_data.message,
                actions=step_data.actions,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
                )
                await self.chatbot_messages.insert_one(next_message.model_dump(by_alias=True))
        
        
        await self.update_chat_history(chat_id, context, "STEP_2")

    async def handle_action_step_1_2(self, chat_id: str, context: str, chatbot_user_id: str):
        await self.create_chat_message(chat_id, "We have assigned an agent and you will receive the mail", chatbot_user_id)        
        has_next, result = self.get_next_step("STEP_1", context)
        if has_next:
             step_data = result.get("chat")
             if step_data.message.value:
                next_message = ChatI(
                from_user=chatbot_user_id,
                chat_id=chat_id,
                message=step_data.message,
                actions=step_data.actions,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
                )
                await self.chatbot_messages.insert_one(next_message.model_dump(by_alias=True))
        
        
        await self.update_chat_history(chat_id, context, "STEP_2")

    async def handle_action_step_2_1(self, chat_id: str, context: str, chatbot_user_id: str):
        step_data = self.get_step_data(context, "STEP_1")
        message = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            message=MessageInfo(
                id=str(uuid4()),
                type="string",
                value=step_data.get("message", ""),
                action_id=None
            ),
            actions=[ChatActionI(**action) for action in step_data.get("actions", [])],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.chatbot_messages.insert_one(message.model_dump(by_alias=True))
        await self.update_chat_history(chat_id, context, "STEP_1")

    async def handle_action_step_2_2(self, chat_id: str, context: str, chatbot_user_id: str):
        step_data = self.get_step_data(context, "STEP_3")
        message = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            message=MessageInfo(
                id=str(uuid4()),
                type="string",
                value=step_data.get("message", ""),
                action_id=None
            ),
            actions=[ChatActionI(**action) for action in step_data.get("actions", [])],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.chatbot_messages.insert_one(message.model_dump(by_alias=True))
        await self.update_chat_history(chat_id, context, "STEP_3")