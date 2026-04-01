"""
宝尊电商风控AI Agent — FastAPI Server
Endpoints: /api/chat (SSE), /api/dashboard, /reports/*, /
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from agent import (run_agent_stream, get_dashboard_data, get_work_orders, get_notifications,
                    get_suppliers, get_budgets, get_deliveries, get_assets, build_po_trace)

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
PIPELINE_GRAPH_FILE = DATA_DIR / "pipeline_graph.json"
_log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    try:
        import agent as ag
        from integrations.data_overlay import apply_startup_data_overlays

        merged = apply_startup_data_overlays(BASE_DIR, ag)
        if merged:
            _log.info("external_data overlays merged: %s", merged)
        from integrations.datasources.sync import sync_procurement_into_agent

        ds = sync_procurement_into_agent(ag)
        if ds.get("merged_count"):
            _log.info("procurement datasource sync: %s", ds)
    except Exception:
        _log.exception("startup external_data overlay")
    from integrations.scheduler import monthly_report_scheduler_loop

    sched = asyncio.create_task(monthly_report_scheduler_loop())
    yield
    sched.cancel()
    try:
        await sched
    except asyncio.CancelledError:
        pass


app = FastAPI(title="宝尊风控AI Agent", lifespan=_lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class _NoStrongCacheUiMiddleware(BaseHTTPMiddleware):
    """首页与主静态脚本禁用强缓存，避免 CDN/浏览器长期持有旧版 HTML·JS·CSS（Render 部署后刷新即最新）。"""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        try:
            path = request.url.path
            if path == "/":
                response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
            elif path.startswith("/static/") and path.endswith((".js", ".css")):
                response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
        except Exception:
            pass
        return response


app.add_middleware(_NoStrongCacheUiMiddleware)

REPORTS_DIR.mkdir(exist_ok=True)
_REPORTS_ROOT = str(REPORTS_DIR.resolve())
_STATIC_ROOT = str(STATIC_DIR.resolve())

app.mount("/reports", StaticFiles(directory=_REPORTS_ROOT), name="reports")


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "")
    history = body.get("history", [])
    header_key = request.headers.get("X-DeepSeek-API-Key") or request.headers.get("x-deepseek-api-key")

    async def generate():
        async for event in run_agent_stream(user_message, history, api_key=header_key):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
async def health():
    """Render 会注入 RENDER_GIT_COMMIT，便于对照 GitHub 最新提交是否已上线。"""
    commit = (os.getenv("RENDER_GIT_COMMIT") or os.getenv("COMMIT_REF") or "").strip() or None
    return {"ok": True, "service": "baozun-risk-agent", "commit": commit}


@app.get("/api/config")
async def app_config():
    """前端可用来提示：是否仍可用服务器默认 Key（未在界面填写时）。"""
    return {
        "server_has_default_key": bool(
            os.getenv("LLM_API_KEY", "").strip() or os.getenv("DEEPSEEK_API_KEY", "").strip()
        ),
    }


@app.get("/api/integrations/status")
async def integrations_status():
    """对接状态：飞书/OA Webhook、LLM 端点、定时月报、external_data 覆盖文件。"""
    from integrations.settings import integration_status_dict

    return integration_status_dict(BASE_DIR)


@app.get("/api/datasources/status")
async def datasources_status():
    """采购数据源：mock / http_rest / selectdb_mysql 同步结果。"""
    from integrations.datasources.sync import get_procurement_sync_status

    return get_procurement_sync_status()


@app.get("/api/pipeline/status")
async def pipeline_status():
    """数据接入与工作流编排页：聚合集成状态、采购数据源、侧栏模块映射与交付阶段。"""
    from integrations.settings import integration_status_dict
    from integrations.datasources.sync import get_procurement_sync_status

    return {
        "integrations": integration_status_dict(BASE_DIR),
        "procurement_datasource": get_procurement_sync_status(),
        "sidebar_binding": [
            {
                "page": "异常看板 / 预警列表",
                "api": "GET /api/dashboard，Agent 工具链",
                "upstream": "各信息系统数据经适配与校验后的异常集合",
            },
            {
                "page": "工单管理 / 通知记录 / 月度报告",
                "api": "/api/workorders · /api/notifications · /api/reports",
                "upstream": "风控决策后的闭环：派单、触达、月报 HTML",
            },
            {
                "page": "供应商 / 预算 / 交付 / 资产",
                "api": "/api/suppliers · /api/budgets · /api/deliveries · /api/assets",
                "upstream": "外围系统适配节点（REST / 只读库 / RPA）",
            },
        ],
        "delivery_phases": [
            {
                "phase": "P0 · 当前 POC",
                "done": True,
                "items": [
                    "侧栏九大模块与现有 API 已贯通（演示数据 + LangChain 工具）",
                    "采购域：mock / HTTP REST / SelectDB 只读 SQL 适配层",
                    "飞书·OA Webhook、external_data、定时月报可选集成",
                ],
            },
            {
                "phase": "P1 · 准实时与标准宽表",
                "done": False,
                "items": [
                    "客户审批流 Webhook / 消息队列与定时轮询双触发",
                    "ETL 统一单据模型（跨 OA·ERP·费控）",
                    "合同/付款等域独立 Adapter，与采购并列接入",
                ],
            },
            {
                "phase": "P2 · 生产闭环",
                "done": False,
                "items": [
                    "决策结果回写 OA 审批意见 / 加签节点",
                    "RPA 兜底与异常重试队列",
                    "审计日志外置存储与权限分级",
                ],
            },
        ],
    }


@app.get("/api/pipeline/graph")
async def get_pipeline_graph():
    """节点编排画布持久化（LiteGraph.serialize 结构，包装在 JSON 根字段 litegraph）。"""
    if PIPELINE_GRAPH_FILE.is_file():
        try:
            return json.loads(PIPELINE_GRAPH_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            _log.warning("pipeline_graph.json corrupt, ignoring")
    return {"litegraph": None}


@app.post("/api/pipeline/graph")
async def post_pipeline_graph(request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="expected JSON object")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PIPELINE_GRAPH_FILE.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}


@app.post("/api/pipeline/risk-insights")
async def pipeline_risk_insights(request: Request):
    """工作流「运行」结束后：结合当前画布节点摘要与看板真实数据，生成运行结果区展示 JSON。"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    nodes_ctx = body.get("nodes")
    if not isinstance(nodes_ctx, list):
        nodes_ctx = []

    dash = get_dashboard_data()
    exc = dash.get("exceptions") or []
    summary = dash.get("summary") or {}
    wos = dash.get("work_orders") or get_work_orders()

    def _sev_order(level: str) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(str(level or "").lower(), 9)

    pick = None
    if exc:
        pick = sorted(exc, key=lambda e: _sev_order(e.get("level")))[0]

    three_ok = int(summary.get("three_doc_pass") or 0)
    three_tot = int(summary.get("three_doc_total") or 0)
    if three_tot > 0 and three_ok == three_tot:
        match_label = "一致"
    elif three_ok > 0:
        match_label = "部分一致"
    else:
        match_label = "待核对"

    wo_open = None
    closed = {"resolved", "closed", "done"}
    for w in wos:
        st = str(w.get("status") or "").lower()
        if st not in closed:
            wo_open = w
            break
    if wo_open is None and wos:
        wo_open = wos[0]

    hints = []
    if pick:
        hints.append(f"{pick.get('title') or pick.get('type') or '异常'}（风险：{pick.get('level') or '—'}）")
    hints.append(f"画布节点 {len(nodes_ctx)} 个已汇入上下文（触发 / 适配 / 智能体链路）")
    if nodes_ctx:
        sys_names = [str(n.get("source_system") or "").strip() for n in nodes_ctx if str(n.get("source_system") or "").strip()]
        if sys_names:
            hints.append("标注系统：" + "、".join(sys_names[:6]) + ("…" if len(sys_names) > 6 else ""))

    amt = pick.get("amount") if pick else None
    po_guess = pick.get("po") if pick else "—"
    contract_guess = pick.get("contract") if pick else "—"

    return {
        "alert": "存在待处理异常，已关联工单待闭环" if pick else "当前样本下暂无高危异常（仍可继续巡检）",
        "match_label": match_label,
        "three_way": {
            "contract_no": contract_guess,
            "po": po_guess,
            "invoice": "—",
            "acceptance": "—",
            "amount": amt,
            "subtitle": f"三单一致度：{three_ok}/{three_tot}（演示宽表统计）",
        },
        "hints": hints[:8],
        "work_order": wo_open,
        "source": "dashboard",
    }


@app.post("/api/datasources/reload-procurement")
async def datasources_reload_procurement(request: Request):
    """再次拉取采购数据并合并（需配置 DATASOURCE_RELOAD_TOKEN 时校验 Header）。"""
    import agent as ag
    from integrations.datasources.config import reload_admin_token
    from integrations.datasources.sync import sync_procurement_into_agent

    tok = reload_admin_token()
    if tok:
        got = request.headers.get("X-Admin-Token", "").strip()
        if got != tok:
            raise HTTPException(status_code=403, detail="invalid X-Admin-Token")
    return sync_procurement_into_agent(ag)


@app.get("/api/dashboard")
async def dashboard():
    return get_dashboard_data()


@app.get("/api/reports")
async def list_reports():
    reports_dir = str(REPORTS_DIR)
    files = []
    if os.path.exists(reports_dir):
        for f in sorted(os.listdir(reports_dir), reverse=True):
            if f.endswith(".html"):
                filepath = os.path.join(reports_dir, f)
                stat = os.stat(filepath)
                files.append({
                    "filename": f,
                    "url": f"/reports/{f}",
                    "size": stat.st_size,
                    "created": stat.st_mtime,
                })
    return {"reports": files}


@app.get("/api/workorders")
async def workorders():
    return {"work_orders": get_work_orders()}


@app.get("/api/notifications")
async def notifications():
    return {"notifications": get_notifications()}


@app.get("/api/suppliers")
async def suppliers():
    return {"suppliers": get_suppliers()}


@app.get("/api/budgets")
async def budgets():
    return {"budgets": get_budgets()}


@app.get("/api/deliveries")
async def deliveries():
    return {"deliveries": get_deliveries()}


@app.get("/api/assets")
async def assets():
    return {"assets": get_assets()}


@app.get("/api/po-trace/{po}")
async def po_trace(po: str):
    """采购溯源 POC：全链路步骤条 + 金额一致性 + 关联工单（模拟库）。"""
    data = build_po_trace(po)
    if not data:
        raise HTTPException(status_code=404, detail="未知或无法识别的采购单号")
    return data


@app.get("/static/brand-logo.svg", include_in_schema=False)
async def serve_brand_logo_svg():
    """显式提供 Logo，避免部分环境下 StaticFiles 对 /static 子路径返回 404。"""
    path = STATIC_DIR.resolve() / "brand-logo.svg"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="brand-logo.svg missing")
    return FileResponse(
        path,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


app.mount("/static", StaticFiles(directory=_STATIC_ROOT), name="static")


@app.get("/")
async def index():
    return FileResponse(
        STATIC_DIR.resolve() / "index.html",
        headers={"Cache-Control": "no-store, max-age=0, must-revalidate"},
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8800"))
    uvicorn.run(app, host="0.0.0.0", port=port)
