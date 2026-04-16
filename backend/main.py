from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import backend.models  # noqa: F401 - register all models
from backend.api.v1 import router as api_v1_router
from backend.config import apply_db_settings, settings
from backend.database import Base, engine

# Thư mục serve audio files
_AUDIO_DIR = Path(__file__).resolve().parent / "static" / "audio"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables (chỉ chạy khi không phải production)
    if not settings.is_production:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Nạp platform credentials từ DB vào settings singleton
    await apply_db_settings()

    # Khởi tạo Gemini Vision engine
    from backend.ai_engine.gemini_engine import create_gemini_engine

    app.state.gemini = create_gemini_engine()
    await app.state.gemini.initialize()

    # Khởi tạo ElevenLabs Audio engine
    from backend.ai_engine.elevenlabs_engine import create_elevenlabs_engine

    app.state.elevenlabs = create_elevenlabs_engine()
    await app.state.elevenlabs.initialize()

    # Khởi tạo HeyGen Video engine
    from backend.ai_engine.heygen_engine import create_heygen_engine

    app.state.heygen = create_heygen_engine()
    await app.state.heygen.initialize()

    # Khởi động Automation Scheduler
    from backend.affiliate.scheduler import start_scheduler, stop_scheduler

    await start_scheduler()

    yield

    # Shutdown
    await stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title="Affiliate Marketing Automation",
    description="AI-powered affiliate marketing automation for Vietnamese e-commerce platforms",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve audio files tại /static/audio/{filename}.mp3
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/audio", StaticFiles(directory=str(_AUDIO_DIR)), name="audio")

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}
