"""In-memory write buffer for fast /update writes with batch flush to DB"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.services import feed_service, channel_service
from app.services.automation_service import automation_engine
from app.schemas.feed import FeedCreate


@dataclass
class FeedSpec:
    channel_id: int
    fields: Dict[str, Optional[float]]
    latitude: Optional[float]
    longitude: Optional[float]
    elevation: Optional[float]
    status: Optional[str]
    received_ts_ms: int


class MemWriteBuffer:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[FeedSpec] = asyncio.Queue(maxsize=max(1, settings.MEMBUFFER_MAX_QUEUE))
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        # metrics
        self._batches_total: int = 0
        self._flush_errors: int = 0
        self._drops_total: int = 0
        self._last_flush_ms: float = 0.0

    def stats(self) -> Dict[str, Any]:
        oldest_age = 0
        try:
            # can't peek queue; estimate by last flush interval
            oldest_age = int(self._last_flush_ms)
        except Exception:
            oldest_age = 0
        return {
            "queue_size": self._queue.qsize(),
            "batches_total": self._batches_total,
            "flush_errors": self._flush_errors,
            "drops_total": self._drops_total,
            "last_flush_ms": self._last_flush_ms,
        }

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            await self._task
            self._task = None

    async def drain_and_stop(self) -> None:
        self._running = False
        # drain remaining
        await self._flush_batch(flush_all=True)
        if self._task:
            await self._task
            self._task = None

    def enqueue(self, spec: FeedSpec) -> bool:
        if self._queue.full():
            mode = (settings.MEMBUFFER_ON_OVERFLOW or "fallback").lower()
            if mode == "drop":
                self._drops_total += 1
                return False
            elif mode == "block":
                # blocking put (caller must await), but to keep /update fast we return False to fallback
                return False
            else:
                # fallback mode — caller will do direct write
                return False
        try:
            self._queue.put_nowait(spec)
            return True
        except asyncio.QueueFull:
            self._drops_total += 1
            return False

    async def _flush_loop(self) -> None:
        interval = max(1, settings.MEMBUFFER_FLUSH_INTERVAL_MS) / 1000.0
        while self._running:
            await asyncio.sleep(interval)
            await self._flush_batch()

    async def _flush_batch(self, flush_all: bool = False) -> None:
        start = time.time()
        batch: List[FeedSpec] = []
        try:
            limit = max(1, settings.MEMBUFFER_BATCH_SIZE)
            # non-blocking drain up to limit (or all)
            while (flush_all or len(batch) < limit) and not self._queue.empty():
                try:
                    spec = self._queue.get_nowait()
                    batch.append(spec)
                except asyncio.QueueEmpty:
                    break
            if not batch:
                self._last_flush_ms = (time.time() - start) * 1000.0
                return

            db: Session = SessionLocal()
            try:
                # batch transaction
                for spec in batch:
                    channel = channel_service.get_channel(db, spec.channel_id)
                    if not channel:
                        continue
                    feed = feed_service.create_feed(
                        db=db,
                        channel=channel,
                        feed_data=FeedCreate(
                            field1=spec.fields.get("field1"),
                            field2=spec.fields.get("field2"),
                            field3=spec.fields.get("field3"),
                            field4=spec.fields.get("field4"),
                            field5=spec.fields.get("field5"),
                            field6=spec.fields.get("field6"),
                            field7=spec.fields.get("field7"),
                            field8=spec.fields.get("field8"),
                            latitude=spec.latitude,
                            longitude=spec.longitude,
                            elevation=spec.elevation,
                            status=spec.status,
                        ),
                        auto_commit=False,
                    )
                    # apply automation rules before commit (same as /update)
                    automation_engine.execute_rules(channel.id, feed, db)
                db.commit()
                self._batches_total += 1
            except Exception:
                db.rollback()
                self._flush_errors += 1
            finally:
                db.close()
        finally:
            self._last_flush_ms = (time.time() - start) * 1000.0


# Singleton buffer instance
mem_buffer = MemWriteBuffer()


