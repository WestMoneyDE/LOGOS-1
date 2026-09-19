"""Control-plane persistence (`ros_*` tables in the lab Postgres). Fail-open to records-only: `connect()` returns None when the DB is unreachable.

The git registries remain the scientific record; nothing here holds a claim status the registry does not (spec §3). No model call.
"""
from __future__ import annotations

from typing import Any

from .migrations import MIGRATIONS, ROS_TABLES, VERSION_TABLE, ensure_schema  # noqa: F401


def dsn() -> str:
    """DATABASE_URL (host/dev) or, inside the ros-worker container, assembled from LOGOS_PG_HOST + POSTGRES_* parts (no credential-in-URL literal in compose)."""
    import os
    from urllib.parse import quote
    host = os.environ.get("LOGOS_PG_HOST")
    if host and not os.environ.get("DATABASE_URL"):
        return f"postgresql://{quote(os.environ.get('POSTGRES_USER', 'logos'))}:{quote(os.environ.get('POSTGRES_PASSWORD', ''))}@{host}:{os.environ.get('LOGOS_PG_PORT', '5432')}/{os.environ.get('POSTGRES_DB', 'logos_research')}"
    from logos_research.infra.backends import dsn_from_env
    return dsn_from_env()


def connect() -> Any | None:
    """psycopg connection (autocommit off) or None when the lab DB is down. Callers commit per unit of work."""
    try:
        import psycopg
        return psycopg.connect(dsn(), autocommit=False, connect_timeout=3)
    except Exception:
        return None


def status() -> dict:
    conn = connect()
    if conn is None:
        return {"db": "unreachable", "records_only": True, "schema_version": None}
    try:
        v = ensure_schema(conn)
        return {"db": "ok", "records_only": False, "schema_version": v}
    finally:
        conn.close()
