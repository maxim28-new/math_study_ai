"""Serve the V2 workshop at /v2 without touching the V1 static tree."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from server.config import V2_DIST_DIR

V2_STUB = """<!DOCTYPE html>
<html lang="zh-CN" data-v2="workshop">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>小欧数学世界</title>
</head>
<body>
  <p>桥梁工坊还没构建。在 <code>v2/</code> 里运行 <code>npm run build</code>。</p>
</body>
</html>
"""


def mount_v2(app: FastAPI) -> None:
    index = V2_DIST_DIR / "index.html"
    if index.is_file():
        app.mount("/v2", StaticFiles(directory=V2_DIST_DIR, html=True), name="v2")
        return

    def v2_stub() -> HTMLResponse:
        return HTMLResponse(V2_STUB)

    app.add_api_route("/v2", v2_stub, methods=["GET"], include_in_schema=False)
    app.add_api_route("/v2/", v2_stub, methods=["GET"], include_in_schema=False)
