import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# from app_educare.views.urls import router as educare_router
from app_identity.identity import router as identity_router
from app_exam_maker.test_maker import router as testmaker_router
from incident_middleware import IncidentRecordMiddleware
from logger import get_logger
from web import Context

app = FastAPI(debug=True)
logger = get_logger(__name__)

ALLOWED_ORIGINS = [
    # dev if you actually use it:
    "http://localhost:3060",
    "http://127.0.0.1:3060",
    "http://localhost:3061",
    "http://127.0.0.1:3061",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
    # production
    "https://papercraft-frontend.vercel.app",
    "https://papercraft.pk",
    "https://www.papercraft.pk",
]

# Allow any localhost/lan origin (Expo web / device tunnels) without enumerating every port.
LOCAL_ORIGIN_REGEX = (
    r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$"
)

allow_all = os.getenv("EDUCARE_ALLOW_ALL_ORIGINS", "false").lower() in {
    "1",
    "true",
    "yes",
    "1"
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else ALLOWED_ORIGINS,
    allow_origin_regex=None if allow_all else LOCAL_ORIGIN_REGEX,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],  # requires Authorization for user token fetches
)

# app.add_middleware(IncidentRecordMiddleware)
app.add_middleware(Context)

app.include_router(identity_router)
app.include_router(testmaker_router)


@app.middleware("http")
async def log_unhandled_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:  # pragma: no cover - Diagnostics middleware
        logger.exception(
            "Unhandled exception during request: %s %s",
            request.method,
            request.url.path,
        )
        raise


@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url="/docs")
