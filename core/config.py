from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppConfig:
    config_version: int = 281

    # AI / agent provider
    ai_provider: str = "LM Studio"
    ai_base_url: str = "http://127.0.0.1:1234/v1"
    ai_model_name: str = "jarvis-qwen"
    ai_api_key: str = "lm-studio"
    ai_timeout_seconds: float = 60.0
    ai_max_tool_rounds: int = 6
    ai_temperature: float = 0.35
    conversation_history_turns: int = 12

    language_mode: str = "English"
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
    command_max_seconds: float = 14.0
    command_silence_seconds: float = 2.2
    command_min_seconds: float = 1.6
    command_preroll_seconds: float = 0.45
    accent_assist_enabled: bool = True
    tavily_api_key: str = ""
    searxng_base_url: str = "http://localhost:8888"
    web_max_results: int = 10
    web_timeout_seconds: float = 18.0
    web_research_depth: str = "deep"
    camera_vision_enabled: bool = True
    camera_frame_interval_seconds: float = 1.5

    # v25 managed runtime / services
    auto_manage_services: bool = True
    auto_start_lm_studio: bool = True
    auto_load_ai_model: bool = True
    ai_local_model_key: str = "qwen/qwen3.5-9b"
    ai_context_length: int = 16384
    auto_start_docker_desktop: bool = True
    auto_start_searxng: bool = True
    service_health_interval_seconds: float = 45.0

    # Daily intelligence
    briefing_enabled: bool = True
    briefing_on_workspace_open: bool = True
    briefing_announce_voice: bool = True
    briefing_include_israel: bool = True
    briefing_include_idf: bool = True
    briefing_include_champions_league: bool = True
    briefing_include_f1: bool = True
    briefing_include_f1_learning: bool = True
    briefing_include_ai: bool = True
    briefing_include_football: bool = True
    briefing_include_world: bool = True
    briefing_include_weather: bool = True
    briefing_include_calendar: bool = True
    weather_location: str = "Netanya, Israel"

    # Google Calendar OAuth desktop client JSON. Leave blank to use %APPDATA%\Jarvis\credentials\google_calendar_client.json
    google_calendar_client_secret_path: str = ""


    # v26 secure phone companion foundation. The phone bridge itself listens only
    # on localhost; remote access is expected to be provided by Tailscale Serve.
    phone_bridge_enabled: bool = True
    phone_bridge_port: int = 8766
    phone_poll_timeout_seconds: float = 22.0
    phone_command_timeout_seconds: float = 30.0
    phone_pairing_minutes: int = 5
    prefer_phone_calendar: bool = True
    google_calendar_fallback_enabled: bool = True


    # v27 specialist-agent foundation. Profiles are lightweight identities that
    # share the same local model; the resource governor prevents uncontrolled fan-out.
    agent_mesh_enabled: bool = True
    agent_max_active_specialists: int = 6
    agent_max_parallel_llm: int = 2
    resource_governor_enabled: bool = True
    resource_ram_warn_percent: float = 75.0
    resource_ram_stop_percent: float = 85.0
    resource_vram_warn_percent: float = 85.0
    resource_vram_stop_percent: float = 92.0
    resource_gpu_temp_warn_c: float = 80.0
    resource_gpu_temp_stop_c: float = 84.0

    # Personality / behavior
    tone_mode: str = "Respectful"
    address_name: str = "sir"
    verbosity_mode: str = "Brief"
    ask_before_open_related_apps: bool = True
    auto_open_explicit_only: bool = True

    # Background runtime
    minimize_to_tray_on_close: bool = True
    start_with_windows: bool = True
    start_minimized: bool = False
    keep_assistant_running_in_tray: bool = True

    # Conversation mode
    conversation_mode_enabled: bool = True
    conversation_timeout_seconds: float = 35.0
    conversation_followup_max_turns: int = 5
    interruption_enabled: bool = False
    speech_finish_sentence_on_interrupt: bool = True
    tts_sentence_pause_ms: int = 70
    tts_retry_once: bool = True

    # v28 phone and spatial-vision behavior
    phone_dns_fallback_enabled: bool = True
    hololab_enabled: bool = True

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

        old_version = int(data.get("config_version") or 0)
        cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        if old_version < 24:
            # v24 recorder/research migration. Preserve deliberate custom values,
            # but upgrade old defaults that caused clipped endings and shallow web answers.
            if float(data.get("command_silence_seconds", 1.4)) <= 1.45:
                cfg.command_silence_seconds = 2.2
            if float(data.get("command_max_seconds", 9.0)) <= 9.1:
                cfg.command_max_seconds = 14.0
            if int(data.get("web_max_results", 5)) <= 5:
                cfg.web_max_results = 10
            if float(data.get("web_timeout_seconds", 12.0)) <= 12.1:
                cfg.web_timeout_seconds = 18.0
            cfg.config_version = 24
        if old_version < 25:
            cfg.config_version = 25
            # v25 makes the runtime app-like: services are managed in the background
            # and start-with-Windows is enabled by default for fresh/older configs.
            if "start_with_windows" not in data:
                cfg.start_with_windows = True
        if old_version < 26:
            cfg.config_version = 26
            # v26 defaults weather to Netanya and makes native phone calendar the
            # preferred source when a companion is connected.
            if not str(data.get("weather_location") or "").strip():
                cfg.weather_location = "Netanya, Israel"
        if old_version < 27:
            cfg.config_version = 27
            # v27 keeps the local model shared between specialist identities and
            # starts with conservative limits suitable for an 8 GB class GPU.
            cfg.agent_max_parallel_llm = min(2, max(1, int(getattr(cfg, "agent_max_parallel_llm", 2))))
            cfg.agent_max_active_specialists = min(6, max(2, int(getattr(cfg, "agent_max_active_specialists", 6))))
        if old_version < 28:
            cfg.config_version = 28
            # v28 never blocks the foreground assistant merely because background
            # fan-out is throttled, and speech interruption is deferred until the
            # current sentence has completed.
            cfg.speech_finish_sentence_on_interrupt = True
            cfg.phone_dns_fallback_enabled = True
            cfg.hololab_enabled = True
        if old_version < 281:
            # v28.1 hotfix: English-first STT avoids multilingual Whisper
            # interpreting accented English as Hebrew unless bilingual Auto mode
            # is explicitly selected later in Settings.
            cfg.config_version = 281
            if str(data.get("language_mode") or "Auto") == "Auto":
                cfg.language_mode = "English"
            # Normal follow-up input is queued until the spoken reply is complete.
            cfg.interruption_enabled = False
        if not str(cfg.searxng_base_url).strip():
            cfg.searxng_base_url = "http://localhost:8888"
        if not str(cfg.ai_base_url).strip():
            cfg.ai_base_url = "http://127.0.0.1:1234/v1"
        if not str(cfg.ai_model_name).strip():
            cfg.ai_model_name = "jarvis-qwen"
        return cfg

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
