from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.admin_router import router as admin_router
from api.chat_router import limiter as chat_limiter
from api.chat_router import router as chat_router
from core import settings
from dotenv import load_dotenv
import os

load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title="Portfolio RAG Chatbot", version="1.0.0")

    origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # slowapi rate-limit handler
    app.state.limiter = chat_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(chat_router)
    app.include_router(admin_router)

    @app.get("/health")
    async def health(_: Request) -> dict:
        return {"ok": True}

    return app


app = create_app()
