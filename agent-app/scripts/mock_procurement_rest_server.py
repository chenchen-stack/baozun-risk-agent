"""
本地模拟采购 REST：返回 fixtures/procurement_list.sample.json

用法（在 agent-app 目录）:
  python scripts/mock_procurement_rest_server.py

另开终端设环境变量后启动主服务:
  set PROCUREMENT_DATA_SOURCE=http_rest
  set PROCUREMENT_REST_BASE_URL=http://127.0.0.1:8765
  python server.py
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_FIXTURE = Path(__file__).resolve().parent.parent / "integrations" / "datasources" / "fixtures" / "procurement_list.sample.json"
_PORT = 8765


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(fmt % args)

    def do_GET(self) -> None:
        if self.path.startswith("/api/v1/purchase-orders"):
            raw = _FIXTURE.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(raw.encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()


def main() -> None:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    n = len(data.get("items", []))
    print(f"mock procurement REST → http://127.0.0.1:{_PORT}/api/v1/purchase-orders  ({n} PO)")
    HTTPServer(("0.0.0.0", _PORT), H).serve_forever()


if __name__ == "__main__":
    main()
