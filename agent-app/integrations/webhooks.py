"""飞书群机器人 / 通用 OA Webhook（POST JSON）。未配置 URL 时不发起网络请求。"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _feishu_text_payload(title: str, body: str) -> dict[str, Any]:
    text = f"{title}\n{body}" if title else body
    return {"msg_type": "text", "content": {"text": text[:8000]}}


def deliver_feishu_text(webhook_url: str, title: str, body: str) -> tuple[bool, str]:
    url = (webhook_url or "").strip()
    if not url:
        return False, "skipped_no_url"
    try:
        import httpx

        r = httpx.post(url, json=_feishu_text_payload(title, body), timeout=15.0)
        if r.status_code >= 400:
            return False, f"http_{r.status_code}:{r.text[:200]}"
        try:
            data = r.json()
        except Exception:
            return True, "ok_no_json"
        if isinstance(data, dict) and data.get("code") not in (0, None):
            return False, f"feishu_api:{data}"
        return True, "ok"
    except Exception as e:
        logger.exception("feishu webhook")
        return False, str(e)


def deliver_oa_webhook(webhook_url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    url = (webhook_url or "").strip()
    if not url:
        return False, "skipped_no_url"
    try:
        import httpx

        r = httpx.post(url, json=payload, timeout=15.0)
        if r.status_code >= 400:
            return False, f"http_{r.status_code}:{r.text[:200]}"
        return True, "ok"
    except Exception as e:
        logger.exception("oa webhook")
        return False, str(e)


def notify_integrations(
    *,
    recipient: str,
    message: str,
    notification_type: str,
) -> dict[str, Any]:
    """同时尝试飞书 + OA（若配置了环境变量）。"""
    feishu_url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    oa_url = os.getenv("OA_WEBHOOK_URL", "").strip()
    title = f"[{notification_type}] → {recipient}"
    out: dict[str, Any] = {"feishu": None, "oa": None}
    if feishu_url:
        ok, detail = deliver_feishu_text(feishu_url, title, message)
        out["feishu"] = {"ok": ok, "detail": detail}
    if oa_url:
        ok, detail = deliver_oa_webhook(
            oa_url,
            {
                "source": "baozun-risk-agent",
                "type": notification_type,
                "recipient": recipient,
                "message": message,
                "raw": json.dumps({"recipient": recipient, "message": message, "type": notification_type}, ensure_ascii=False),
            },
        )
        out["oa"] = {"ok": ok, "detail": detail}
    return out
