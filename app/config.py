"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_TYPE: str = "sqlite"
    DATABASE_URL: str = "sqlite:///./ibolid.db"
    
    # Authentication
    AUTH_ENABLED: bool = True
    JWT_SECRET_KEY: str = "your-secret-key-change-this"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    APP_NAME: str = "IBolid Cloud"
    DEBUG: bool = False
    CORS_ORIGINS: str = '["http://localhost:3000"]'
    
    # Admin
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"
    
    # Performance (Uvicorn workers)
    WORKERS: int = 4  # Количество uvicorn воркеров
    WORKER_TIMEOUT: int = 120  # Таймаут воркера в секундах
    
    # Stress test limits
    STRESS_TEST_MAX_WORKERS: int = 100  # Максимум воркеров в тесте
    STRESS_TEST_MAX_RPS: int = 10000   # Максимум RPS в тесте
    STRESS_TEST_MAX_DURATION: int = 600  # Максимум 10 минут
    
    # In-memory write buffer
    MEMBUFFER_ENABLED: bool = True
    MEMBUFFER_MAX_QUEUE: int = 50000
    MEMBUFFER_BATCH_SIZE: int = 200
    MEMBUFFER_FLUSH_INTERVAL_MS: int = 100
    MEMBUFFER_MAX_LATENCY_MS: int = 500
    MEMBUFFER_ON_OVERFLOW: str = "fallback"  # drop|block|fallback
    
    # SQLite tuning
    SQLITE_TUNING_WAL: bool = True

    # Database pool
    DB_POOL_SIZE: int = 50
    DB_MAX_OVERFLOW: int = 100
    DB_POOL_TIMEOUT: int = 60

    # Caching
    API_KEY_CACHE_TTL: int = 60  # seconds
    
    # Reverse proxy settings
    ROOT_PATH: str = ""  # Префикс пути для работы за реверс-прокси (например, "/cloud2")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string"""
        try:
            return json.loads(self.CORS_ORIGINS)
        except:
            return ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

