"""启动脚本。填好 .env 之后，直接运行： python run.py"""

import uvicorn

from server.config import settings

if __name__ == "__main__":
    print("=" * 56)
    print("  小欧 · 启发式数学老师")
    print(f"  已连接大模型：{'是（模型 ' + settings.model + '）' if settings.is_configured else '否（请先配置 .env）'}")
    print(f"  打开浏览器访问： http://{settings.host}:{settings.port}")
    print("  按 Ctrl+C 停止")
    print("=" * 56)
    uvicorn.run("server.app:app", host=settings.host, port=settings.port, reload=False)
