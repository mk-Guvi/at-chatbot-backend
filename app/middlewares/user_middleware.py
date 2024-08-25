from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid

class UserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Retrieve the User-ID from headers
        user_id_str = request.headers.get("User-ID",  "4b3c9f32-bfee-426f-ba09-4810da0930f1")
        
        # Validate and parse the User-ID as a UUID, or generate a new one if invalid
        try:
            user_id = uuid.UUID(user_id_str) if user_id_str else uuid.uuid4()
        except ValueError:
            user_id = uuid.uuid4()
        
        print(user_id, "User Id")
        
        # Attach the User-ID to the request state
        request.state.user_id = user_id
        
        # Process the request and get the response
        response = await call_next(request)
        
        return response
