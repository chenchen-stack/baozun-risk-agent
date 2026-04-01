# 宝尊电商 · 非经营性采购风控 AI Agent（POC）

本仓库为**客户 POC / 演示**工程：对话式风控 Agent、异常看板、采购全链路溯源、月报 HTML、阿里云 Docker 部署说明等。

## 目录说明

| 路径 | 说明 |
|------|------|
| **`agent-app/`** | **主应用**（FastAPI + LangChain 工具链 + 前端单页）。日常开发与部署以该目录为准。 |
| `agent-app/阿里云部署说明.md` | ACR + ECS / compose / SAE 部署步骤。 |
| `agent-app/integrations/` | 飞书/OA Webhook、外部 JSON 覆盖、定时月报等可选集成。 |
| `agent-app/integrations/datasources/` | **采购数据源分层**：`mock` / `http_rest` / `selectdb_mysql`，OpenAPI 与 SQL 样例见该目录下 `openapi/`、`sql/`、`fixtures/`；说明见 `README.txt`。 |
| `render.yaml` | [Render](https://render.com) 从本仓库根目录用 Docker 构建 `agent-app` 的示例配置。 |
| `app.py`、`static/` | 历史极简 Demo（OpenAI SDK 直连），**与 `agent-app` 数据与能力不一致**；正式演示请用 `agent-app`。 |
| `presentation.html`、`ppt-diagrams/` | 汇报材料相关。 |
| `docs/` | 文档占位（可按需补充）。 |

## 快速运行（主应用）

```bash
cd agent-app
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # 填入 DEEPSEEK_API_KEY 或 LLM_API_KEY
python server.py
```

浏览器打开：`http://127.0.0.1:8800/`  

健康检查：`/api/health` · 集成状态：`/api/integrations/status`

## 推送到 GitHub

1. 在 [新建仓库](https://github.com/new)（例如名称为 `baozun-risk-agent`），**不要**勾选自动添加 README（若本地已有）。
2. 在本仓库根目录执行：

```bash
git init
git add .
git status   # 确认无 .env / .venv / reports/*.html
git commit -m "chore: initial import — Baozun risk agent POC"
git branch -M main
git remote add origin https://github.com/chenchen-stack/你的仓库名.git
git push -u origin main
```

**切勿**将 `.env`、`env.deploy`、真实 API Key 或 `reports/` 下生成 HTML 提交到公开仓库（已在 `.gitignore` 中排除）。

## 许可证

内部 POC 使用；对外分发前请与客户及法务确认。
