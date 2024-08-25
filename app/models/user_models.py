from pydantic import BaseModel, Field
from datetime import datetime, timezone
from uuid import UUID, uuid4

class UserBase(BaseModel):
    name: str
    profile_image: str
    is_bot: bool = Field(default=False)

class UserCreate(UserBase):
    pass

class UserInDB(UserBase):
    user_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserResponse(UserBase):
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_model(cls, db_model: UserInDB) -> 'UserResponse':
        return cls(
            user_id=db_model.user_id,
            name=db_model.name,
            profile_image=db_model.profile_image,
            is_bot=db_model.is_bot,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at
        )