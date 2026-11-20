import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, officials, users, problems, schemes, scheme_list, dashboard, biometric_router, locations_router
from app.migrate_schema import run_lightweight_migrations
from app.seed_schemes import seed_scheme_master


def init_database():
    Base.metadata.create_all(bind=engine)
    run_lightweight_migrations(engine)
    # Load/refresh the master scheme catalog on startup.
    with SessionLocal() as db:
        seed_scheme_master(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Retry a few times in case the database is waking up (Neon scales to zero when idle)
    for attempt in range(1, 6):
        try:
            init_database()
            print("[startup] Database ready")
            break
        except Exception as e:
            print(f"[startup] DB init failed (attempt {attempt}/5): {e}")
            time.sleep(4)
    else:
        print("[startup] Database still unreachable; app started without DB init")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Sugam Seva - a digital citizen assistant "
                 "for Government of India services and schemes.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sugamseva-govt.netlify.app"],  # tighten this to your dashboard's origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(officials.router)
app.include_router(users.router)
app.include_router(users.documents_router)
app.include_router(problems.router)
app.include_router(schemes.router)
app.include_router(scheme_list.router)
app.include_router(dashboard.router)
app.include_router(biometric_router.router)
app.include_router(locations_router.router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "demo_mode": settings.DEMO_MODE,
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
