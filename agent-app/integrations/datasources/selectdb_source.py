"""SelectDB / MySQL 兼容协议：只读查询采购视图（需 pymysql）。"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import unquote, urlparse

from integrations.datasources.config import selectdb_dsn, selectdb_sql
from integrations.datasources.mapper import sql_row_to_po_record

logger = logging.getLogger(__name__)


def _parse_mysql_dsn(dsn: str) -> dict[str, Any]:
    """支持 mysql:// 或 mysql+pymysql://user:pass@host:9030/db?charset=utf8mb4"""
    u = urlparse(dsn.replace("mysql+pymysql://", "mysql://", 1))
    if u.scheme not in ("mysql", "mysql2"):
        raise ValueError("DSN scheme must be mysql:// or mysql+pymysql://")
    host = u.hostname or "127.0.0.1"
    port = u.port or 3306
    user = unquote(u.username or "")
    password = unquote(u.password or "")
    database = (u.path or "").lstrip("/") or None
    return {"host": host, "port": port, "user": user, "password": password, "database": database}


def _validate_readonly_sql(sql: str) -> None:
    s = sql.strip().lower()
    if not s.startswith("select"):
        raise ValueError("仅允许 SELECT（只读）")
    if re.search(r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke)\b", s):
        raise ValueError("SQL 含非只读关键字")


def fetch_procurement_rows_from_selectdb() -> tuple[list[dict[str, Any]], str]:
    dsn = selectdb_dsn()
    if not dsn:
        return [], "SELECTDB_MYSQL_DSN empty"
    sql = selectdb_sql()
    try:
        _validate_readonly_sql(sql)
    except ValueError as e:
        return [], str(e)
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError:
        return [], "缺少依赖 pymysql，请 pip install pymysql"

    try:
        kw = _parse_mysql_dsn(dsn)
        conn = pymysql.connect(
            host=kw["host"],
            port=int(kw["port"]),
            user=kw["user"],
            password=kw["password"],
            database=kw["database"],
            charset="utf8mb4",
            cursorclass=DictCursor,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        logger.exception("selectdb fetch failed")
        return [], str(e)

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rec = sql_row_to_po_record(row)
        if rec:
            out.append(rec)
    return out, ""
