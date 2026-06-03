from __future__ import annotations

import secrets
import base64
from datetime import date, datetime, timezone
from typing import Optional

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from lib_identity.models.identity import (
    CreateUserRequest,
    CreateUserResponse,
    UpdateUserRequest,
    UpdateUserResponse,
    UserListItem,
    UserListResponse,
    UploadLogoResponse,
    UpdateBoardPermissionsRequest,
    UpdateBoardPermissionsResponse,
)
from lib_utils.password import hash_password
from lib_utils.sql import sql

cloudinary.config(
    cloud_name="ddxgyz6ha",
    api_key="836136496762524",
    api_secret="aB1jIzKiKH22VqltJ7eZu4QrUcg"
)


def _generate_user_code() -> str:
    return f"USR_{secrets.token_hex(6).upper()}"


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


def create_user(
    conn: Connection,
    payload: CreateUserRequest,
    created_by: str,
) -> CreateUserResponse:
    # Check username not taken
    existing = sql(
        conn,
        "SELECT id FROM users WHERE username = :username",
        {"username": payload.username},
    ).dict()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user_code = _generate_user_code()
    password_hash = hash_password(payload.password)

    try:
        sql(
            conn,
            """
            INSERT INTO users (
                user_code, username, email, school_name, owner_name,
                phone_number, city, province, user_type, subscription_plan,
                subscription_start, subscription_end, password_hash,
                is_active, created_by
            ) VALUES (
                :user_code, :username, :email, :school_name, :owner_name,
                :phone_number, :city, :province, :user_type, :subscription_plan,
                :subscription_start, :subscription_end, :password_hash,
                1, :created_by
            )
            """,
            {
                "user_code": user_code,
                "username": payload.username,
                "email": payload.email,
                "school_name": payload.school_name,
                "owner_name": payload.owner_name,
                "phone_number": payload.phone_number,
                "city": payload.city,
                "province": payload.province,
                "user_type": payload.user_type,
                "subscription_plan": payload.subscription_plan,
                "subscription_start": payload.subscription_start,
                "subscription_end": payload.subscription_end,
                "password_hash": password_hash,
                "created_by": created_by,
            },
        ).run()

        # Assign board/class permissions
        if payload.class_ids:
            for class_id in payload.class_ids:
                sql(
                    conn,
                    """
                    INSERT IGNORE INTO user_board_permissions (user_code, class_id)
                    VALUES (:user_code, :class_id)
                    """,
                    {"user_code": user_code, "class_id": class_id},
                ).run()

        conn.commit()
    except SQLAlchemyError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        ) from exc

    return CreateUserResponse(
        message="User created successfully",
        user_code=user_code,
        username=payload.username,
    )


def update_user(
    conn: Connection,
    target_user_code: str,
    payload: UpdateUserRequest,
    updated_by: str,
) -> UpdateUserResponse:
    user = sql(
        conn,
        "SELECT user_code FROM users WHERE user_code = :user_code",
        {"user_code": target_user_code},
    ).dict()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {k: v for k, v in payload.model_dump().items()
               if v is not None and k != "class_ids"}

    if updates:
        set_clause = ", ".join([f"{k} = :{k}" for k in updates])
        updates["user_code"] = target_user_code
        updates["updated_by"] = updated_by
        try:
            sql(
                conn,
                f"UPDATE users SET {set_clause}, updated_at = NOW(), updated_by = :updated_by WHERE user_code = :user_code",
                updates,
            ).run()
        except SQLAlchemyError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=500, detail="Failed to update user"
            ) from exc

    # Update permissions if provided
    if payload.class_ids is not None:
        try:
            sql(
                conn,
                "DELETE FROM user_board_permissions WHERE user_code = :user_code",
                {"user_code": target_user_code},
            ).run()
            for class_id in payload.class_ids:
                sql(
                    conn,
                    """
                    INSERT IGNORE INTO user_board_permissions (user_code, class_id)
                    VALUES (:user_code, :class_id)
                    """,
                    {"user_code": target_user_code, "class_id": class_id},
                ).run()
        except SQLAlchemyError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=500, detail="Failed to update permissions"
            ) from exc

    conn.commit()
    return UpdateUserResponse(message="User updated successfully")


def get_user_list(conn: Connection) -> UserListResponse:
    users = sql(
        conn,
        """
        SELECT user_code, username, email, school_name, owner_name,
               phone_number, city, province, user_type, is_active,
               subscription_plan, subscription_end, school_logo, created_at
        FROM users
        WHERE user_type != 'admin'
        ORDER BY created_at DESC
        """,
        {},
    ).dicts()

    result = []
    for u in users:
        # Get class permissions
        perms = sql(
            conn,
            "SELECT class_id FROM user_board_permissions WHERE user_code = :user_code",
            {"user_code": u["user_code"]},
        ).dicts()
        class_ids = [p["class_id"] for p in perms]

        sub_status, days_left = _get_subscription_status(u.get("subscription_end"))
        result.append(UserListItem(
            **{k: v for k, v in u.items()},
            subscription_status=sub_status,
            subscription_days_left=days_left,
            class_ids=class_ids,
        ))

    return UserListResponse(users=result, total=len(result))


def upload_school_logo(
    conn: Connection,
    user_code: str,
    image_base64: str,
) -> UploadLogoResponse:
    try:
        image_data = base64.b64decode(image_base64)
        result = cloudinary.uploader.upload(
            image_data,
            public_id=f"logos/{user_code}",
            overwrite=True,
            folder="",
        )
        logo_url = result["secure_url"]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload logo: {str(exc)}"
        ) from exc

    try:
        sql(
            conn,
            "UPDATE users SET school_logo = :logo_url WHERE user_code = :user_code",
            {"logo_url": logo_url, "user_code": user_code},
        ).run()
        conn.commit()
    except SQLAlchemyError as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to save logo URL") from exc

    return UploadLogoResponse(message="Logo uploaded successfully", logo_url=logo_url)


def update_board_permissions(
    conn: Connection,
    target_user_code: str,
    payload: UpdateBoardPermissionsRequest,
) -> UpdateBoardPermissionsResponse:
    try:
        sql(
            conn,
            "DELETE FROM user_board_permissions WHERE user_code = :user_code",
            {"user_code": target_user_code},
        ).run()
        for class_id in payload.class_ids:
            sql(
                conn,
                """
                INSERT IGNORE INTO user_board_permissions (user_code, class_id)
                VALUES (:user_code, :class_id)
                """,
                {"user_code": target_user_code, "class_id": class_id},
            ).run()
        conn.commit()
    except SQLAlchemyError as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to update permissions") from exc

    return UpdateBoardPermissionsResponse(message="Permissions updated successfully")