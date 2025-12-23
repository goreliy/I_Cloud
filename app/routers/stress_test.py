"""Stress test API endpoints for admin panel"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime
import subprocess
import json
import asyncio
import os

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.stress_test import StressTestRun
from app.models.channel import Channel
from app.config import settings

router = APIRouter(prefix="/api/admin/stress-test", tags=["stress-test"])


class StressTestConfig(BaseModel):
    """Конфигурация стресс-теста"""
    channel_id: int
    workers: int
    rps: int
    duration: int
    
    @validator('workers')
    def validate_workers(cls, v):
        if not 1 <= v <= settings.STRESS_TEST_MAX_WORKERS:
            raise ValueError(f'workers must be between 1 and {settings.STRESS_TEST_MAX_WORKERS}')
        return v
    
    @validator('rps')
    def validate_rps(cls, v):
        if not 1 <= v <= settings.STRESS_TEST_MAX_RPS:
            raise ValueError(f'rps must be between 1 and {settings.STRESS_TEST_MAX_RPS}')
        return v
    
    @validator('duration')
    def validate_duration(cls, v):
        if not 1 <= v <= settings.STRESS_TEST_MAX_DURATION:
            raise ValueError(f'duration must be between 1 and {settings.STRESS_TEST_MAX_DURATION} seconds')
        return v


class StressTestResponse(BaseModel):
    """Ответ с информацией о тесте"""
    id: int
    channel_id: int
    workers: int
    target_rps: int
    duration: int
    total_requests: Optional[int]
    successful_requests: Optional[int]
    failed_requests: Optional[int]
    actual_rps: Optional[float]
    avg_latency_ms: Optional[float]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


async def run_stress_test_subprocess(test_id: int, config: StressTestConfig, db: Session):
    """Запустить стресс-тест в отдельном процессе"""
    test_run = db.query(StressTestRun).filter(StressTestRun.id == test_id).first()
    if not test_run:
        return
    
    # Обновить статус
    test_run.status = 'running'
    db.commit()
    
    try:
        # Получить API ключ канала
        from app.services import channel_service
        channel = channel_service.get_channel(db, config.channel_id)
        if not channel:
            raise Exception(f"Channel {config.channel_id} not found")
        
        api_keys = channel_service.get_channel_api_keys(db, config.channel_id)
        write_key = next((k for k in api_keys if k.type == "write" and k.is_active), None)
        
        if not write_key:
            raise Exception("No active write API key found")
        
        # Запустить скрипт стресс-теста
        result = subprocess.run(
            [
                sys.executable,  # Python interpreter
                'tests/stress_test.py',
                '--url', 'http://localhost:8000',
                '--channel', str(config.channel_id),
                '--api-key', write_key.key,
                '--workers', str(config.workers),
                '--rps', str(config.rps),
                '--duration', str(config.duration)
            ],
            capture_output=True,
            text=True,
            timeout=config.duration + 60  # Дополнительно 60 секунд для завершения
        )
        
        # Найти JSON файл с результатами
        import glob
        json_files = glob.glob('stress_test_*.json')
        if json_files:
            # Взять последний созданный файл
            latest_file = max(json_files, key=os.path.getctime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Обновить запись в БД
            test_run.status = 'completed'
            test_run.completed_at = datetime.now()
            test_run.total_requests = results['results']['total']
            test_run.successful_requests = results['results']['success']
            test_run.failed_requests = results['results']['failed']
            test_run.actual_rps = results['results']['actual_rps']
            test_run.avg_latency_ms = results['results']['avg_latency_ms']
            test_run.min_latency_ms = results['results'].get('min_latency_ms')
            test_run.max_latency_ms = results['results'].get('max_latency_ms')
            test_run.p95_latency_ms = results['results'].get('p95_latency_ms')
            test_run.results_json = json.dumps(results, ensure_ascii=False)
            
            # Удалить временный JSON файл
            os.remove(latest_file)
        else:
            raise Exception("Results file not found")
        
        db.commit()
        
    except subprocess.TimeoutExpired:
        test_run.status = 'failed'
        test_run.completed_at = datetime.now()
        test_run.error_message = 'Test timeout'
        db.commit()
    except Exception as e:
        test_run.status = 'failed'
        test_run.completed_at = datetime.now()
        test_run.error_message = str(e)
        db.commit()


@router.post("/start", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def start_stress_test(
    test_config: StressTestConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Запустить стресс-тест (только для админов)
    Тест запускается в фоне
    """
    # Проверка прав админа
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can run stress tests"
        )
    
    # Проверить, что канал существует
    channel = db.query(Channel).filter(Channel.id == test_config.channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel {test_config.channel_id} not found"
        )
    
    # Проверить, нет ли уже запущенного теста
    running_test = db.query(StressTestRun).filter(
        StressTestRun.status == 'running'
    ).first()
    
    if running_test:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Test #{running_test.id} is already running. Wait for completion."
        )
    
    # Создать запись в БД
    test_run = StressTestRun(
        channel_id=test_config.channel_id,
        workers=test_config.workers,
        target_rps=test_config.rps,
        duration=test_config.duration,
        status='pending'
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)
    
    # Запустить в фоне
    background_tasks.add_task(run_stress_test_subprocess, test_run.id, test_config, db)
    
    return {
        "test_id": test_run.id,
        "status": "started",
        "message": f"Stress test #{test_run.id} started in background"
    }


@router.get("/{test_id}", response_model=StressTestResponse)
async def get_stress_test_status(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить статус конкретного теста"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    
    test_run = db.query(StressTestRun).filter(StressTestRun.id == test_id).first()
    if not test_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    return test_run


@router.get("/history/list", response_model=List[StressTestResponse])
async def get_stress_test_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить историю тестов"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    
    tests = db.query(StressTestRun).order_by(
        StressTestRun.started_at.desc()
    ).limit(min(limit, 100)).all()
    
    return tests


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stress_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить запись о тесте"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    
    test_run = db.query(StressTestRun).filter(StressTestRun.id == test_id).first()
    if not test_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    
    if test_run.status == 'running':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running test"
        )
    
    db.delete(test_run)
    db.commit()


import sys















