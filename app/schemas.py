from pydantic import BaseModel
from typing import Optional, Dict, Any, Generic, TypeVar

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    type: str
    message: Optional[str] = None
    data: Optional[T] = None