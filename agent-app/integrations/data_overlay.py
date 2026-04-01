"""启动时合并 external_data/*.json 到内存模拟库，便于无 API 时的过渡接入（F01 过渡方案）。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 文件名 → agent 模块中的 dict 属性名
_OVERLAY_MAP = {
    "procurement.json": "PROCUREMENT_DB",
    "contract.json": "CONTRACT_DB",
    "payment.json": "PAYMENT_DB",
    "acceptance.json": "ACCEPTANCE_DB",
    "invoice.json": "INVOICE_DB",
}


def _merge_db(target: dict[Any, Any], patch: dict[Any, Any], name: str) -> int:
    if not isinstance(patch, dict):
        logger.warning("external_data overlay %s: root must be object", name)
        return 0
    n = 0
    for k, v in patch.items():
        if isinstance(v, dict):
            target[k] = v
            n += 1
        else:
            logger.warning("external_data overlay %s: skip key %s (not object)", name, k)
    return n


def apply_startup_data_overlays(base_dir: Path, agent_module: Any) -> dict[str, int]:
    """将 base_dir/external_data/<name>.json 合并进 agent 内存库（按主键覆盖/新增）。"""
    root = base_dir / "external_data"
    counts: dict[str, int] = {}
    if not root.is_dir():
        return counts
    for fname, attr in _OVERLAY_MAP.items():
        path = root / fname
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("failed to read %s: %s", path, e)
            continue
        db = getattr(agent_module, attr, None)
        if not isinstance(db, dict):
            continue
        n = _merge_db(db, data, fname)
        counts[fname] = n
        if n:
            logger.info("external_data merged %s → %s records into %s", fname, n, attr)

    # 可选：从 HTTP 拉取单文件（启动时一次）
    import os

    url = os.getenv("EXTERNAL_DATA_BOOTSTRAP_URL", "").strip()
    if url:
        try:
            import httpx

            r = httpx.get(url, timeout=30.0)
            r.raise_for_status()
            bundle = r.json()
            if isinstance(bundle, dict):
                for fname, attr in _OVERLAY_MAP.items():
                    if fname not in bundle:
                        continue
                    db = getattr(agent_module, attr, None)
                    if isinstance(db, dict) and isinstance(bundle[fname], dict):
                        n = _merge_db(db, bundle[fname], fname + "@url")
                        counts[fname + "@url"] = n
        except Exception as e:
            logger.error("EXTERNAL_DATA_BOOTSTRAP_URL fetch failed: %s", e)

    return counts
