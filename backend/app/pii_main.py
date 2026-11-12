import asyncio
import contextlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .intpii_routes import purge_expired_sessions, router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def cleanup():
        while True:
            await asyncio.sleep(60)
            purge_expired_sessions()

    task = asyncio.create_task(cleanup())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="int-pii API", lifespan=lifespan)
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5188,https://frontend-beta-seven-50.vercel.app")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
    expose_headers=["Content-Disposition"],
)
app.include_router(router)
