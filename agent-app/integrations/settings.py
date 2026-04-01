"""集成相关环境变量（与 .env / 部署说明对齐）。"""

import os
from pathlib import Path


def integration_status_dict(base_dir: Path) -> dict:
    ext = base_dir / "external_data"
    return {
        "feishu_webhook_configured": bool(os.getenv("FEISHU_WEBHOOK_URL", "").strip()),
        "oa_webhook_configured": bool(os.getenv("OA_WEBHOOK_URL", "").strip()),
        "llm_openai_api_base": (os.getenv("LLM_OPENAI_API_BASE") or os.getenv("OPENAI_API_BASE") or "").strip()
        or "(default https://api.deepseek.com)",
        "llm_model": (os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "").strip() or "deepseek-chat",
        "scheduled_monthly_report": os.getenv("ENABLE_SCHEDULED_MONTHLY_REPORT", "").strip() == "1",
        "external_data_dir_exists": ext.is_dir(),
        "external_overlay_files": sorted([p.name for p in ext.glob("*.json")]) if ext.is_dir() else [],
    }
