from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from typing import Any

import pandas as pd
import pymysql

from pit_pre.config import DatabaseConfig


class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config

    @contextmanager
    def connect(self):
        conn = pymysql.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
            charset=self.config.charset,
            autocommit=False,
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def read_frame(self, sql: str, params: Sequence[Any] | None = None) -> pd.DataFrame:
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [item[0] for item in cursor.description or []]
                rows = cursor.fetchall()
            return pd.DataFrame(list(rows), columns=columns)

    def execute_many(self, sql: str, rows: Iterable[Sequence[Any]]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, rows)
                return cursor.rowcount

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> int:
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.rowcount

    def insert_one(self, sql: str, params: Sequence[Any] | None = None) -> int:
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return int(cursor.lastrowid)
