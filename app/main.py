"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models import User, Channel, Feed, ApiKey  # Import models before creating tables
from app.routers import auth, channels, feeds, web, admin, admin_archive
from app.services.auth_service import get_or_create_admin
from app.services.mem_buffer import mem_buffer
from app.services.archive.scheduler import archive_scheduler
from app.services.archive import service as archive_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Create admin user if AUTH_ENABLED
    if settings.AUTH_ENABLED:
        db = SessionLocal()
        try:
            get_or_create_admin(db)
            print(f"[OK] Admin user: {settings.ADMIN_EMAIL}")
        finally:
            db.close()
    
    print(f"[OK] Application started")
    print(f"[OK] Auth enabled: {settings.AUTH_ENABLED}")
    print(f"[OK] Database: {settings.DATABASE_TYPE}")
    
    # Start in-memory write buffer
    if settings.MEMBUFFER_ENABLED:
        import asyncio
        asyncio.create_task(mem_buffer.start())
        print("[OK] In-memory write buffer started")

    # Start archive scheduler if enabled
    db_archive = SessionLocal()
    try:
        archive_config = archive_service.load_config(db_archive)
        if archive_config.enabled:
            await archive_scheduler.start()
            print("[OK] Archive scheduler started")
    finally:
        db_archive.close()
    
    yield
    
    # Shutdown
    print("Application shutting down...")
    # Drain buffer
    if settings.MEMBUFFER_ENABLED:
        import asyncio
        await mem_buffer.drain_and_stop()

    await archive_scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Облачная платформа для IoT данных",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root path middleware (для работы за реверс-прокси)
if settings.ROOT_PATH:
    from app.middleware.root_path_middleware import RootPathMiddleware
    app.add_middleware(RootPathMiddleware)

# Request logging middleware
from app.middleware.logging_middleware import RequestLoggingMiddleware
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting middleware (optional - can be enabled/disabled)
from app.middleware.rate_limiter import RateLimitMiddleware
if not settings.DEBUG:  # Enable only in production
    app.add_middleware(RateLimitMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(channels.router)
app.include_router(feeds.router)
app.include_router(admin.router)
app.include_router(admin_archive.router)

# Import settings router (as settings_router to avoid name conflict)
from app.routers import settings as settings_router
app.include_router(settings_router.router)

# Import widgets router
from app.routers import widgets
app.include_router(widgets.router)
app.include_router(widgets.ai_router)

# Import automation router
from app.routers import automation
app.include_router(automation.router)

# Import control router (secure widget control)
from app.routers import control
app.include_router(control.router)

# Import stress test router
from app.routers import stress_test
app.include_router(stress_test.router)

app.include_router(web.router)  # Web router last to catch remaining routes


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "auth_enabled": settings.AUTH_ENABLED,
        "database": settings.DATABASE_TYPE
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

