"""从采购 REST 列表接口拉取数据（GET）。"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from integrations.datasources.config import rest_base_url, rest_extra_headers, rest_list_path, rest_timeout_sec
from integrations.datasources.mapper import rest_item_to_po_record

logger = logging.getLogger(__name__)


def fetch_procurement_items_from_rest() -> tuple[list[dict[str, Any]], str]:
    base = rest_base_url()
    if not base:
        return [], "PROCUREMENT_REST_BASE_URL empty"
    path = rest_list_path()
    if not path.startswith("/"):
        path = "/" + path
    url = base + path
    headers = {"Accept": "application/json", **rest_extra_headers()}
    try:
        # 避免系统 HTTP(S)_PROXY 把 127.0.0.1 走公司网关导致 502
        with httpx.Client(timeout=rest_timeout_sec(), trust_env=False) as client:
            r = client.get(url, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.exception("procurement REST fetch failed")
        return [], str(e)

    items: list[Any]
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = (
            data.get("items")
            or data.get("data")
            or data.get("records")
            or data.get("list")
            or data.get("rows")
            or []
        )
        if not isinstance(items, list):
            items = []
    else:
        items = []

    out: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        rec = rest_item_to_po_record(it)
        if rec:
            out.append(rec)
    return out, ""
