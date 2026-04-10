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
        self._current_process = None
        self._last_backend = ''
        self._interrupt_requested = False

    def speak(self, text: str) -> str:
        if not self.config.voice_enabled or not text.strip():
            return "Voice disabled."

        with self._lock:
            errors: list[str] = []
            self._last_backend = ''
            self._interrupt_requested = False
            if self.config.piper_model_path:
                try:
                    self._last_backend = 'piper'
                    return self._speak_with_piper(text)
                except InterruptedError:
                    return "Speech interrupted."
                except Exception as exc:  # pragma: no cover - best effort fallback
                    errors.append(f"Piper failed: {exc}")

            if platform.system() == "Windows":
                try:
                    self._last_backend = 'windows_sapi'
                    return self._speak_with_windows_sapi(text)
                except InterruptedError:
                    return "Speech interrupted."
                except Exception as exc:  # pragma: no cover - best effort fallback
                    errors.append(f"Windows SAPI failed: {exc}")

            try:
                self._last_backend = 'pyttsx3'
                return self._speak_with_pyttsx3(text)
            except InterruptedError:
                return "Speech interrupted."
            except Exception as exc:  # pragma: no cover - best effort fallback
                errors.append(f"pyttsx3 failed: {exc}")
                return "TTS failed: " + " | ".join(errors)

    def can_interrupt(self) -> bool:
        return True

    def stop(self) -> str:
        self._interrupt_requested = True
        stopped = False
        proc = self._current_process
        if proc is not None:
            try:
                proc.terminate()
                stopped = True
            except Exception:
                pass
            finally:
                self._current_process = None
        if self._pyttsx3_engine is not None:
            try:
                self._pyttsx3_engine.stop()
                stopped = True
            except Exception:
                pass
        return "Speech interrupted." if stopped else "No active speech to interrupt."

    def _speak_with_piper(self, text: str) -> str:
        model_path = Path(self.config.piper_model_path)
        if not model_path.exists():
            raise FileNotFoundError(model_path)

        piper_exe = shutil.which("piper") or shutil.which("piper.exe")
        if not piper_exe:
            raise RuntimeError("Piper executable not found in PATH")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            output_path = Path(tmp.name)

        proc = subprocess.Popen(
            [piper_exe, "--model", str(model_path), "--output_file", str(output_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._current_process = proc
        proc.communicate(input=text.encode("utf-8"))
        self._current_process = None
        if self._interrupt_requested:
            raise InterruptedError()
        if proc.returncode not in (0, None):
            raise RuntimeError(f"Piper exited with code {proc.returncode}")

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
        proc = subprocess.Popen(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._current_process = proc
        return_code = proc.wait()
        self._current_process = None
        if self._interrupt_requested:
            raise InterruptedError()
        if return_code not in (0, None):
            raise RuntimeError(f"PowerShell speech exited with code {return_code}")
        return "Spoken with Windows SAPI."

    def _speak_with_pyttsx3(self, text: str) -> str:
        import pyttsx3  # type: ignore

        if self._pyttsx3_engine is None:
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", 190)
        self._pyttsx3_engine.say(text)
        self._pyttsx3_engine.runAndWait()
        if self._interrupt_requested:
            raise InterruptedError()
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
