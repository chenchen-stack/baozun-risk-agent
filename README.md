# 宝尊电商 · 非经营性采购风控 AI Agent（POC）

> **用自然语言对话，把采购风控从「事后报表」推进到「实时可问、可溯源、可闭环」。**  
> 面向企业非经营性采购场景的可演示工程：**对话式风控 Agent**、**异常洞察看板**、**全链路溯源**与**自动化月报**，并为企业协作与数据源落地预留标准接口。

[![Repo](https://img.shields.io/badge/GitHub-baozun--risk--agent-181717?logo=github)](https://github.com/chenchen-stack/baozun-risk-agent)

---

## 产品定位：为谁解决什么问题

非经营性采购链条长、单据多、规则杂——传统方式依赖人工翻系统、对 Excel、开周会复盘，**风险发现滞后、解释成本高、跨部门协同慢**。  
本 POC 将大模型与结构化工具链结合，让业务与内控人员**像和同事说话一样**完成：异常追问、单据穿透、维度对比与报告生成，同时保留**可部署、可集成、可换数据源**的工程化路径，便于从演示走向试点。

---

## 核心能力（营销向一览）

| 能力 | 你能对外怎么说 |
|------|----------------|
| **对话式风控** | 不用记菜单路径，用业务语言提问，Agent 调用内置知识与工具给出可追溯结论。 |
| **异常看板** | 一屏聚合关键异常与指标，适合管理层与项目组周会、评审会投屏。 |
| **采购全链路溯源** | 从申请、预算、订单到履约相关线索的关联查询路径，支撑「这笔单为什么标红」的说明。 |
| **月报 HTML 自动化** | 定时生成可读性好的 HTML 报告，减轻月初手工汇总与排版成本。 |
| **企业协作就绪** | 飞书 / OA Webhook 可选接入，关键事件可推到现有协作流，而不是再造一个孤岛系统。 |
| **数据源可演进** | 同一套 `integrations/datasources` 分层：**Mock 演示**、**采购 REST（OpenAPI 样例）**、**SelectDB / MySQL 只读视图（SQL 样例）**，按客户环境逐步替换，无需推翻前端与 Agent 框架。 |

---

## 技术架构：稳定、可演示、可上云

- **应用内核**：**FastAPI** 提供 API 与页面服务；**LangChain** 工具链组织检索、风控逻辑与 LLM 调用。  
- **前端体验**：`agent-app/static` 内嵌**单页交互**，开箱即演示，无需单独前端工程即可对外展示。  
- **部署与交付**：Docker 与 **阿里云**（ACR、ECS、Compose、SAE 等）部署说明见 `agent-app/阿里云部署说明.md`；根目录另含 [Render](https://render.com) 的 `render.yaml` 示例，便于多云对比验证。

---

## 仓库导览

| 路径 | 说明 |
|------|------|
| **`agent-app/`** | **主应用**：日常开发、客户演示、部署均以该目录为准。 |
| `agent-app/阿里云部署说明.md` | 阿里云容器化与上线步骤说明。 |
| `agent-app/integrations/` | 飞书/OA Webhook、外部 JSON 覆盖、定时月报等**可选集成**。 |
| `agent-app/integrations/datasources/` | **采购数据源分层**（`mock` / `http_rest` / `selectdb_mysql`）；OpenAPI、SQL 与 fixture 见 `openapi/`、`sql/`、`fixtures/`，说明见 `README.txt`。 |
| `render.yaml` | Render 从仓库根目录构建 `agent-app` 的示例配置。 |
| `app.py`、`static/` | 历史极简 Demo（OpenAI SDK 直连），**与 `agent-app` 数据与能力不一致**；正式演示请用 `agent-app`。 |
| `presentation.html`、`ppt-diagrams/` | 汇报与演示材料。 |
| `参考材料-*.md` | 业务流程、风控控制点与竞品/业务知识等参考资料。 |

---

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

- 健康检查：`/api/health`  
- 集成状态：`/api/integrations/status`  
- 数据源状态：`/api/datasources/status`  

---

## 推送到 GitHub

公开仓库：**[github.com/chenchen-stack/baozun-risk-agent](https://github.com/chenchen-stack/baozun-risk-agent)**

本地更新后：

```bash
git add .
git commit -m "docs: your message"
git push origin main
```

**切勿**将 `.env`、`env.deploy`、真实 API Key 或 `reports/` 下生成 HTML 提交到公开仓库（已在 `.gitignore` 中排除）。

---

## 许可证

内部 POC 使用；对外分发前请与客户及法务确认。
