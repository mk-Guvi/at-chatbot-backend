from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import uuid4, UUID
from bson import Binary
from typing import Any

class UserBase(BaseModel):
    name: str
    profile_image: str
    is_bot: bool = Field(default=False)

class UserCreate(UserBase):
    pass

class UserInDB(UserBase):
    user_id: Binary = Field(default_factory=lambda: Binary.from_uuid(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={Binary: lambda v: str(UUID(bytes=v))}
    )

class UserResponse(UserBase):
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )

    @classmethod
    def from_db_model(cls, db_model: UserInDB) -> 'UserResponse':
        return cls(
            user_id=UUID(bytes=db_model.user_id),
            name=db_model.name,
            profile_image=db_model.profile_image,
            is_bot=db_model.is_bot,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at
        )