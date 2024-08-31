from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4

class MessageInfo(BaseModel):
    type: str = Field(..., pattern="^(string|HTML)$")
    value: str
    action_id: Optional[str] = None
    id: UUID = Field(default_factory=uuid4)

class ChatActionI(BaseModel):
    type: str = Field(..., pattern="^(BUTTON|FILE)$")
    value: str
    action_id: str

class ChatI(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    from_user: str
    user_id:str#To Group the chats by user
    chat_id: str = Field(default_factory=lambda: str(uuid4()))
    context: str = "ONBOARDING"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: MessageInfo
    actions: List[ChatActionI] = []

    @property
    def from_user_str(self) -> str:
        return str(self.from_user)


class ChatbotMessageTracking(BaseModel):
    chat_id: str
    ONBOARDING: str

# Importing UserInDB to resolve the forward reference
from app.models.user_models import UserInDB