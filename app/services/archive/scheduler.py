"""Background scheduler for archive service."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from .service import load_config, archive_once_with_handling


class ArchiveScheduler:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running:
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    async def _run_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while not self._stop_event.is_set():
            try:
                delay = await loop.run_in_executor(None, self._execute_cycle)
            except Exception:
                delay = 600
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                continue

    def _execute_cycle(self) -> int:
        delay_seconds = 3600
        session: Session = SessionLocal()
        try:
            config = load_config(session)
            interval = config.schedule_interval_seconds or 3600
            delay_seconds = max(300, interval)

            if not config.enabled:
                return delay_seconds

            processed, deleted, duration, error = archive_once_with_handling(session, config)
            session.commit()
            if error:
                # In case of error, wait longer to avoid tight loop
                return max(delay_seconds, 600)
            return delay_seconds
        finally:
            session.close()


archive_scheduler = ArchiveScheduler()

