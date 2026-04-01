"""外部集成：飞书/OA Webhook、外部 JSON 数据覆盖、定时任务等（V4 需求落地桥接）。"""

from integrations.webhooks import deliver_feishu_text, deliver_oa_webhook
from integrations.data_overlay import apply_startup_data_overlays
from integrations.scheduler import monthly_report_scheduler_loop
from integrations.settings import integration_status_dict as build_integration_status

__all__ = [
    "deliver_feishu_text",
    "deliver_oa_webhook",
    "apply_startup_data_overlays",
    "monthly_report_scheduler_loop",
    "build_integration_status",
]
