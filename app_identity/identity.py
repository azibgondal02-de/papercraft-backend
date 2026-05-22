from fastapi import APIRouter, HTTPException, Request, status, Depends
from fastapi.security import HTTPBearer

from lib_identity.identity import (
    InvalidCredentialsError,
    SessionCreationError,
    TokenValidationError,
    check_username,
    get_user_profile,
    login_user,
    logout_user,
    require_auth,
    reset_password,
    update_user_profile,
    validate_session_token,
)
from lib_identity.models.identity import (
    CreateResetPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    ResetPasswordResponse,
    TokenValidationRequest,
    TokenValidationResponse,
    UpdateUserProfileRequest,
    UpdateUserProfileResponse,
    UserProfileResponse,
    UsernameExistsResponse,
)
from web import get_context, get_context_with_user_info

router = APIRouter(prefix="/identity", tags=["identity"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse, response_model_exclude_none=True)
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    print("hello")
    context = get_context(request)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    try:
        return login_user(
            context.conn,
            payload.username,
            payload.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials",
        ) from exc
    except SessionCreationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create session",
        ) from exc


@router.post("/logout", dependencies=[Depends(bearer_scheme)])
def logout(request: Request) -> LogoutResponse:
    context = get_context(request)
    logout_user(context.conn, request=request)
    return LogoutResponse(message="User Logout Successfully")


@router.post(
    "/token/validate",
    dependencies=[Depends(bearer_scheme)],
    response_model=TokenValidationResponse,
)
def validate_token(payload: TokenValidationRequest, request: Request) -> TokenValidationResponse:
    context = get_context(request)
    try:
        return validate_session_token(context.conn, payload.token)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to validate token",
        ) from exc


@require_auth
@router.get("/username-exists/{username}", dependencies=[Depends(bearer_scheme)])
def check(request: Request, username: str) -> UsernameExistsResponse:
    context = get_context(request)
    return check_username(conn=context.conn, username=username)


@require_auth
@router.post("/reset-password", dependencies=[Depends(bearer_scheme)])
def change_password(request: Request, payload: CreateResetPasswordRequest) -> ResetPasswordResponse:
    context = get_context(request)
    return reset_password(conn=context.conn, user_code=context.user_code, payload=payload)


@router.get("/profile", dependencies=[Depends(bearer_scheme)], response_model=UserProfileResponse)
@require_auth
def get_profile(request: Request) -> UserProfileResponse:
    context, user_code, user_type = get_context_with_user_info(request)
    return get_user_profile(conn=context.conn, user_code=user_code)


@router.put("/profile", dependencies=[Depends(bearer_scheme)], response_model=UpdateUserProfileResponse)
@require_auth
def update_profile(request: Request, payload: UpdateUserProfileRequest) -> UpdateUserProfileResponse:
    context, user_code, user_type = get_context_with_user_info(request)
    return update_user_profile(conn=context.conn, user_code=user_code, payload=payload)