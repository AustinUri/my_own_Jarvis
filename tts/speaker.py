from __future__ import annotations

import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from core.config import AppConfig

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(?:[\"'”’)]*)\s+")


class Speaker:
    """Serialized TTS with sentence-completion guarantees.

    V28.1 serializes and awaits every TTS chunk. Normal follow-up input is queued by
    the orchestrator and does not cancel playback. Only an explicit forced stop may
    terminate an active chunk.
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self._lock = threading.Lock()
        self._pyttsx3_engine = None
        self._current_process = None
        self._last_backend = ''
        self._interrupt_requested = False
        self._force_interrupt_requested = False

    def speak(self, text: str) -> str:
        if not self.config.voice_enabled or not text.strip():
            return "Voice disabled."

        with self._lock:
            errors: list[str] = []
            self._last_backend = ''
            self._interrupt_requested = False
            self._force_interrupt_requested = False
            chunks = self._sentence_chunks(text)
            pause = max(0, int(getattr(self.config, "tts_sentence_pause_ms", 70))) / 1000.0
            retry_once = bool(getattr(self.config, "tts_retry_once", True))

            for index, chunk in enumerate(chunks):
                if index > 0 and self._interrupt_requested:
                    return "Speech interrupted after sentence."
                if index > 0 and pause:
                    time.sleep(pause)

                attempts = 2 if retry_once else 1
                last_error: Exception | None = None
                for attempt in range(attempts):
                    try:
                        self._speak_one(chunk)
                        last_error = None
                        break
                    except InterruptedError:
                        return "Speech interrupted."
                    except Exception as exc:  # pragma: no cover - best effort fallback
                        last_error = exc
                        if attempt + 1 < attempts:
                            time.sleep(0.08)
                if last_error is not None:
                    errors.append(str(last_error))
                    break

            if errors:
                return "TTS failed: " + " | ".join(errors)
            return f"Spoken with {self._last_backend or 'TTS'}."

    def _speak_one(self, text: str) -> None:
        errors: list[str] = []
        if self.config.piper_model_path:
            try:
                self._last_backend = 'piper'
                self._speak_with_piper(text)
                return
            except InterruptedError:
                raise
            except Exception as exc:
                errors.append(f"Piper failed: {exc}")

        if platform.system() == "Windows":
            try:
                self._last_backend = 'windows_sapi'
                self._speak_with_windows_sapi(text)
                return
            except InterruptedError:
                raise
            except Exception as exc:
                errors.append(f"Windows SAPI failed: {exc}")

        try:
            self._last_backend = 'pyttsx3'
            self._speak_with_pyttsx3(text)
            return
        except InterruptedError:
            raise
        except Exception as exc:
            errors.append(f"pyttsx3 failed: {exc}")
            raise RuntimeError(" | ".join(errors))

    def can_interrupt(self) -> bool:
        return True

    def stop(self, force: bool = False) -> str:
        """Request speech interruption.

        By default V28 finishes the sentence currently being played, then stops before
        the next sentence. `force=True` is reserved for shutdown/emergency behavior.
        """
        self._interrupt_requested = True
        finish_sentence = bool(getattr(self.config, "speech_finish_sentence_on_interrupt", True))
        if finish_sentence and not force:
            return "Interruption queued; finishing the current sentence first."

        self._force_interrupt_requested = True
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

    @staticmethod
    def _sentence_chunks(text: str, max_chars: int = 280) -> list[str]:
        """Return TTS-safe chunks without dropping any text.

        Sentence boundaries are preferred. If a single sentence is unusually long,
        split it at a clause/space boundary so Windows SAPI is never handed one huge
        buffer. Every chunk is still spoken serially and awaited to completion.
        """
        cleaned = " ".join((text or "").split())
        if not cleaned:
            return []
        sentences = [part.strip() for part in _SENTENCE_BOUNDARY.split(cleaned) if part.strip()] or [cleaned]
        chunks: list[str] = []
        for sentence in sentences:
            remaining = sentence
            while len(remaining) > max_chars:
                window = remaining[: max_chars + 1]
                cut = max(
                    window.rfind("; "),
                    window.rfind(": "),
                    window.rfind(", "),
                    window.rfind(" — "),
                    window.rfind(" - "),
                    window.rfind(" "),
                )
                if cut < int(max_chars * 0.55):
                    cut = max_chars
                part = remaining[:cut].strip()
                if part:
                    chunks.append(part)
                remaining = remaining[cut:].strip(" ,;:—-")
            if remaining:
                chunks.append(remaining)
        return chunks

    def _speak_with_piper(self, text: str) -> None:
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
        if self._force_interrupt_requested:
            raise InterruptedError()
        if proc.returncode not in (0, None):
            raise RuntimeError(f"Piper exited with code {proc.returncode}")

        self._play_wave(output_path)

    def _speak_with_windows_sapi(self, text: str) -> None:
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
        if self._force_interrupt_requested:
            raise InterruptedError()
        if return_code not in (0, None):
            raise RuntimeError(f"PowerShell speech exited with code {return_code}")

    def _speak_with_pyttsx3(self, text: str) -> None:
        import pyttsx3  # type: ignore

        if self._pyttsx3_engine is None:
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", 190)
        self._pyttsx3_engine.say(text)
        self._pyttsx3_engine.runAndWait()
        if self._force_interrupt_requested:
            raise InterruptedError()

    def _play_wave(self, path: Path) -> None:
        try:
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME)
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
