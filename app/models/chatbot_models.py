# app/models/chatbot_models.py

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union
from datetime import datetime, timezone
from uuid import UUID, uuid4
from bson import ObjectId

class ChatActionI(BaseModel):
    type: str = Field(..., pattern="^(BUTTON|FILE)$")
    value: str
    action_id: str

class MessageInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str = "string"
    value: str
    action_id: Optional[str] = None

class ChatI(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, json_encoders={ObjectId: str, UUID: str})

    from_user: Union[UUID, ObjectId] = Field(..., alias="from_user")
    chat_id: str = Field(default_factory=lambda: str(uuid4()))
    context: str = "ONBOARDING"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: MessageInfo
    actions: List[ChatActionI] = []

    @property
    def from_user_str(self) -> str:
        return str(self.from_user)

class PopulatedChatI(ChatI):
    from_user: 'UserInDB'

class ChatbotMessageTracking(BaseModel):
    chat_id: str
    ONBOARDING: str

# Importing UserInDB to resolve the forward reference
from app.models.user_models import UserInDB