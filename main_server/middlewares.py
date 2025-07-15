from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse


from utils.security import verify_jwt_token


class VerifyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/auth"):
            return await call_next(request)

        authorization = request.headers.get("authorization")

        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header missing"}
            )

        token = authorization.split(" ")[1]

        status, data = verify_jwt_token(token)

        if not status:
            return JSONResponse(
                status_code=401,
                content={"detail": data}
            )

        return await call_next(request)
