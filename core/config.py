from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppConfig:
    # AI / agent provider
    ai_provider: str = "LM Studio"
    ai_base_url: str = "http://127.0.0.1:1234/v1"
    ai_model_name: str = "jarvis-qwen"
    ai_api_key: str = "lm-studio"
    ai_timeout_seconds: float = 60.0
    ai_max_tool_rounds: int = 6
    ai_temperature: float = 0.35
    conversation_history_turns: int = 12

    language_mode: str = "Auto"
    mic_name: str = "Default"
    speaker_name: str = "Default"
    voice_enabled: bool = True
    assistant_enabled: bool = True
    wake_word_enabled: bool = True
    require_confirmation: bool = True
    piper_model_path: str = ""
    notes_dir: str = "notes"
    prefer_short_replies: bool = True
    stt_model_name: str = "medium"
    stt_backend: str = "faster-whisper"
    whisper_cpp_path: str = ""
    wake_word_threshold: float = 0.15
    wake_vad_threshold: float = 0.18
    silence_threshold: float = 0.009
    command_max_seconds: float = 9.0
    command_silence_seconds: float = 1.4
    command_min_seconds: float = 1.8
    command_preroll_seconds: float = 0.45
    accent_assist_enabled: bool = True
    tavily_api_key: str = ""
    searxng_base_url: str = "http://localhost:8888"
    web_max_results: int = 5
    web_timeout_seconds: float = 12.0

    # Personality / behavior
    tone_mode: str = "Respectful"
    address_name: str = "sir"
    verbosity_mode: str = "Brief"
    ask_before_open_related_apps: bool = True
    auto_open_explicit_only: bool = True

    # Background runtime
    minimize_to_tray_on_close: bool = True
    start_with_windows: bool = False
    start_minimized: bool = False
    keep_assistant_running_in_tray: bool = True

    # Conversation mode
    conversation_mode_enabled: bool = True
    conversation_timeout_seconds: float = 35.0
    conversation_followup_max_turns: int = 5
    interruption_enabled: bool = True

    # Wake phrases groundwork
    wake_phrases: str = "Hey Jarvis, Jarvis, Wake up Jarvis"

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()

        # Backward compatibility with the old Ollama-era config.
        if "model_name" in data and "ai_model_name" not in data:
            data["ai_model_name"] = "jarvis-qwen"
        if "ai_base_url" not in data:
            data["ai_base_url"] = "http://127.0.0.1:1234/v1"
        if "ai_provider" not in data:
            data["ai_provider"] = "LM Studio"

        cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        if not str(cfg.searxng_base_url).strip():
            cfg.searxng_base_url = "http://localhost:8888"
        if not str(cfg.ai_base_url).strip():
            cfg.ai_base_url = "http://127.0.0.1:1234/v1"
        if not str(cfg.ai_model_name).strip():
            cfg.ai_model_name = "jarvis-qwen"
        return cfg

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
