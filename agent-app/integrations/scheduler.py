"""可选：每月 1 号自动生成内控 HTML 报告（F14 定时能力）。"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


async def monthly_report_scheduler_loop() -> None:
    """每小时唤醒一次；开启 ENABLE_SCHEDULED_MONTHLY_REPORT=1 且为每月 1 号时生成一份报告（同月仅一次）。"""
    last_month_key: str | None = None
    while True:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            break
        if os.getenv("ENABLE_SCHEDULED_MONTHLY_REPORT", "").strip() != "1":
            continue
        now = datetime.now()
        if now.day != 1:
            continue
        key = f"{now.year}-{now.month:02d}"
        if last_month_key == key:
            continue
        try:
            import agent as ag

            title = f"{now.year}年{now.month}月非经营性采购内控报告（定时自动生成）"
            ag.generate_risk_report.invoke({"report_title": title})
            last_month_key = key
            logger.info("scheduled monthly report generated: %s", title)
            hook = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
            if hook:
                from integrations.webhooks import deliver_feishu_text

                deliver_feishu_text(
                    hook,
                    "月度内控报告",
                    f"已生成：{title}，请在系统「月度报告」页下载 /reports/ 下最新 HTML。",
                )
        except Exception:
            logger.exception("scheduled monthly report failed")
