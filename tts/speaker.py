from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from core.config import AppConfig


class Speaker:
    def __init__(self, config: AppConfig):
        self.config = config
        self._lock = threading.Lock()
        self._pyttsx3_engine = None

    def speak(self, text: str) -> str:
        if not self.config.voice_enabled or not text.strip():
            return "Voice disabled."

        with self._lock:
            errors: list[str] = []
            if self.config.piper_model_path:
                try:
                    return self._speak_with_piper(text)
                except Exception as exc:  # pragma: no cover - best effort fallback
                    errors.append(f"Piper failed: {exc}")

            if platform.system() == "Windows":
                try:
                    return self._speak_with_windows_sapi(text)
                except Exception as exc:  # pragma: no cover - best effort fallback
                    errors.append(f"Windows SAPI failed: {exc}")

            try:
                return self._speak_with_pyttsx3(text)
            except Exception as exc:  # pragma: no cover - best effort fallback
                errors.append(f"pyttsx3 failed: {exc}")
                return "TTS failed: " + " | ".join(errors)

    def _speak_with_piper(self, text: str) -> str:
        model_path = Path(self.config.piper_model_path)
        if not model_path.exists():
            raise FileNotFoundError(model_path)

        piper_exe = shutil.which("piper") or shutil.which("piper.exe")
        if not piper_exe:
            raise RuntimeError("Piper executable not found in PATH")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            output_path = Path(tmp.name)

        subprocess.run(
            [piper_exe, "--model", str(model_path), "--output_file", str(output_path)],
            input=text.encode("utf-8"),
            check=True,
        )

        self._play_wave(output_path)
        return "Spoken with Piper."

    def _speak_with_windows_sapi(self, text: str) -> str:
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            raise RuntimeError("PowerShell not found")

        escaped = text.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = 0; "
            f"$s.Speak('{escaped}');"
        )
        subprocess.run(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return "Spoken with Windows SAPI."

    def _speak_with_pyttsx3(self, text: str) -> str:
        import pyttsx3  # type: ignore

        if self._pyttsx3_engine is None:
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", 190)
        self._pyttsx3_engine.say(text)
        self._pyttsx3_engine.runAndWait()
        return "Spoken with pyttsx3."

    def _play_wave(self, path: Path) -> None:
        try:
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME)
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
