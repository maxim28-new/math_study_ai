"""启动脚本。填好 .env 之后，直接运行： python run.py"""

from __future__ import annotations

import socket
from typing import Optional

import uvicorn

from server.config import settings


def lan_ip() -> Optional[str]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return None


if __name__ == "__main__":
    print("=" * 56)
    print("  小欧 · 启发式数学老师（手机 H5）")
    print("  若仍看到左侧设置栏，说明跑的是旧代码，请切到 cursor/kid-h5-d734 后重启")
    mode = "多模态一体（unified）" if settings.is_unified else "OCR + 文字（split）"
    print(f"  处理模式：{mode}")
    if settings.is_configured:
        print(f"  主模型  ：{settings.model}")
        print(f"            {settings.base_url}")
        if settings.is_unified:
            print("  拍照读题：由同一多模态模型直接处理（无需 LLM_VISION_*）")
        elif settings.thinking_enabled:
            show = "灰色展示" if settings.show_reasoning else "不展示（仅最终回复）"
            print(f"  Thinking ：已开启（{settings.reasoning_effort}，思考过程{show}）")
        else:
            print("  Thinking ：关闭（短问短答，推荐陪练）")
    else:
        print("  主模型  ：未配置（请先填写 .env 里的 LLM_API_KEY）")
    if not settings.is_unified and settings.is_vision_configured:
        tag = "独立 OCR 配置" if settings.vision_uses_separate_credentials else "沿用文字模型配置"
        print(f"  拍照 OCR ：{settings.vision_model}（{tag}）")
        print(f"            {settings.vision_base_url}")
    elif not settings.is_unified:
        print("  拍照 OCR ：未配置（可选填 LLM_VISION_*，或改用 unified 模式）")
    print(f"  本机打开： http://127.0.0.1:{settings.port}")
    ip = lan_ip()
    if ip:
        print(f"  手机打开（同一 WiFi）： http://{ip}:{settings.port}")
        print("  把这个网址发给孩子，用浏览器打开即可；可「添加到主屏幕」。")
    if settings.gate_enabled:
        print("  访问门禁：已开启（验证码写在 .env 的 ACCESS_CODE，不要把码印在网址里）")
    else:
        print("  访问门禁：已关闭")
    print("  按 Ctrl+C 停止")
    print("=" * 56)
    uvicorn.run("server.app:app", host=settings.host, port=settings.port, reload=False)
