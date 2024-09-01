from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.chatbot_models import ChatI, MessageInfo, ChatActionI
from app.models.user_models import UserInDB
from bson import ObjectId
from uuid import UUID, uuid4
import json

from typing import List, Dict, Any, Tuple,Optional
from app.schemas import ApiResponse
from datetime import datetime, timezone

class ChatbotService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.chatbot_messages = self.db['chatbot_messages']
        self.chatbot_messages_history = self.db['chatbot_messages_history']
        self.users = self.db['users']
        self.allowed_contexts=["ONBOARDING"]
        self.chatbot_data = self.load_chatbot_data()
        
    
    def load_chatbot_data(self) -> Dict[str, Any]:
        with open('chatbot.json', 'r') as f:
            return json.load(f)

    def get_step_data(self, context: str, step: str) -> Dict[str, Any]:
        return self.chatbot_data.get(context, {}).get(step, {})

    async def get_chatbot_response(self, chat_id: str, context: str, chatbot_user_id: str, user_id: str) -> ApiResponse:
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
            return ApiResponse(type="success", data={"chats": [], "has_next": has_next})
        else:
            action_id = last_message['message'].get('action_id')
            if action_id:
                response = await self.responseByActionId[action_id](self, chat_id, context, chatbot_user_id, user_id)
                
                if action_id in ["action_step_1_1", "action_step_1_2"]:
                    latest_messages = response
                else:
                    latest_messages = response
                
                chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
                current_step = chat_history[context] if chat_history else None
                context_data = self.chatbot_data.get(context, {})
                has_next = current_step != list(context_data.keys())[-1] if current_step else True
                
                return ApiResponse(type="success", data={"chats": latest_messages, "has_next": has_next})
            else:
                chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
                current_step = chat_history[context] if chat_history else None
                if current_step:
                    step_data = self.get_step_data(context, current_step)
                    
                    chat = ChatI(
                        from_user=chatbot_user_id,
                        chat_id=str(chat_id),
                        user_id=str(user_id),
                        message=MessageInfo(
                            id=str(uuid4()),
                            type="string",
                            value=step_data.get("message", ""),
                            action_id=None
                        ),
                        actions=[ChatActionI(**action) for action in step_data.get("actions", [])]
                    )
                    
                    # Insert the new chatbot message
                    await self.chatbot_messages.insert_one(chat.model_dump(by_alias=True))
                    
                    context_data = self.chatbot_data.get(context, {})
                    has_next = current_step != list(context_data.keys())[-1]
                    
                    return ApiResponse(type="success", data={"chats": [chat.model_dump()], "has_next": has_next})
                else:
                    return ApiResponse(type="error", message="No current step found in chat history")                
            
    async def get_user_chats(self, user_id: str) -> ApiResponse:
        try:
            chats = await self.chatbot_messages.aggregate([
                {"$match": {"user_id": user_id}},
                {"$sort": {"updated_at": -1}},
                {"$group": {
                    "_id": "$chat_id",
                    "last_message": {"$first": "$$ROOT"}
                }},
                {"$replaceRoot": {"newRoot": "$last_message"}},
                {"$sort": {"updated_at": -1}}
            ]).to_list(None)

            # Convert ObjectId to string
            for chat in chats:
                if "_id" in chat and isinstance(chat["_id"], ObjectId):
                    chat["_id"] = str(chat["_id"])
                if "chat_id" in chat and isinstance(chat["chat_id"], ObjectId):
                    chat["chat_id"] = str(chat["chat_id"])

            if not chats:
                return ApiResponse(type="success", data=[])

            return ApiResponse(type="success", data=chats)
        except Exception as e:
            return ApiResponse(type="error", message=str(e))

        
    async def create_chat(self, from_user_id:str,user_id: str) -> ChatI:
        step_data = self.get_step_data("ONBOARDING", "STEP_1")
        
        message = MessageInfo(
            id=str(uuid4()),
            type="string",
            value=step_data.get("message", "Welcome"),
            action_id=None
        )
        
        actions = [ChatActionI(**action) for action in step_data.get("actions", [])]
        
        chat = ChatI(
            from_user=str(from_user_id),
            user_id=str(user_id), 
            message=message,
            actions=actions
        )
        
        chat_dict = chat.model_dump(by_alias=True)
        chat_dict['from_user'] = str(chat_dict['from_user'])  # Convert UUID to string for MongoDB
        await self.chatbot_messages.insert_one(chat_dict)
        
        await self.update_chat_history(chat.chat_id, "ONBOARDING", "STEP_1")

        return ChatI(**chat_dict)

    async def get_all_chats(self) -> List[ChatI]:
        cursor = self.chatbot_messages.find()
        chats = []
        async for chat in cursor:
            chats.append(ChatI(**chat))

    async def delete_chat_message(self, chat_id: str, message_id: str, context: str, user_id: str) -> ApiResponse:
        try:
            if context not in self.allowed_contexts:
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
            await self.chatbot_messages.delete_many({
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

            return ApiResponse(type="success", message="Message successfully deleted",data=None)

        except Exception as e:
            return ApiResponse(type="error", message=str(e))
        
    async def update_chat_message(self, chat_id: str, message_id: str, context: str, new_message: MessageInfo, user_id: str) -> ApiResponse:
        try:
            if context not in self.allowed_contexts:
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
            try:
                message_id_uuid = UUID(message_id)
            except ValueError:
                return ApiResponse(type="error", message="Invalid message_id format")

            message_to_update = await self.chatbot_messages.find_one({"chat_id": chat_id, "message.id": message_id_uuid})
            if not message_to_update:
                return ApiResponse(type="error", message="Message not found")

            # 4. Check if the message is from the user
            if message_to_update['from_user'] != user_id:
                return ApiResponse(type="error", message="Cannot update bot message")

            # 5. Handle action_id
            if new_message.action_id:
                return ApiResponse(type="error", message="Cannot update message with an action_id")
            delete_result = await self.chatbot_messages.delete_many({
                "chat_id": chat_id,
                "created_at": {"$gt": message_to_update['created_at']}
            })
            print(f"Deleted {delete_result.deleted_count} subsequent messages")
            # 6. Create new_message_payload
            new_message_payload = {
                "id": UUID(message_id),
                "value": new_message.value or "",
                "type": new_message.type or "string"
            }

            # 7. Update the message using find_one_and_update
            try:
                updated_message = await self.chatbot_messages.find_one_and_update(
                    {"chat_id": chat_id, "message.id": message_id_uuid},
                    {"$set": {
                        "message": new_message_payload,
                        "updated_at": datetime.now(timezone.utc)
                    }},
                    return_document=True  # This ensures we get the updated document
                )
                
            except Exception as e:
                print(f"Error updating message: {str(e)}")
                return ApiResponse(type="error", message=f"Failed to update message: {str(e)}")

            if not updated_message:
                return ApiResponse(type="error", message="Failed to update message")

            # 8. Update the context step if necessary
            new_step = self.get_step_from_user_message(new_message, context)
            if new_step:
                await self.update_chat_history(chat_id, context, new_step)

            
            chat_message = ChatI(**updated_message)
            return ApiResponse(type="success", message="Message successfully updated", data=chat_message.model_dump())

        except Exception as e:
            print(f"Unexpected error in update_chat_message: {str(e)}")
            return ApiResponse(type="error", message=f"An unexpected error occurred: {str(e)}")


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
    
    
    async def get_all_chat_messages(self, chat_id: str,context:str) -> ApiResponse:
        try:
            messages = await self.chatbot_messages.find({"chat_id": chat_id, "context": context}).sort("created_at", 1).to_list(length=None)
        
            if not messages:
                return ApiResponse(type="error", message="Chat not found or no messages available")

            chat_messages = [ChatI(**message) for message in messages]

            chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
            has_next = False

            if chat_history:
                current_step = chat_history.get(context)
                if current_step:
                    context_data = self.chatbot_data.get(context, {})
                    steps = list(context_data.keys())
                    if current_step != steps[-1]:
                        has_next = True

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

    async def add_chat_message(self, chat_id: str, message: MessageInfo, user_id: str, context: str, from_message_id: Optional[str] = None) -> ApiResponse:
        try:
            if context not in self.allowed_contexts:
                return ApiResponse(type="error", message="Invalid Context")

            chat_history = await self.chatbot_messages_history.find_one({"chat_id": chat_id})
            if not chat_history:
                return ApiResponse(type="error", message="Chat not found")

            current_step = chat_history.get(context)
            context_data = self.chatbot_data.get(context, {})
            last_step = list(context_data.keys())[-1]

            if current_step == last_step:
                return ApiResponse(type="error", message="Cannot add message after chat has ended")

            if from_message_id:
                from_message = await self.chatbot_messages.find_one({"chat_id": chat_id, "message.id": UUID(from_message_id)})
                if from_message:
                    await self.chatbot_messages.delete_many({
                        "chat_id": chat_id,
                        "created_at": {"$gt": from_message['created_at']}
                    })
                else:
                    return ApiResponse(type="error", message="From message not found")

            new_message = ChatI(
                from_user=str(user_id),
                chat_id=chat_id,
                user_id=str(user_id),
                context=context,
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
            
            return ApiResponse(type="success", data=new_message_dict)

        except Exception as e:
            return ApiResponse(type="error", message=str(e))
    
    async def get_chat(self, chat_id: str) -> ChatI:
        chat = await self.chatbot_messages.find_one({"chat_id": chat_id})
        if chat:
            return ChatI(**chat)
        return None
    
    def get_next_step(self, current_step: str, context: str) -> Tuple[bool, Dict[str, Any]]:
        context_data = self.chatbot_data.get(context, {})
        steps = list(context_data.keys())
        current_index = steps.index(current_step) if current_step in steps else -1
        
        if current_index < len(steps) - 1:
            next_step = steps[current_index + 1]
            step_data = context_data[next_step]
            return True, {"step": next_step, "data": step_data}
        return False, {}

    async def update_chat_history(self, chat_id: str, context: str, step: str):
        await self.chatbot_messages_history.update_one(
            {"chat_id": chat_id},
            {"$set": {context: step}},
            upsert=True
        )

    async def get_latest_chat_message(self, chat_id: str, count: int = 1) -> ApiResponse:
        latest_messages_cursor = self.chatbot_messages.find(
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
        "action_step_1_1": lambda self, chat_id, context,chatbot_user_id,user_id: self.handle_action_step_1_1(chat_id, context, chatbot_user_id,user_id),
        "action_step_1_2": lambda self, chat_id, context, chatbot_user_id,user_id: self.handle_action_step_1_2(chat_id, context, chatbot_user_id,user_id),
        "action_step_2_1": lambda self, chat_id, context, chatbot_user_id,user_id: self.handle_action_step_2_1(chat_id, context, chatbot_user_id,user_id),
        "action_step_2_2": lambda self, chat_id, context, chatbot_user_id,user_id: self.handle_action_step_2_2(chat_id, context, chatbot_user_id,user_id),
    }

    async def handle_action_step_1_1(self, chat_id: str, context: str, chatbot_user_id: str, user_id: str):
        initial_response = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            user_id=user_id,
            message=MessageInfo(
                id=str(uuid4()),
                type="string",
                value="We have mailed the report to your email address.",
                action_id=None
            ),
            actions=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.chatbot_messages.insert_one(initial_response.model_dump(by_alias=True))

        has_next, result = self.get_next_step("STEP_1", context)
        next_message = None
        if has_next:
            step_data = result.get("data")
            if step_data and step_data.get("message"):
                next_message = ChatI(
                    from_user=chatbot_user_id,
                    chat_id=chat_id,
                    user_id=user_id,
                    message=MessageInfo(
                        id=str(uuid4()),
                        type="string",
                        value=step_data["message"],
                        action_id=None
                    ),
                    actions=[ChatActionI(**action) for action in step_data.get("actions", [])],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                await self.chatbot_messages.insert_one(next_message.model_dump(by_alias=True))

        await self.update_chat_history(chat_id, context, "STEP_2")

        messages = [initial_response.model_dump()]
        if next_message:
            messages.append(next_message.model_dump())
        
        return messages

    async def handle_action_step_1_2(self, chat_id: str, context: str, chatbot_user_id: str, user_id: str):
        initial_response = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            user_id=user_id,
            message=MessageInfo(
                id=str(uuid4()),
                type="string",
                value="We have assigned an agent and you will receive the mail.",
                action_id=None
            ),
            actions=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.chatbot_messages.insert_one(initial_response.model_dump(by_alias=True))

        has_next, result = self.get_next_step("STEP_1", context)
        next_message = None
        if has_next:
            step_data = result.get("data")
            if step_data and step_data.get("message"):
                next_message = ChatI(
                    from_user=chatbot_user_id,
                    chat_id=chat_id,
                    user_id=user_id,
                    message=MessageInfo(
                        id=str(uuid4()),
                        type="string",
                        value=step_data["message"],
                        action_id=None
                    ),
                    actions=[ChatActionI(**action) for action in step_data.get("actions", [])],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                await self.chatbot_messages.insert_one(next_message.model_dump(by_alias=True))

        await self.update_chat_history(chat_id, context, "STEP_2")

        messages = [initial_response.model_dump()]
        if next_message:
            messages.append(next_message.model_dump())
        
        return messages

    async def handle_action_step_2_1(self, chat_id: str, context: str, chatbot_user_id: str, user_id: str):
        step_data = self.get_step_data(context, "STEP_1")
        message = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            user_id=user_id,
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
        
        return [message.model_dump()]

    async def handle_action_step_2_2(self, chat_id: str, context: str, chatbot_user_id: str, user_id: str):
        step_data = self.get_step_data(context, "STEP_3")
        message = ChatI(
            from_user=chatbot_user_id,
            chat_id=chat_id,
            user_id=user_id,
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
        
        return [message.model_dump()]