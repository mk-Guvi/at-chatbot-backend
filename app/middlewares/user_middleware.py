from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid

class UserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Retrieve the User-ID from headers
        user_id_str = request.headers.get("User-ID",  "f20e9aad-1e32-4e37-8944-969dadb5aa6f")
        
        # # Validate and parse the User-ID as a UUID, or generate a new one if invalid
        # try:
        #     user_id = uuid.UUID(user_id_str) if user_id_str else uuid.uuid4()
        # except ValueError:
        #     user_id = uuid.uuid4()
        
        print(user_id_str, "User Id")
        
        # Attach the User-ID to the request state
        request.state.user_id = user_id_str
        
        # Process the request and get the response
        response = await call_next(request)
        
        return response
