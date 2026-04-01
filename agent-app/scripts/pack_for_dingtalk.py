# -*- coding: utf-8 -*-
"""Pack agent-app to Desktop zip for DingTalk share (excludes .venv, .env, __pycache__)."""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

SKIP_DIR = {".venv", "__pycache__", ".git"}
SKIP_FILE = {".env"}


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    app_root = script_dir.parent
    if not (app_root / "server.py").is_file():
        print("error: server.py not found", file=sys.stderr)
        return 1

    desktop = Path.home() / "Desktop"
    if not desktop.is_dir():
        desktop = Path.home() / "OneDrive" / "Desktop"
    zip_path = desktop / "宝尊风控Agent-钉钉分享.zip"

    inner_root = "宝尊风控Agent"
    readme_name = "【先看这里】解压后双击一键安装并启动.txt"
    readme_body = """============================================
  宝尊风控 AI Agent — 解压后怎么做
============================================

1. 解压本压缩包到任意文件夹（路径尽量不要有奇怪符号）。

2. 打开文件夹「宝尊风控Agent」。

3. 先看：小白使用说明-如何打开.md
   （用记事本打开即可）

4. 双击运行：一键安装并启动.bat

5. 浏览器打开：http://127.0.0.1:8800/

注意：首次运行会自动装依赖，需已安装 Python 3.10+。
压缩包内不含 .venv（体积大），第一次启动会自动创建。
不含 .env 密钥文件，请按说明填写 DeepSeek API Key。
"""

    if zip_path.exists():
        zip_path.unlink()

    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{inner_root}/{readme_name}", readme_body.encode("utf-8"))
        count += 1
        for path in app_root.rglob("*"):
            rel = path.relative_to(app_root)
            parts = set(rel.parts)
            if parts & SKIP_DIR:
                continue
            if any(p in SKIP_DIR for p in rel.parts):
                continue
            if path.is_dir():
                continue
            if path.name in SKIP_FILE:
                continue
            arc = f"{inner_root}/" + rel.as_posix()
            zf.write(path, arcname=arc)
            count += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"OK: {zip_path}")
    print(f"  files in zip (incl. readme): {count}, size: {size_mb:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
