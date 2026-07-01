"""启动脚本。填好 .env 之后，直接运行： python run.py"""

import uvicorn

from server.config import settings

if __name__ == "__main__":
    print("=" * 56)
    print("  小欧 · 启发式数学老师")
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
    print(f"  打开浏览器访问： http://{settings.host}:{settings.port}")
    print("  按 Ctrl+C 停止")
    print("=" * 56)
    uvicorn.run("server.app:app", host=settings.host, port=settings.port, reload=False)
