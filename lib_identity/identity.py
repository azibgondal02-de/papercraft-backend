from __future__ import annotations

import secrets
import random
from datetime import datetime, timedelta, timezone, date
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Callable, Optional, TypeVar

from fastapi import HTTPException, Request, status
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from lib_identity.models.identity import (
    CreateResetPasswordRequest,
    InvalidCredentialsError,
    LoginResponse,
    ResetPasswordResponse,
    SessionCreationError,
    TokenValidationError,
    TokenValidationResponse,
    UpdateUserProfileRequest,
    UpdateUserProfileResponse,
    UserProfileResponse,
    UsernameExistsResponse,
)
from lib_utils.password import verify_password, hash_password
from lib_utils.sql import sql
from web import get_context

SESSION_DURATION_HOURS = 2


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def login_user(
    conn: Connection,
    identifier: str,
    password: str,
    *,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> LoginResponse:
    user = sql(
        conn,
        """
        SELECT id, user_code, username, email, password_hash, user_type,
               is_active, school_name, subscription_end
        FROM users
        WHERE username = :identifier
        LIMIT 1
        """,
        {"identifier": identifier},
    ).dict()

    if not user or not user.get("is_active"):
        raise InvalidCredentialsError("Invalid credentials")

    if not verify_password(user["password_hash"], password):
        raise InvalidCredentialsError("Invalid credentials")

    expires_at_utc = datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)
    expires_at_db = expires_at_utc.replace(tzinfo=None)
    session_token = _generate_token()

    try:
        sql(
            conn,
            """
            INSERT INTO sessions (user_code, user_type, session_token, expires_at, ip_address, user_agent)
            VALUES (:user_code, :user_type, :token, :expires_at, :ip_address, :user_agent)
            """,
            {
                "user_code": user["user_code"],
                "user_type": user["user_type"],
                "token": session_token,
                "expires_at": expires_at_db,
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        ).run()

        # Update last_login_at
        sql(
            conn,
            "UPDATE users SET last_login_at = :now WHERE user_code = :user_code",
            {
                "now": datetime.now(timezone.utc).replace(tzinfo=None),
                "user_code": user["user_code"],
            },
        ).run()

        conn.commit()
    except SQLAlchemyError as exc:
        conn.rollback()
        raise SessionCreationError("Unable to create session") from exc

    status, days_left = _get_subscription_status(user.get("subscription_end"))
    return LoginResponse(
        access_token=session_token,
        expires_at=expires_at_utc,
        user_code=user["user_code"],
        username=user["username"],
        user_type=user["user_type"],
        school_name=user.get("school_name"),
        subscription_end=user.get("subscription_end"),
        subscription_status=status,
        subscription_days_left=days_left
    )


def _get_subscription_status(subscription_end) -> tuple[str, Optional[int]]:
    if not subscription_end:
        return "active", None
    today = date.today()
    sub_date = subscription_end.date() if hasattr(subscription_end, "date") else subscription_end
    days_left = (sub_date - today).days
    if days_left < 0:
        return "expired", 0
    elif days_left <= 7:
        return "expiring_soon", days_left
    else:
        return "active", days_left

def logout_user(conn, request):
    try:
        token = _extract_bearer_token(request)
        sql(
            conn,
            """
            UPDATE sessions
            SET expires_at = :expires_at
            WHERE session_token = :token
            """,
            {
                "expires_at": datetime.now(timezone.utc),
                "token": token,
            },
        ).run()
        conn.commit()
    except SQLAlchemyError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session",
        )


def reset_password(conn, user_code: str, payload: CreateResetPasswordRequest):
    user = user_exists(conn, payload.user_code)
    if not user:
        raise HTTPException(status_code=404, detail="no such user exists")

    if verify_password(user["password_hash"], payload.previous_password):
        sql(conn).update_one(
            "users",
            {"password_hash": hash_password(payload.new_password)},
            {"user_code": payload.user_code},
            updated_by=user_code,
        )
        conn.commit()
    else:
        raise HTTPException(status_code=400, detail="previous password is incorrect")

    return ResetPasswordResponse(message="password changed successfully")


def get_user_profile(conn: Connection, user_code: str) -> UserProfileResponse:
    user = sql(
        conn,
        """
        SELECT user_code, username, email, user_type,
               school_name, owner_name, phone_number, city, province,
               subscription_plan, subscription_start, subscription_end
        FROM users
        WHERE user_code = :user_code
        LIMIT 1
        """,
        {"user_code": user_code},
    ).dict()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(**user)


def update_user_profile(
    conn: Connection,
    user_code: str,
    payload: UpdateUserProfileRequest,
) -> UpdateUserProfileResponse:
    # Only update fields that were actually provided
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    set_clause = ", ".join([f"{k} = :{k}" for k in updates])
    updates["user_code"] = user_code

    try:
        sql(
            conn,
            f"UPDATE users SET {set_clause}, updated_at = NOW() WHERE user_code = :user_code",
            updates,
        ).run()
        conn.commit()
    except SQLAlchemyError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        ) from exc

    return UpdateUserProfileResponse(message="Profile updated successfully")


def validate_session_token(conn: Connection, token: str) -> TokenValidationResponse:
    if not token:
        return TokenValidationResponse(valid=False)

    session_record = sql(
        conn,
        """
        SELECT session_id, session_token, expires_at, is_active, user_code, user_type
        FROM sessions
        WHERE session_token = :token
        LIMIT 1
        """,
        {"token": token},
    ).dict()

    if not session_record or not session_record.get("is_active"):
        return TokenValidationResponse(valid=False)

    expires_at_db = session_record.get("expires_at")
    if expires_at_db is None:
        return TokenValidationResponse(valid=False)

    expires_at_utc = (
        expires_at_db.replace(tzinfo=timezone.utc)
        if getattr(expires_at_db, "tzinfo", None) is None
        else expires_at_db.astimezone(timezone.utc)
    )

    now_utc = datetime.now(timezone.utc)
    if expires_at_utc <= now_utc:
        try:
            sql(
                conn,
                "UPDATE sessions SET is_active = FALSE WHERE session_id = :session_id",
                {"session_id": session_record["session_id"]},
            ).run()
            conn.commit()
        except SQLAlchemyError:
            conn.rollback()
            raise TokenValidationError("Failed to update expired token state")
        return TokenValidationResponse(valid=False)

    username_record = sql(
        conn,
        "SELECT username FROM users WHERE user_code = :user_code LIMIT 1",
        {"user_code": session_record["user_code"]},
    ).dict()
    username_value = username_record["username"] if username_record else None

    return TokenValidationResponse(
        valid=True,
        user_code=session_record["user_code"],
        username=username_value,
        user_type=session_record["user_type"],
        expires_at=expires_at_utc,
    )


F = TypeVar("F", bound=Callable[..., Any])


def _extract_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request:
    for value in list(args) + list(kwargs.values()):
        if isinstance(value, Request):
            return value
    raise RuntimeError("Authenticated endpoints must receive a fastapi.Request argument")


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    return token.strip()


def require_auth(func: F) -> F:
    if not callable(func):
        raise TypeError("require_authenticated decorator can only be applied to callables")

    def get_auth_map():
        return {
            "/get_boards": ["admin", "school_admin"],
            "/get_classes_against_board/{board_id}": ["admin", "school_admin"],
            "/get_subjects_against_class_board/{class_id}": ["admin", "school_admin"],
            "/get_topics_against_subject/{subject_id}": ["admin", "school_admin"],
            "/get_chapters_against_subject/{subject_id}": ["admin", "school_admin"],
            "/get_questions": ["admin", "school_admin"],
            "/paper-config/{subject_id}": ["admin", "school_admin"],
            "/generate-questions": ["admin", "school_admin"],
            "/reset-password": ["admin", "school_admin", "teacher"],
            "/username-exists/{username}": ["admin"],
            "/profile": ["admin", "school_admin", "teacher"],
        }

    def ensure(request: Request) -> None:
        context = getattr(request.state, "context", None)
        if context is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Context middleware missing",
            )
        token = _extract_bearer_token(request)
        try:
            validation = validate_session_token(context.conn, token)
        except TokenValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to validate token",
            ) from exc
        if not validation.valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        context.user_code = validation.user_code
        context.user_type = validation.user_type
        request.state.user = {
            "user_code": validation.user_code,
            "user_type": validation.user_type,
            "expires_at": validation.expires_at,
        }

    if iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any):
            request = _extract_request(args, kwargs)
            ensure(request)
            return await func(*args, **kwargs)
        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any):
        request = _extract_request(args, kwargs)
        ensure(request)
        return func(*args, **kwargs)
    return sync_wrapper


def check_username(conn, username: str) -> UsernameExistsResponse:
    if not username_exists(conn=conn, username=username):
        return UsernameExistsResponse(can_use=True)
    suggested_username = username
    while True:
        temp = f"{username}{random.randint(10, 9999)}"
        suggested_username = temp
        if not username_exists(conn=conn, username=temp):
            break
    return UsernameExistsResponse(can_use=False, suggestion=suggested_username)


def username_exists(conn, username: str) -> bool:
    try:
        result = sql(
            conn,
            "SELECT id FROM users WHERE username = :username",
            {"username": username},
        ).dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed",
        )
    return bool(result)


def user_exists(conn, user_code: str):
    try:
        user = sql(
            conn,
            "SELECT password_hash FROM users WHERE user_code = :user_code",
            {"user_code": user_code},
        ).dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed",
        )
    return user