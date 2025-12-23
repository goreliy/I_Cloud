"""Run the application"""
import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.APP_NAME}...")
    print(f"Auth enabled: {settings.AUTH_ENABLED}")
    print(f"Database: {settings.DATABASE_TYPE}")
    print(f"Debug mode: {settings.DEBUG}")
    print(f"Workers: {settings.WORKERS}")
    print("\nServer will be available at: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs\n")
    
    # В debug режиме используем 1 воркер с reload, иначе - settings.WORKERS
    uvicorn_config = {
        "app": "app.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "timeout_keep_alive": settings.WORKER_TIMEOUT,
    }
    
    # Настройка root_path для работы за реверс-прокси
    if settings.ROOT_PATH:
        uvicorn_config["root_path"] = settings.ROOT_PATH
    
    if settings.DEBUG:
        uvicorn_config["reload"] = True
        uvicorn.run(**uvicorn_config)
    else:
        uvicorn_config["workers"] = settings.WORKERS
        uvicorn.run(**uvicorn_config)

