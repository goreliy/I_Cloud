"""Archive backends for SQLite and PostgreSQL."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


ARCHIVE_COLUMNS = [
    "id",
    "channel_id",
    "entry_id",
    "created_at",
    "field1",
    "field2",
    "field3",
    "field4",
    "field5",
    "field6",
    "field7",
    "field8",
    "latitude",
    "longitude",
    "elevation",
    "status",
]


class ArchiveBackend:
    """Base class for archive backend implementations."""

    def test_connection(self) -> None:
        raise NotImplementedError

    def init_schema(self) -> None:
        raise NotImplementedError

    def archive_batch(self, rows: Iterable[dict]) -> int:
        raise NotImplementedError

    def read_all(self, batch_size: int = 1000, offset: int = 0) -> Iterable[list[dict]]:
        """Read all archived records in batches.
        
        Args:
            batch_size: Number of records per batch
            offset: Starting offset for reading
            
        Yields:
            Lists of dictionaries representing archive records
        """
        raise NotImplementedError

    def count_records(self) -> int:
        """Get total count of archived records."""
        raise NotImplementedError


class SQLiteArchiveBackend(ArchiveBackend):
    def __init__(self, file_path: str):
        if not file_path:
            raise ValueError("SQLite file path is required")
        self.file_path = file_path
        self.engine: Engine = create_engine(
            f"sqlite:///{file_path}",
            connect_args={"check_same_thread": False}
        )

    def test_connection(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    def init_schema(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS feeds_archive (
            id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            entry_id INTEGER NOT NULL,
            created_at DATETIME,
            field1 REAL,
            field2 REAL,
            field3 REAL,
            field4 REAL,
            field5 REAL,
            field6 REAL,
            field7 REAL,
            field8 REAL,
            latitude REAL,
            longitude REAL,
            elevation REAL,
            status TEXT,
            archived_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        idx_sql = """
        CREATE INDEX IF NOT EXISTS idx_feeds_archive_channel_created
        ON feeds_archive(channel_id, created_at);
        """
        with self.engine.begin() as conn:
            conn.execute(text(sql))
            conn.execute(text(idx_sql))

    def archive_batch(self, rows: Iterable[dict]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        placeholders = ",".join([f":{col}" for col in ARCHIVE_COLUMNS])
        sql = f"INSERT OR IGNORE INTO feeds_archive ({','.join(ARCHIVE_COLUMNS)}) VALUES ({placeholders})"
        rows_with_defaults = []
        for row in rows:
            data = {col: row.get(col) for col in ARCHIVE_COLUMNS}
            rows_with_defaults.append(data)
        with self.engine.begin() as conn:
            conn.execute(text(sql), rows_with_defaults)
        return len(rows)

    def read_all(self, batch_size: int = 1000, offset: int = 0) -> Iterable[list[dict]]:
        """Read all archived records in batches."""
        columns = ','.join(ARCHIVE_COLUMNS)
        sql = f"SELECT {columns} FROM feeds_archive ORDER BY id LIMIT :limit OFFSET :offset"
        
        current_offset = offset
        while True:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), {"limit": batch_size, "offset": current_offset})
                rows = []
                for row in result:
                    row_dict = {col: row[i] for i, col in enumerate(ARCHIVE_COLUMNS)}
                    rows.append(row_dict)
                
                if not rows:
                    break
                
                yield rows
                current_offset += len(rows)
                
                if len(rows) < batch_size:
                    break

    def count_records(self) -> int:
        """Get total count of archived records."""
        sql = "SELECT COUNT(*) as cnt FROM feeds_archive"
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            row = result.fetchone()
            return int(row[0]) if row else 0


class PostgresArchiveBackend(ArchiveBackend):
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        schema: str | None = None,
        ssl: bool = False,
    ):
        if not all([host, port, database, user]):
            raise ValueError("PostgreSQL configuration is incomplete")
        ssl_part = "?sslmode=require" if ssl else ""
        self.schema = schema or "public"
        self.engine: Engine = create_engine(
            f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}{ssl_part}"
        )

    def test_connection(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    def init_schema(self) -> None:
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.schema}.feeds_archive (
            id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            entry_id INTEGER NOT NULL,
            created_at TIMESTAMPTZ,
            field1 DOUBLE PRECISION,
            field2 DOUBLE PRECISION,
            field3 DOUBLE PRECISION,
            field4 DOUBLE PRECISION,
            field5 DOUBLE PRECISION,
            field6 DOUBLE PRECISION,
            field7 DOUBLE PRECISION,
            field8 DOUBLE PRECISION,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            elevation DOUBLE PRECISION,
            status TEXT,
            archived_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        index_sql = f"""
        CREATE INDEX IF NOT EXISTS idx_feeds_archive_channel_created
        ON {self.schema}.feeds_archive(channel_id, created_at);
        """
        with self.engine.begin() as conn:
            conn.execute(text(f"SET search_path TO {self.schema}"))
            conn.execute(text(create_sql))
            conn.execute(text(index_sql))

    def archive_batch(self, rows: Iterable[dict]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        columns = ','.join(ARCHIVE_COLUMNS)
        values = ','.join([f":{col}" for col in ARCHIVE_COLUMNS])
        sql = text(
            f"INSERT INTO {self.schema}.feeds_archive ({columns}) "
            f"VALUES ({values}) ON CONFLICT (id) DO NOTHING"
        )
        payload = [{col: row.get(col) for col in ARCHIVE_COLUMNS} for row in rows]
        with self.engine.begin() as conn:
            conn.execute(sql, payload)
        return len(rows)

    def read_all(self, batch_size: int = 1000, offset: int = 0) -> Iterable[list[dict]]:
        """Read all archived records in batches."""
        columns = ','.join(ARCHIVE_COLUMNS)
        sql = text(
            f"SELECT {columns} FROM {self.schema}.feeds_archive "
            f"ORDER BY id LIMIT :limit OFFSET :offset"
        )
        
        current_offset = offset
        while True:
            with self.engine.connect() as conn:
                conn.execute(text(f"SET search_path TO {self.schema}"))
                result = conn.execute(sql, {"limit": batch_size, "offset": current_offset})
                rows = []
                for row in result:
                    row_dict = {col: row[i] for i, col in enumerate(ARCHIVE_COLUMNS)}
                    rows.append(row_dict)
                
                if not rows:
                    break
                
                yield rows
                current_offset += len(rows)
                
                if len(rows) < batch_size:
                    break

    def count_records(self) -> int:
        """Get total count of archived records."""
        sql = text(f"SELECT COUNT(*) as cnt FROM {self.schema}.feeds_archive")
        with self.engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {self.schema}"))
            result = conn.execute(sql)
            row = result.fetchone()
            return int(row[0]) if row else 0

