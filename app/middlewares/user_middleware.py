from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class UserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Retrieve the User-ID from headers
        user_id = request.headers.get("User-ID", None)
        print(user_id,"User Id")
        # Attach the User-ID to the request state
        request.state.user_id = user_id
        
        # Process the request and get the response
        response = await call_next(request)
        
        return response
