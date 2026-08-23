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
    # 处理流水线：split=OCR+文字模型；unified=一个多模态模型包办
    pipeline: str
    # 文字模型（split 模式下负责教学；unified 模式下包办文字+图片）
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
    # 公网访问验证码。默认 maxim；设为 off/disabled/none 则关闭门禁。
    access_code: str
    # 语音听写。local / faster-whisper 走本机；其它名字走云端；off 关闭。
    asr_model: str
    asr_local_engine: str
    asr_whisper_size: str
    asr_cloud_fallback: str
    # 出题作者（强模型）。deepseek | glm
    author_engine: str
    author_reasoning_effort: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    zhipu_api_key: str
    zhipu_base_url: str
    zhipu_model: str

    @property
    def gate_enabled(self) -> bool:
        return bool(self.access_code)

    @property
    def is_configured(self) -> bool:
        """文字模型是否已配置（教学功能的前提）。"""
        return bool(self.api_key.strip())

    @property
    def voice_enabled(self) -> bool:
        """本机 whisper 不需要云端听写密钥；云端听写仍要文字模型密钥。"""
        if not self.asr_model:
            return False
        if is_local_asr_model(self.asr_model):
            return True
        return self.is_configured

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
    def is_unified(self) -> bool:
        return self.pipeline == "unified"

    @property
    def photo_enabled(self) -> bool:
        """是否允许拍照/上传题目。"""
        if not self.is_configured:
            return False
        if self.is_unified:
            return True
        return self.is_vision_configured

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

    pipeline_raw = os.getenv("LLM_PIPELINE", "split").strip().lower()
    pipeline = "unified" if pipeline_raw in ("unified", "multimodal", "single") else "split"

    thinking_raw = os.getenv("LLM_THINKING", "disabled").strip().lower()
    thinking_enabled = thinking_raw in ("1", "true", "yes", "enabled", "on")
    reasoning_effort = os.getenv("LLM_REASONING_EFFORT", "high").strip().lower()
    if reasoning_effort not in ("high", "max"):
        reasoning_effort = "high"
    # 未显式设置时：开启 thinking 就默认展示思考过程（用户："开启的时候干脆展示"）。
    show_reasoning_raw = os.getenv("LLM_SHOW_REASONING")
    if show_reasoning_raw is None or show_reasoning_raw.strip() == "":
        show_reasoning = thinking_enabled
    else:
        show_reasoning = show_reasoning_raw.strip().lower() in ("1", "true", "yes", "on")

    return Settings(
        pipeline=pipeline,
        base_url=base_url,
        api_key=api_key,
        model=model,
        vision_base_url=vision_base_url,
        vision_api_key=vision_api_key,
        vision_model=vision_model,
        thinking_enabled=thinking_enabled,
        reasoning_effort=reasoning_effort,
        show_reasoning=show_reasoning,
        host=os.getenv("HOST", "0.0.0.0").strip(),
        port=int(os.getenv("PORT", "8000")),
        access_code=_load_access_code(),
        asr_model=_load_asr_model(),
        asr_local_engine=_load_local_engine(),
        asr_whisper_size=_load_whisper_size(),
        asr_cloud_fallback=_load_asr_cloud_fallback(),
        author_engine=_load_author_engine(),
        author_reasoning_effort=_load_author_effort(),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
        or "https://api.deepseek.com",
        deepseek_model=os.getenv("DEEPSEEK_AUTHOR_MODEL", "deepseek-v4-pro").strip()
        or "deepseek-v4-pro",
        zhipu_api_key=(os.getenv("ZHIPU_API_KEY") or os.getenv("GLM_API_KEY") or "").strip(),
        zhipu_base_url=os.getenv(
            "ZHIPU_BASE_URL", "https://api.z.ai/api/coding/paas/v4"
        ).strip()
        or "https://api.z.ai/api/coding/paas/v4",
        zhipu_model=os.getenv("ZHIPU_AUTHOR_MODEL", "glm-5.3").strip() or "glm-5.3",
    )


def _load_author_engine() -> str:
    raw = os.getenv("LLM_AUTHOR", "glm").strip().lower()
    if raw in ("deepseek", "ds", "v4-pro"):
        return "deepseek"
    return "glm"


def _load_author_effort() -> str:
    raw = os.getenv("LLM_AUTHOR_REASONING_EFFORT", "high").strip().lower()
    if raw not in ("low", "high", "max"):
        return "high"
    return raw


LOCAL_ASR_MODELS = frozenset({"local", "faster-whisper", "whisper", "whisper-local"})
_WHISPER_SIZES = frozenset(
    {"tiny", "base", "small", "medium", "large-v2", "large-v3", "turbo"}
)


def is_local_asr_model(model: str) -> bool:
    return (model or "").strip().lower() in LOCAL_ASR_MODELS


def normalize_asr_model(raw: str | None) -> str:
    if raw is None or str(raw).strip() == "":
        return "local"
    model = str(raw).strip()
    if model.lower() in ("off", "disabled", "none"):
        return ""
    return model


def _load_asr_model() -> str:
    return normalize_asr_model(os.getenv("LLM_ASR_MODEL"))


def _load_local_engine() -> str:
    raw = os.getenv("LLM_ASR_LOCAL_ENGINE", "auto").strip().lower() or "auto"
    if raw in ("auto", "sensevoice", "whisper"):
        return raw
    return "auto"


def _load_whisper_size() -> str:
    raw = os.getenv("LLM_ASR_WHISPER_SIZE", "small").strip().lower() or "small"
    if raw not in _WHISPER_SIZES:
        return "small"
    return raw


def _load_asr_cloud_fallback() -> str:
    raw = os.getenv("LLM_ASR_CLOUD_FALLBACK")
    if raw is None or raw.strip() == "":
        return "qwen3-asr-flash"
    model = raw.strip()
    if model.lower() in ("off", "disabled", "none"):
        return ""
    return model


def _load_access_code() -> str:
    raw = os.getenv("ACCESS_CODE")
    if raw is None or raw.strip() == "":
        return "maxim"
    code = raw.strip()
    if code.lower() in ("off", "disabled", "none"):
        return ""
    return code


settings = load_settings()


def thinking_request_extras(
    base_url: str, model: str, thinking_enabled: bool, reasoning_effort: str = "high"
) -> dict:
    """各家"思考模式"专用参数。会随模型/接口自动选择正确的字段名。

    - DeepSeek V4：thinking={type:enabled/disabled} (+ reasoning_effort)
      见 https://api-docs.deepseek.com/guides/thinking_mode
    - 通义千问 / 百炼（DashScope 兼容模式）：enable_thinking=true/false
      见 https://help.aliyun.com/zh/model-studio/deep-thinking
      注意：Qwen3 系模型默认可能开启思考、且很慢，必须显式关闭。
    - 其他服务商：不加任何字段。
    """
    u = (base_url or "").lower()
    m = (model or "").lower()
    is_deepseek = "deepseek.com" in u or m.startswith("deepseek-")
    is_glm = "z.ai" in u or "bigmodel" in u or m.startswith("glm-")
    is_qwen = (
        "dashscope" in u
        or "aliyuncs" in u
        or m.startswith("qwen")
    )
    if is_glm:
        effort = reasoning_effort if reasoning_effort in ("low", "high", "max") else "high"
        return {"thinking": {"type": "enabled"}, "reasoning_effort": effort}
    if is_deepseek:
        if thinking_enabled:
            return {"thinking": {"type": "enabled"}, "reasoning_effort": reasoning_effort}
        return {"thinking": {"type": "disabled"}}
    if is_qwen:
        # DashScope 兼容模式接受把 enable_thinking 放在请求体顶层。
        return {"enable_thinking": bool(thinking_enabled)}
    return {}


def teaching_request_extras(settings: Settings) -> dict:
    return thinking_request_extras(
        settings.base_url, settings.model, settings.thinking_enabled, settings.reasoning_effort
    )
