采购数据源分层（integrations/datasources）
============================================

模式（环境变量 PROCUREMENT_DATA_SOURCE）：
  mock            — 不同步，仅用内置 PROCUREMENT_DB + external_data 覆盖（默认）
  http_rest       — GET PROCUREMENT_REST_BASE_URL + PROCUREMENT_REST_LIST_PATH
  selectdb_mysql  — pymysql 执行只读 SELECT（SELECTDB_MYSQL_DSN + SELECTDB_PROCUREMENT_SQL）

合并：
  PROCUREMENT_MERGE_MODE=merge   外部记录按 po_number 写入/覆盖（默认）
  PROCUREMENT_MERGE_MODE=replace 先清空 PROCUREMENT_DB 再写入外部（慎用）

REST 可选：
  PROCUREMENT_REST_HEADERS_JSON  例: {"Authorization":"Bearer xxx"}

说明：REST 客户端默认 trust_env=False，避免本机 HTTP(S)_PROXY 把 127.0.0.1 走代理导致 502。
若目标 URL 必须经公司代理访问，可后续在代码中改为可配置。

SelectDB：
  SELECTDB_MYSQL_DSN   例: mysql+pymysql://user:pass@selectdb-host:9030/analytics
  SELECTDB_PROCUREMENT_SQL  不填则使用 config 内默认 SELECT ... FROM vw_risk_procurement_po

热更新：
  POST /api/datasources/reload-procurement
  若设置 DATASOURCE_RELOAD_TOKEN，需 Header: X-Admin-Token: <token>

契约文件：
  openapi/procurement_list.yaml
  sql/procurement_view_sample.sql
  fixtures/procurement_list.sample.json

本地打通：
  终端1: python scripts/mock_procurement_rest_server.py
  终端2: set PROCUREMENT_DATA_SOURCE=http_rest
         set PROCUREMENT_REST_BASE_URL=http://127.0.0.1:8765
         python server.py
  浏览器或 curl: GET http://127.0.0.1:8800/api/datasources/status
