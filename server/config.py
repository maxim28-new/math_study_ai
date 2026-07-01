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
    # 文字模型（负责全部教学对话）
    base_url: str
    api_key: str
    model: str
    # 视觉模型（只负责拍照 OCR，不参与教学）
    vision_base_url: str
    vision_api_key: str
    vision_model: str
    # DeepSeek V4 thinking 模式（仅 DeepSeek 生效）
    thinking_enabled: bool
    reasoning_effort: str  # "high" | "max"
    show_reasoning: bool   # 开启 thinking 时，是否在界面灰色展示思考过程
    host: str
    port: int

    @property
    def is_configured(self) -> bool:
        """文字模型是否已配置（教学功能的前提）。"""
        return bool(self.api_key.strip())

    @property
    def is_vision_configured(self) -> bool:
        """视觉模型是否可用（拍照 OCR 的前提）。"""
        return bool(self.vision_api_key.strip()) and bool(self.vision_model.strip())

    @property
    def vision_uses_separate_credentials(self) -> bool:
        """OCR 是否使用了与文字模型不同的接口或密钥。"""
        return (
            self.vision_base_url.rstrip("/") != self.base_url.rstrip("/")
            or self.vision_api_key != self.api_key
        )

    @property
    def chat_endpoint(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    @property
    def vision_chat_endpoint(self) -> str:
        return self.vision_base_url.rstrip("/") + "/chat/completions"


def load_settings() -> Settings:
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    # DeepSeek V4：官方推荐 deepseek-v4-flash（快/省）或 deepseek-v4-pro（更强）。
    # 旧名 deepseek-chat 将于 2026-07-24 退役，仍可用但建议迁移。
    model = os.getenv("LLM_MODEL", "deepseek-v4-flash").strip()

    # 视觉模型三项均可独立配置；留空则分别沿用文字模型的对应项。
    vision_base_url = os.getenv("LLM_VISION_BASE_URL", "").strip() or base_url
    vision_api_key = os.getenv("LLM_VISION_API_KEY", "").strip() or api_key
    vision_model = os.getenv("LLM_VISION_MODEL", "").strip() or model

    thinking_raw = os.getenv("LLM_THINKING", "disabled").strip().lower()
    thinking_enabled = thinking_raw in ("1", "true", "yes", "enabled", "on")
    reasoning_effort = os.getenv("LLM_REASONING_EFFORT", "high").strip().lower()
    if reasoning_effort not in ("high", "max"):
        reasoning_effort = "high"
    show_reasoning_raw = os.getenv("LLM_SHOW_REASONING", "false").strip().lower()
    show_reasoning = show_reasoning_raw in ("1", "true", "yes", "on")

    return Settings(
        base_url=base_url,
        api_key=api_key,
        model=model,
        vision_base_url=vision_base_url,
        vision_api_key=vision_api_key,
        vision_model=vision_model,
        thinking_enabled=thinking_enabled,
        reasoning_effort=reasoning_effort,
        show_reasoning=show_reasoning,
        host=os.getenv("HOST", "127.0.0.1").strip(),
        port=int(os.getenv("PORT", "8000")),
    )


settings = load_settings()


def teaching_request_extras(settings: Settings) -> dict:
    """DeepSeek V4 专用参数：thinking 模式与推理深度。

    见 https://api-docs.deepseek.com/guides/thinking_mode
    非 DeepSeek 服务商忽略这些字段（由对方 API 自行处理或忽略）。
    """
    u = settings.base_url.lower()
    m = settings.model.lower()
    if "deepseek.com" not in u and not m.startswith("deepseek-"):
        return {}
    if settings.thinking_enabled:
        return {
            "thinking": {"type": "enabled"},
            "reasoning_effort": settings.reasoning_effort,
        }
    return {"thinking": {"type": "disabled"}}
