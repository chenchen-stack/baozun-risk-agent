"""环境变量说明见 integrations/datasources/README.txt（与 .env.example 同步）。"""

from __future__ import annotations

import json
import os
from typing import Any


def procurement_source_mode() -> str:
    return (os.getenv("PROCUREMENT_DATA_SOURCE", "") or "mock").strip().lower()


def procurement_merge_mode() -> str:
    """merge：与内置 Mock 叠加；replace：清空 PROCUREMENT_DB 后仅保留外部数据（慎用）。"""
    return (os.getenv("PROCUREMENT_MERGE_MODE", "") or "merge").strip().lower()


def rest_base_url() -> str:
    return os.getenv("PROCUREMENT_REST_BASE_URL", "").strip().rstrip("/")


def rest_list_path() -> str:
    return os.getenv("PROCUREMENT_REST_LIST_PATH", "/api/v1/purchase-orders").strip() or "/api/v1/purchase-orders"


def rest_timeout_sec() -> float:
    try:
        return float(os.getenv("PROCUREMENT_REST_TIMEOUT", "30"))
    except ValueError:
        return 30.0


def rest_extra_headers() -> dict[str, str]:
    raw = os.getenv("PROCUREMENT_REST_HEADERS_JSON", "").strip()
    if not raw:
        return {}
    try:
        h = json.loads(raw)
        return {str(k): str(v) for k, v in h.items()} if isinstance(h, dict) else {}
    except json.JSONDecodeError:
        return {}


def selectdb_dsn() -> str:
    return os.getenv("SELECTDB_MYSQL_DSN", "").strip()


def selectdb_sql() -> str:
    q = os.getenv("SELECTDB_PROCUREMENT_SQL", "").strip()
    if q:
        return q
    return (
        "SELECT po_number, title, category, department, applicant, supplier, supplier_id, "
        "amount, apply_date, status, has_purchase_request, pr_number, budget_code, budget_total, budget_used "
        "FROM vw_risk_procurement_po"
    )


def reload_admin_token() -> str:
    return os.getenv("DATASOURCE_RELOAD_TOKEN", "").strip()
