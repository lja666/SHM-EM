#!/usr/bin/env python3
"""Authorized Phase 1A.1 backfill for isolated reproduction databases only."""

from __future__ import annotations

import argparse
import json
import os
import re

import pymysql

from persisted_integrity_reference import recompute_batch


class Database:
    def __init__(self, connection):
        self.connection = connection

    def all(self, sql, params=()):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())

    def execute(self, sql, params=()):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
        self.connection.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Phase 1A.1 persisted forecast integrity metadata")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default=os.environ.get("DB_ADMIN_PASSWORD"))
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    if not args.password:
        parser.error("Set DB_ADMIN_PASSWORD; credentials are never written to evidence")
    if not re.fullmatch(r"shm_em_reproduce_phase1a1_[A-Za-z0-9_]+", args.database):
        parser.error("Backfill is restricted to shm_em_reproduce_phase1a1_* databases")

    connection = pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=args.password,
        database=args.database, charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    try:
        db = Database(connection)
        batches = db.all("SELECT id FROM em_prediction_batch WHERE status='success' ORDER BY id")
        reports = [recompute_batch(db, int(row["id"])) for row in batches]
        print(json.dumps({"database": args.database, "batches": reports}, indent=2))
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
