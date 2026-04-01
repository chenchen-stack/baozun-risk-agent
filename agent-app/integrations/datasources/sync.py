"""按 PROCUREMENT_DATA_SOURCE 将外部采购数据写入 agent.PROCUREMENT_DB。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from integrations.datasources import config as ds_config
from integrations.datasources.rest_source import fetch_procurement_items_from_rest
from integrations.datasources.selectdb_source import fetch_procurement_rows_from_selectdb

logger = logging.getLogger(__name__)

_LAST: dict[str, Any] = {
    "mode": "mock",
    "ok": True,
    "error": "",
    "merged_count": 0,
    "at": "",
}


def get_procurement_sync_status() -> dict[str, Any]:
    return dict(_LAST)


def sync_procurement_into_agent(agent_module: Any) -> dict[str, Any]:
    """在 external_data overlay 之后调用；根据模式合并或替换 PROCUREMENT_DB。"""
    mode = ds_config.procurement_source_mode()
    _LAST["mode"] = mode
    _LAST["at"] = datetime.now(timezone.utc).isoformat()
    if mode in ("mock", "", "none"):
        _LAST["ok"] = True
        _LAST["error"] = ""
        _LAST["merged_count"] = 0
        return _LAST

    if mode == "http_rest":
        rows, err = fetch_procurement_items_from_rest()
    elif mode in ("selectdb", "selectdb_mysql", "mysql"):
        rows, err = fetch_procurement_rows_from_selectdb()
    else:
        _LAST["ok"] = False
        _LAST["error"] = f"unknown PROCUREMENT_DATA_SOURCE: {mode}"
        _LAST["merged_count"] = 0
        return _LAST

    if err:
        _LAST["ok"] = False
        _LAST["error"] = err
        _LAST["merged_count"] = 0
        logger.error("procurement sync failed: %s", err)
        return _LAST

    db = getattr(agent_module, "PROCUREMENT_DB", None)
    if not isinstance(db, dict):
        _LAST["ok"] = False
        _LAST["error"] = "agent.PROCUREMENT_DB missing"
        return _LAST

    merge_mode = ds_config.procurement_merge_mode()
    if merge_mode == "replace":
        db.clear()

    n = 0
    for rec in rows:
        key = rec.get("po_number")
        if not key:
            continue
        db[key] = rec
        n += 1

    _LAST["ok"] = True
    _LAST["error"] = ""
    _LAST["merged_count"] = n
    logger.info("procurement sync mode=%s merged=%s total_keys=%s", mode, n, len(db))
    return _LAST
