import json
from typing import Any

from fastapi import Request, HTTPException
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from lib_utils.sql import sql
from web import engine
from lib_identity.identity import _extract_bearer_token, validate_session_token
import traceback

class IncidentRecordMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        payload = await self._read_payload(request)

        # defaults so finally block never crashes
        status_code = 500
        user_code = None
        user_type = None

        # -------------------------
        # Authorization handling
        # -------------------------
        auth_header = request.headers.get("authorization")

        if auth_header:
            scheme, _, token = auth_header.partition(" ")

            if scheme.lower() == "bearer" and token:
                token = token.strip()

                try:
                    context = getattr(request.state, "context", None)

                    if context and getattr(context, "conn", None):
                        validation = validate_session_token(
                            context.conn, token
                        )
                        user_code = validation.user_code
                        user_type = validation.user_type

                except Exception:
                    # token issue should not break request logging
                    user_code = None
                    user_type = None

        # -------------------------
        # Main request execution
        # -------------------------
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except HTTPException as exc:
            status_code = exc.status_code
            raise

        except Exception:
            status_code = 500
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error",
            )

        # -------------------------
        # Always log request
        # -------------------------
        finally:
            try:
                await self._insert_incident_record(
                    status_code=status_code,
                    method=request.method,
                    endpoint=request.url.path,
                    payload=payload,
                    user_code=user_code,
                    user_type=user_type,
                )
            except Exception:
                # logging should never break API response
                pass

    async def _read_payload(self, request: Request) -> dict[str, Any] | list[Any] | None:
        body = await request.body()

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive  # noqa: SLF001

        if not body:
            return None

        content_type = request.headers.get("content-type", "").lower()
        if "application/json" not in content_type:
            return {"raw_body": body.decode("utf-8", errors="replace")[:4000]}

        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"raw_body": body.decode("utf-8", errors="replace")[:4000]}

    async def _insert_incident_record(
        self,
        status_code: int,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | list[Any] | None,
        user_code: str,
        user_type: str,
    ) -> None:
        try:
            with engine.begin() as conn:
                sql(conn).insert_one(
                    "incident_record",
                    {
                        "status_code": status_code,
                        "method": method,
                        "endpoint": endpoint,
                        "payload": payload,
                        "user_code": user_code,
                        "user_type": user_type,
                    }
                )
        except Exception as exc:
            traceback.print_exc()
            pass
