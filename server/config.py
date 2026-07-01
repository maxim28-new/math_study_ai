"""集中管理运行配置。所有可调项都来自环境变量或项目根目录的 .env 文件。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"

# 优先加载项目根目录下的 .env（若存在）。
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    host: str
    port: int

    @property
    def is_configured(self) -> bool:
        """是否已经填好密钥。未配置时前端会进入"未连接"提示状态。"""
        return bool(self.api_key.strip())

    @property
    def chat_endpoint(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"


def load_settings() -> Settings:
    return Settings(
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").strip(),
        api_key=os.getenv("LLM_API_KEY", "").strip(),
        model=os.getenv("LLM_MODEL", "deepseek-chat").strip(),
        host=os.getenv("HOST", "127.0.0.1").strip(),
        port=int(os.getenv("PORT", "8000")),
    )


settings = load_settings()
