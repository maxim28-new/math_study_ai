"""启动脚本。填好 .env 之后，直接运行： python run.py"""

import uvicorn

from server.config import settings

if __name__ == "__main__":
    print("=" * 56)
    print("  小欧 · 启发式数学老师")
    if settings.is_configured:
        print(f"  文字教学：{settings.model}")
        print(f"            {settings.base_url}")
    else:
        print("  文字教学：未配置（请先填写 .env 里的 LLM_API_KEY）")
    if settings.is_vision_configured:
        tag = "独立 OCR 配置" if settings.vision_uses_separate_credentials else "沿用文字模型配置"
        print(f"  拍照 OCR ：{settings.vision_model}（{tag}）")
        print(f"            {settings.vision_base_url}")
    else:
        print("  拍照 OCR ：未配置（可选填 LLM_VISION_* 三项）")
    print(f"  打开浏览器访问： http://{settings.host}:{settings.port}")
    print("  按 Ctrl+C 停止")
    print("=" * 56)
    uvicorn.run("server.app:app", host=settings.host, port=settings.port, reload=False)
