# 宝尊电商 · 非经营性采购风控 AI Agent（POC）

> **用自然语言对话，把采购风控从「事后报表」推进到「实时可问、可溯源、可闭环」。**  
> 面向企业非经营性采购场景的可演示工程：**对话式风控 Agent**、**异常洞察看板**、**全链路溯源**与**自动化月报**，并为企业协作与数据源落地预留标准接口。

[![Repo](https://img.shields.io/badge/GitHub-baozun--risk--agent-181717?logo=github)](https://github.com/chenchen-stack/baozun-risk-agent)
[![Live Demo](https://img.shields.io/badge/在线演示-Render-46E3B7?logo=render)](https://baozun-risk-agent.onrender.com/)

**公网演示（Render）：** [https://baozun-risk-agent.onrender.com/](https://baozun-risk-agent.onrender.com/) · 推送 `main` 后由 [Render Blueprint](https://github.com/chenchen-stack/baozun-risk-agent/blob/main/render.yaml) 自动构建部署（免费档冷启动约 30～60 秒）。

<a id="readme-toc"></a>

## 文档目录（GitHub 首页即可看完）

以下链接在 [本仓库 README](https://github.com/chenchen-stack/baozun-risk-agent) 中跳转；**各场景使用说明均写在本页，无需另开 Wiki。**

| 区块 | 说明 |
|------|------|
| [产品定位](#id-product) | 痛点与 POC 价值 |
| [核心能力](#id-capabilities) | 对外话术一览表 |
| [技术架构](#id-arch) | FastAPI / LangChain / 部署形态 |
| [仓库导览](#id-layout) | 目录与文件用途 |
| [快速运行](#id-quickstart) | 本地一条链路启动 |
| [使用说明 · 分场景](#id-usage) | **场景一～十一（完整）** |
| └ [环境变量速查表](#scenario-env-table) | 变量与场景对照 |
| └ [场景一～十一](#scenario-01) | 锚点见下表 |
| [推送到 GitHub](#id-git-push) | 协作与保密提醒 |
| [许可证](#id-license) | 使用范围 |

**场景直达：** [一](#scenario-01) · [二](#scenario-02) · [三](#scenario-03) · [四](#scenario-04) · [五](#scenario-05) · [六](#scenario-06) · [七](#scenario-07) · [八](#scenario-08) · [九](#scenario-09) · [十](#scenario-10) · [十一](#scenario-11)

---

<a id="id-product"></a>

## 产品定位：为谁解决什么问题

非经营性采购链条长、单据多、规则杂——传统方式依赖人工翻系统、对 Excel、开周会复盘，**风险发现滞后、解释成本高、跨部门协同慢**。  
本 POC 将大模型与结构化工具链结合，让业务与内控人员**像和同事说话一样**完成：异常追问、单据穿透、维度对比与报告生成，同时保留**可部署、可集成、可换数据源**的工程化路径，便于从演示走向试点。

---

<a id="id-capabilities"></a>

## 核心能力（营销向一览）

| 能力 | 你能对外怎么说 |
|------|----------------|
| **对话式风控** | 不用记菜单路径，用业务语言提问，Agent 调用内置知识与工具给出可追溯结论。 |
| **异常看板** | 一屏聚合关键异常与指标，适合管理层与项目组周会、评审会投屏。 |
| **采购全链路溯源** | 从申请、预算、订单到履约相关线索的关联查询路径，支撑「这笔单为什么标红」的说明。 |
| **月报 HTML 自动化** | 定时生成可读性好的 HTML 报告，减轻月初手工汇总与排版成本。 |
| **企业协作就绪** | 飞书 / OA Webhook 可选接入，关键事件可推到现有协作流，而不是再造一个孤岛系统。 |
| **数据源可演进** | 同一套 `integrations/datasources` 分层：**Mock 演示**、**采购 REST（OpenAPI 样例）**、**SelectDB / MySQL 只读视图（SQL 样例）**，按客户环境逐步替换，无需推翻前端与 Agent 框架。 |
| **风控编排画布** | 侧栏「风控编排」：触发 → API/库/RPA → 标准化 → 智能体 → 决策 → 回调/审计；一键运行串联真实 API，结果区可联动 AI 对话（演示）。 |

---

<a id="id-arch"></a>

## 技术架构：稳定、可演示、可上云

- **应用内核**：**FastAPI** 提供 API 与页面服务；**LangChain** 工具链组织检索、风控逻辑与 LLM 调用。  
- **前端体验**：`agent-app/static` 内嵌**单页交互**，开箱即演示，无需单独前端工程即可对外展示。  
- **部署与交付**：Docker 与 **阿里云**（ACR、ECS、Compose、SAE 等）部署说明见 `agent-app/阿里云部署说明.md`；根目录另含 [Render](https://render.com) 的 `render.yaml` 示例，便于多云对比验证。

---

<a id="id-layout"></a>

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
| `docs/workflow-risk-nodes.html` | **工作流节点静态示意**；与 `agent-app/static/workflow-risk-nodes.html` 同源。主应用侧栏 **「风控编排」** 为 [LiteGraph.js](https://github.com/jagenjo/litegraph.js) 可编辑画布（浅色 Dify 风 UI、节点顺序运行、底部运行结果卡片可点「问 AI / 联系业务」）；编排持久化见下。可选总览接口：`GET /api/pipeline/status`。 |

---

<a id="id-quickstart"></a>

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
- **风控编排（工作流画布）**：侧栏 **「风控编排」**。[LiteGraph.js](https://github.com/jagenjo/litegraph.js) 拖拽连线、右键加节点、缩放平移；**运行**按节点顺序执行各节点 `onExecute`（同源时真实请求 `/api/health`、`/api/datasources/status` 等）；编排持久化 **`GET/POST /api/pipeline/graph`** → `agent-app/data/pipeline_graph.json`（已 `.gitignore`）。脚本依赖 jsDelivr CDN，离线请自备 `litegraph.min.js`。  
- **可选总览接口**：`GET /api/pipeline/status`（集成态摘要；与画布页解耦）。若返回 **404**，说明运行进程不是当前版本，请重新部署或重启服务。  
- **请勿用 `file://` 直接打开 `index.html`**，否则无法请求 API——请通过 `python server.py` 或公网演示地址以 **http(s)** 访问。  

---

<a id="id-usage"></a>

## 使用说明（分场景）

以下均以 **`agent-app/` 为主应用**；环境变量写在 `agent-app/.env`（由 **[`.env.example`](agent-app/.env.example)** 复制）。**本地**修改 `.env` 后需**重启** `python server.py` 生效；**Render / 阿里云**等平台在控制台改环境变量后一般会触发重新部署。热更新采购数据见 [场景七](#scenario-07) 中的 `reload` 接口。

<a id="scenario-env-table"></a>

### 速查：环境变量与场景对照表

| 环境变量（示例见 `.env.example`） | 主要对应场景 | 摘要 |
|----------------------------------|-------------|------|
| `DEEPSEEK_API_KEY` | 二、十 | DeepSeek 对话密钥；云端必填之一 |
| `LLM_API_KEY` | 二、十 | 部分逻辑优先于 `DEEPSEEK_API_KEY` |
| `LLM_OPENAI_API_BASE` / `LLM_MODEL` | 二、十 | 火山 / 通义等 OpenAI 兼容网关 |
| `AGENT_MAX_ITERATIONS` | 二 | 单条用户消息内工具循环上限（默认 36） |
| `FEISHU_WEBHOOK_URL` | 四、六 | 飞书机器人 Webhook，真实 POST |
| `OA_WEBHOOK_URL` | 四 | OA 回调地址 |
| `EXTERNAL_DATA_BOOTSTRAP_URL` | 五 | 启动时从 URL 拉取整包 JSON（可信源） |
| `ENABLE_SCHEDULED_MONTHLY_REPORT` | 六 | 设为 `1` 开启每月 1 号 HTML 月报 |
| `PROCUREMENT_DATA_SOURCE` | 七 | `mock` / `http_rest` / `selectdb_mysql` |
| `PROCUREMENT_REST_*` | 七 | REST 基址、路径、可选 `HEADERS_JSON` |
| `PROCUREMENT_MERGE_MODE` | 七 | `merge`（默认）或 `replace` |
| `SELECTDB_MYSQL_DSN` / `SELECTDB_PROCUREMENT_SQL` | 七 | 只读库与 SQL |
| `DATASOURCE_RELOAD_TOKEN` | 七 | 配置后 `reload-procurement` 需 `X-Admin-Token` |

<details>
<summary><b>展开：与 OpenAPI 兼容的备选变量名（若你沿用旧文档）</b></summary>

部分运行环境也识别 `OPENAI_API_BASE`、`OPENAI_MODEL`（与 `LLM_*` 等价用途），以 [integrations/settings.py](agent-app/integrations/settings.py) 实际读取为准。

</details>

---

<a id="scenario-01"></a>

### 场景一：本地安装与首次启动

适合：开发、客户现场笔记本演示。

1. 进入目录并安装依赖（Windows / macOS / Linux 仅激活虚拟环境命令不同）：

```bash
cd agent-app
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows；Unix 用 cp
```

2. 在 `.env` 中至少配置 **一种** 大模型密钥（见场景二），保存后执行 `python server.py`。  
3. 浏览器访问 **`http://127.0.0.1:8800/`**（端口以终端输出为准）。

<a id="scenario-02"></a>

### 场景二：大模型配置（DeepSeek / OpenAI 兼容）

| 子场景 | 配置要点 |
|--------|----------|
| **默认 DeepSeek** | 填写 `DEEPSEEK_API_KEY`；可选 `LLM_API_KEY`（部分逻辑优先读它）。密钥获取见 [.env.example](agent-app/.env.example) 内注释链接。 |
| **火山引擎 / 通义千问等兼容网关** | 设置 `LLM_OPENAI_API_BASE`（网关 Base URL，通常含 `/v1`）、`LLM_MODEL`（如 `qwen-plus`），并配置对应 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY` 字段承载该网关的 Key（与具体厂商文档一致）。 |
| **对话轮次上限** | 可选 `AGENT_MAX_ITERATIONS`（默认 36；复杂任务可 32～40，最大建议 80）。 |

前端可请求 **`GET /api/config`**，查看服务端是否已配置默认 Key（未在页面填写时是否仍可走服务端 Key）。

<a id="scenario-03"></a>

### 场景三：浏览器内使用（对话、看板、溯源、报告）

| 用途 | 说明 |
|------|------|
| **对话式风控** | 首页多轮对话；流式输出由 **`POST /api/chat`**（SSE）驱动，适合演示「自然语言问风险、要依据」。 |
| **异常看板** | 前端调用 **`GET /api/dashboard`** 等聚合接口；也可直接调 **`/api/workorders`**、`/api/notifications`、`/api/suppliers`、`/api/budgets`、`/api/deliveries`、`/api/assets` 做二次开发或联调。 |
| **采购单溯源** | **`GET /api/po-trace/{po}`**，`po` 为采购单号（如 `PO-2026-101`），用于全链路穿透演示。 |
| **月报列表** | **`GET /api/reports`**；生成文件落在 `agent-app/reports/`（具体生成逻辑见定时任务与相关 API）。 |

<a id="scenario-04"></a>

### 场景四：飞书 / OA 消息推送

适合：风险事件、月报完成时推到现有协作工具。

1. 在 `.env` 中配置（按需其一或全开）：  
   - `FEISHU_WEBHOOK_URL` — 飞书机器人 Webhook  
   - `OA_WEBHOOK_URL` — 贵司 OA 回调地址  
2. 重启服务后，代码路径内调用飞书推送时会**真实 POST** 到上述地址。  
3. 自检：**`GET /api/integrations/status`** 中会显示 `feishu_webhook_configured` / `oa_webhook_configured`。

<a id="scenario-05"></a>

### 场景五：外部 JSON 数据覆盖（演示与客户脱敏数据）

适合：真实 API 未就绪时，用 JSON 补丁演示采购/合同/付款等维度。

1. 将符合约定结构的 **`.json` 文件**放入 `agent-app/external_data/`（启动时合并进内存库）。  
2. 可选：设置 **`EXTERNAL_DATA_BOOTSTRAP_URL`**，启动时从**可信内网地址**拉取整包 JSON（对象键需与文件名对应，如 `procurement.json`）。  
3. 自检：**`GET /api/integrations/status`** 中的 `external_overlay_files` 会列出已扫描到的文件名。

<a id="scenario-06"></a>

### 场景六：定时月报（HTML + 可选飞书提醒）

适合：每月固定产出风控月报 HTML，减少手工汇总。

1. 在 `.env` 中设置 **`ENABLE_SCHEDULED_MONTHLY_REPORT=1`**。  
2. 服务运行后由调度逻辑在 **每月 1 号**触发：生成 HTML 至 `agent-app/reports/`，若已配置 **`FEISHU_WEBHOOK_URL`**，可附带飞书提示（具体文案以当前实现为准）。  
3. 自检：**`GET /api/integrations/status`** 中 `scheduled_monthly_report` 为 `true` 表示已开启。

<a id="scenario-07"></a>

### 场景七：采购数据源（内置 Mock / 采购 REST / SelectDB 只读）

适合：从「纯演示数据」演进到「接客户采购中台 REST」或「SelectDB 只读视图」。

| 模式 | 环境变量 | 说明 |
|------|----------|------|
| **Mock（默认）** | `PROCUREMENT_DATA_SOURCE=mock` 或不写 | 不同步外部接口；使用内置库 + `external_data` 覆盖。 |
| **HTTP GET 列表** | `PROCUREMENT_DATA_SOURCE=http_rest`，`PROCUREMENT_REST_BASE_URL`，`PROCUREMENT_REST_LIST_PATH`（如 `/api/v1/purchase-orders`） | 可选 `PROCUREMENT_REST_HEADERS_JSON` 传鉴权头。本地联调可先起 **`python scripts/mock_procurement_rest_server.py`**（默认 `8765` 端口），再指向 `http://127.0.0.1:8765`。 |
| **SelectDB / MySQL 只读** | `PROCUREMENT_DATA_SOURCE=selectdb_mysql`，`SELECTDB_MYSQL_DSN`，`SELECTDB_PROCUREMENT_SQL`（可省略则用内置默认 SELECT） | 仅允许只读查询；DSN 示例见 `.env.example`。密码含特殊字符时请做 **URL 编码**。 |

合并策略：**`PROCUREMENT_MERGE_MODE=merge`**（按 `po_number` 覆盖，默认）或 **`replace`**（先清空再写入，慎用）。

- 状态查询：**`GET /api/datasources/status`**  
- 热拉取（不配 token 则可直接调；生产建议配 token）：**`POST /api/datasources/reload-procurement`**，若设置 **`DATASOURCE_RELOAD_TOKEN`**，需带请求头 **`X-Admin-Token`**。  

契约与样例：**`agent-app/integrations/datasources/`** 下 `openapi/`、`sql/`、`fixtures/` 与 **[`README.txt`](agent-app/integrations/datasources/README.txt)**（含本机 REST **502 / 系统代理**说明：客户端默认 `trust_env=False`，避免 `HTTP_PROXY` 把 `127.0.0.1` 走公司网关）。

**本地联调 REST 两步：** 终端 A 执行 `python scripts/mock_procurement_rest_server.py`（`agent-app` 目录）；终端 B 设 `PROCUREMENT_DATA_SOURCE=http_rest` 与 `PROCUREMENT_REST_BASE_URL=http://127.0.0.1:8765` 后启动 `server.py`；浏览器访问 `GET /api/datasources/status` 确认同步条数。

<a id="scenario-08"></a>

### 场景八：运维与接口自检

| 接口 | 用途 |
|------|------|
| `GET /api/health` | 进程存活探测 |
| `GET /api/integrations/status` | 飞书/OA、LLM 基址与模型名、定时月报开关、`external_data` 文件列表 |
| `GET /api/datasources/status` | 采购同步模式、是否成功、合并条数、错误信息 |

<a id="scenario-09"></a>

### 场景九：Docker 与阿里云部署

适合：测试环境 / 客户 VPC 内长期运行。

- 详细步骤、镜像构建与环境变量：**[agent-app/阿里云部署说明.md](agent-app/阿里云部署说明.md)**  
- 同目录另有 `Dockerfile`、`docker-compose.aliyun.yml`、脚本示例，按客户网络与安全要求调整端口与密钥注入方式（**勿把 `.env` 提交到 Git**）。

<a id="scenario-10"></a>

### 场景十：公网演示地址（推荐 Render）

适合：**几分钟内得到可分享 HTTPS 链接**（免费档冷启动约 30～60 秒，无人访问会休眠；正式商用建议付费档或阿里云）。

**与本仓库同步的演示地址：** **[https://baozun-risk-agent.onrender.com/](https://baozun-risk-agent.onrender.com/)**（源码：[github.com/chenchen-stack/baozun-risk-agent](https://github.com/chenchen-stack/baozun-risk-agent)）。向 `main` 推送后，Render 会自动重新构建；若页面仍是旧版，在 Render Dashboard 查看部署日志或手动 **Clear build cache & deploy**。

**不推荐用 Vercel 部署本仓库主应用**：当前主工程是 **FastAPI 长驻进程**，与 Vercel 默认 Serverless 模型不匹配；用下面方式更省事。

#### 方案 A：Render（与仓库内 `render.yaml` 对齐）

1. 打开 [render.com](https://render.com) ，用 GitHub 登录。  
2. **Dashboard → New → Blueprint**（或 **New Web Service**）。  
   - 若用 **Blueprint**：选中仓库 **`chenchen-stack/baozun-risk-agent`**，Render 会读取根目录 **`render.yaml`**（Docker 构建上下文为 `agent-app/`，健康检查 `/api/health`）。  
   - 若用手动 **Web Service**：选同一仓库，**Runtime 选 Docker**，**Dockerfile 路径**填 `agent-app/Dockerfile`，**Docker Build Context** 填 `agent-app`。  
3. 在服务的 **Environment** 里新增（至少一项，与本地 `.env` 一致）：  
   - **`DEEPSEEK_API_KEY`** = 你的 DeepSeek Key（必填才能对话）  
   - 若用兼容网关：再加 **`LLM_OPENAI_API_BASE`**、`LLM_MODEL`、`LLM_API_KEY` 等（见 [agent-app/.env.example](agent-app/.env.example)）。  
4. 部署完成后，控制台会给出 **HTTPS 公网 URL**，把根路径 `/` 发给演示对象即可。  
5. 可选：飞书/OA、采购 REST、定时月报等变量同样在 Render 环境变量里配置，无需提交到 Git。

**说明**：**`agent-app/Dockerfile`** 已包含 **`integrations/`** 目录，否则云端启动会因缺模块失败。

#### 方案 B：Railway / Fly.io（备选）

- **Railway**：[railway.app](https://railway.app) 连接 GitHub，以 **`agent-app/`** 为部署根目录（或使用 **`railway.json`**），在 Variables 里填 `DEEPSEEK_API_KEY` 等。  
- **Fly.io**：安装 `flyctl`，在 **`agent-app/`** 下执行 `fly launch`，`fly.toml` 已存在；密钥：`fly secrets set DEEPSEEK_API_KEY=...`。

#### 安全与合规提醒

公网演示会把入口暴露在互联网：**API Key、内网 Webhook、SelectDB 密码等只放在平台「环境变量 / Secrets」**，勿将 `.env` 提交到 Git；演示数据建议用内置 Mock + 脱敏 `external_data`。

**Render Blueprint 常见报错：** 若提示 **`render.yaml not found`**，请确认选中的 GitHub 仓库是 **`chenchen-stack/baozun-risk-agent`**，而不是其他练习仓库；**Branch** 为 **`main`**，**Blueprint Path** 为根目录 **`render.yaml`**。

<a id="scenario-11"></a>

### 场景十一：根目录 `app.py`（历史极简 Demo）

仓库根目录的 **`app.py` + `static/`** 为早期 OpenAI SDK 直连 Demo，**与 `agent-app` 的数据域、风控能力不一致**。对外 POC、验收与运维**请以 `agent-app` 为准**；仅当需要对比「最简聊天壳」时再使用根目录 Demo。

**[↑ 回到文档目录](#readme-toc)**

---

<a id="id-git-push"></a>

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

<a id="id-license"></a>

## 许可证

内部 POC 使用；对外分发前请与客户及法务确认。
