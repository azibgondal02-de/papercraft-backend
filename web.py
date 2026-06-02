from typing import Optional
import os
from dotenv import load_dotenv

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from sqlalchemy import create_engine

load_dotenv(override=True)


# Global SQLAlchemy engine
def _db_url(migrate: bool = False) -> str:
    env_url = os.getenv("EDUCARE_DATABASE_URL")
    if env_url:
        return env_url

    user = os.getenv("EDUCARE_DB_USER")
    password = os.getenv("EDUCARE_DB_PASSWORD")
    if migrate:
        host = os.getenv("EDUCARE_DB_HOST_MIGRATE", "localhost")
    else:
        host = os.getenv("EDUCARE_DB_HOST", "localhost")
    name = os.getenv("EDUCARE_DB_NAME")
    if user and password and name:
        return f"mysql+pymysql://{user}:{password}@{host}/{name}?charset=utf8mb4"

# Global SQLAlchemy engine
engine = create_engine(_db_url())
migrate_engine = create_engine(_db_url(migrate=True))

class RequestContext:
    def __init__(self, request: Optional[Request] = None, connection=None):
        self.request = request
        self.conn = connection
        self.x_api_key = None
        self.user_code = None
        self.user_type = None
        self._init_from_request()

    def _init_from_request(self):
        if self.request:
            self.x_api_key = self.request.headers.get("x-api-key")
            self.user_code = self.request.headers.get("user-code")
            self.user_type = self.request.headers.get("user-type")
        if self.conn is None:
            self.conn = engine.connect()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


class Context(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        connection = engine.connect()
        request_context = RequestContext(request=request, connection=connection)
        request.state.context = request_context
        request.state.db = connection
        try:
            response = await call_next(request)
        finally:
            request_context.close()
            request.state.context = None
            request.state.db = None
        return response


def get_context(request: Request) -> RequestContext:
    context = getattr(request.state, "context", None)
    if context is None:
        raise RuntimeError("Context middleware must be installed")
    return context


authorization_map = {
    "admin": ["/create-school"],
}


def check_user_authorization(request: Request) -> None:
    context = get_context(request)
    user_type = getattr(context, "user_type", None)
    endpoint = request.url.path
    if user_type not in authorization_map:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this endpoint",
        )
    if endpoint not in authorization_map[user_type]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this endpoint",
        )

def get_context_with_user_info(request: Request) -> tuple[object, str, str]:
    context = get_context(request)
    user_code = getattr(context, "user_code", None)
    user_type = getattr(context, "user_type", None)
    if not user_code or not user_type:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authenticated user context missing",
        )
    return context, user_code, user_type
