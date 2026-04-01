# Cursor 改代码 → Render 公网即时更新（闭环说明）

目标站点：**[https://baozun-risk-agent.onrender.com/](https://baozun-risk-agent.onrender.com/)**

## 1. 一次配置（Render 控制台）

1. 打开 [Render Dashboard](https://dashboard.render.com/)，进入服务 **`baozun-risk-agent`**（或你创建时的名称）。
2. **Settings → Build & Deploy**
   - **Branch**：`main`（或与你的默认分支一致）。
   - **Auto-Deploy**：**Yes**（推送到该分支即自动构建部署）。
3. 确认仓库已连接 **GitHub** 上含本项目的仓库（与本地 `git remote` 一致）。

> 若用 Blueprint：仓库根目录的 [`render.yaml`](render.yaml) 已指定 Docker 构建；首次从 Render **New → Blueprint** 选仓库即可。

## 2. 日常闭环（在 Cursor 里）

1. 修改并保存代码（例如 `agent-app/static/`、`agent-app/server.py` 等）。
2. 在终端执行（路径按你本机仓库为准）：

   ```bash
   git add -A
   git status
   git commit -m "描述本次改动"
   git push origin main
   ```

3. 打开 Render → 该服务 → **Events**，等待最新一条 Deploy 变为 **Live**（免费档冷启动约 30～90 秒）。
4. 浏览器打开（或刷新）公网地址；服务端已对 **`/`** 与 **`/static/*.js`、`.css`** 使用 **不长期强缓存** 策略，一般 **普通刷新** 即可拿到新版本。

## 3. 如何确认「线上就是最新 Git」

调用：

```text
GET https://baozun-risk-agent.onrender.com/api/health
```

响应里的 **`commit`** 为 Render 注入的 **`RENDER_GIT_COMMIT`**（当前部署对应的提交 SHA），与 GitHub 上 `main` 最新提交对比即可。

若 **`commit` 为 `null`**：多为本地 Docker 或未在 Render 上跑；在 Render 托管时通常有值。

## 4. 仍像旧版时

1. **硬刷新**：`Ctrl+Shift+R`（Windows）或 `Cmd+Shift+R`（Mac）。
2. Render **Manual Deploy → Clear build cache & deploy**（清缓存重建）。
3. 看 **Deploy logs** 是否构建失败（依赖、Dockerfile 路径等）。

## 5. 与本仓库的对应关系

| 项目 | 说明 |
|------|------|
| [`render.yaml`](render.yaml) | `dockerContext: ./agent-app`，镜像内包含 `static/`（含 `vendor/litegraph`）。 |
| [`agent-app/Dockerfile`](agent-app/Dockerfile) | `COPY static ./static`，推代码即打进镜像。 |

**结论**：只要 **Auto-Deploy 打开** 且 **`git push` 到绑定分支**，每次部署完成后刷新网站即可对齐仓库最新版本；用 **`/api/health` 的 `commit`** 做客观校验。
