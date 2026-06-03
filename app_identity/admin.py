from fastapi import APIRouter, HTTPException, Request, status, Depends
from fastapi.security import HTTPBearer

from lib_identity.admin import (
    create_user,
    update_user,
    get_user_list,
    upload_school_logo,
    update_board_permissions,
)
from lib_identity.models.identity import (
    CreateUserRequest,
    CreateUserResponse,
    UpdateUserRequest,
    UpdateUserResponse,
    UserListResponse,
    UploadLogoResponse,
    UpdateBoardPermissionsRequest,
    UpdateBoardPermissionsResponse,
)
from lib_identity.identity import require_auth
from web import get_context, get_context_with_user_info
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])
bearer_scheme = HTTPBearer(auto_error=False)


class UploadLogoRequest(BaseModel):
    image_base64: str


def require_admin(request: Request):
    context = get_context(request)
    if context.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.post("/users", response_model=CreateUserResponse, dependencies=[Depends(bearer_scheme)])
@require_auth
def create_new_user(request: Request, payload: CreateUserRequest) -> CreateUserResponse:
    context, user_code, user_type = get_context_with_user_info(request)
    require_admin(request)
    return create_user(conn=context.conn, payload=payload, created_by=user_code)


@router.get("/users", response_model=UserListResponse, dependencies=[Depends(bearer_scheme)])
@require_auth
def list_users(request: Request) -> UserListResponse:
    context = get_context(request)
    require_admin(request)
    return get_user_list(conn=context.conn)


@router.put("/users/{user_code}", response_model=UpdateUserResponse, dependencies=[Depends(bearer_scheme)])
@require_auth
def update_existing_user(request: Request, user_code: str, payload: UpdateUserRequest) -> UpdateUserResponse:
    context, admin_code, user_type = get_context_with_user_info(request)
    require_admin(request)
    return update_user(
        conn=context.conn,
        target_user_code=user_code,
        payload=payload,
        updated_by=admin_code,
    )


@router.post("/users/{user_code}/logo", response_model=UploadLogoResponse, dependencies=[Depends(bearer_scheme)])
@require_auth
def upload_logo(request: Request, user_code: str, payload: UploadLogoRequest) -> UploadLogoResponse:
    context = get_context(request)
    require_admin(request)
    return upload_school_logo(
        conn=context.conn,
        user_code=user_code,
        image_base64=payload.image_base64,
    )


@router.put("/users/{user_code}/permissions", response_model=UpdateBoardPermissionsResponse, dependencies=[Depends(bearer_scheme)])
@require_auth
def update_permissions(request: Request, user_code: str, payload: UpdateBoardPermissionsRequest) -> UpdateBoardPermissionsResponse:
    context = get_context(request)
    require_admin(request)
    return update_board_permissions(
        conn=context.conn,
        target_user_code=user_code,
        payload=payload,
    )