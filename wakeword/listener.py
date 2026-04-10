from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

from core.audio_utils import resolve_input_device


@dataclass
class WakeWordEvent:
    phrase: str = "Hey Jarvis"
    score: float = 0.0


class WakeWordListener:
    """Background microphone listener powered by openWakeWord + sounddevice."""

    def __init__(self, threshold: float = 0.15, mic_name: str = 'Default', vad_threshold: float = 0.18):
        self.threshold = threshold
        self.mic_name = mic_name
        self.vad_threshold = vad_threshold
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False
        self._cooldown_until = 0.0
        self._on_detect: Callable[[WakeWordEvent], None] | None = None
        self._on_log: Callable[[str], None] | None = None

    @property
    def running(self) -> bool:
        return self._running

    def start(
        self,
        on_detect: Callable[[WakeWordEvent], None],
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        if self._running:
            return
        self._on_detect = on_detect
        self._on_log = on_log
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None
        self._running = False

    def _log(self, message: str) -> None:
        if self._on_log is not None:
            self._on_log(message)

    def _worker(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd
            import openwakeword
            from openwakeword.model import Model
        except Exception as exc:
            self._log(f"Wake word setup failed: {exc}")
            self._running = False
            return

        try:
            openwakeword.utils.download_models()
            model = Model(vad_threshold=self.vad_threshold)
            blocksize = 1280  # 80 ms at 16 kHz
            device = resolve_input_device(self.mic_name)
            self._log(f'Wake word mic: {self.mic_name}')

            loose_threshold = max(0.06, min(self.threshold * 0.82, self.threshold - 0.005))
            consecutive_loose_hits = 0
            best_recent_score = 0.0
            last_debug_at = 0.0

            def callback(indata, frames, time_info, status):
                nonlocal consecutive_loose_hits, best_recent_score, last_debug_at
                if self._stop_event.is_set():
                    raise sd.CallbackStop()
                if status:
                    self._log(f'Wake stream status: {status}')
                    return
                if time.time() < self._cooldown_until:
                    return
                pcm = np.copy(indata[:, 0]).astype(np.int16)
                predictions = model.predict(pcm)
                best_name = None
                best_score = 0.0
                for name, score in predictions.items():
                    model_name = str(name).lower().replace('_', ' ')
                    score_value = float(score)
                    if 'jarvis' in model_name and score_value > best_score:
                        best_name = name
                        best_score = score_value

                if best_score >= loose_threshold:
                    consecutive_loose_hits += 1
                elif consecutive_loose_hits > 0:
                    consecutive_loose_hits -= 1

                best_recent_score = max(best_recent_score * 0.95, best_score)
                now = time.time()
                if best_recent_score >= max(0.06, loose_threshold * 0.70) and (now - last_debug_at) > 0.8:
                    self._log(f'Wake score: {best_recent_score:.2f} (threshold {self.threshold:.2f})')
                    last_debug_at = now

                detected = False
                if best_name and best_score >= self.threshold:
                    detected = True
                elif best_name and best_score >= loose_threshold and consecutive_loose_hits >= 2:
                    detected = True
                elif best_name and best_recent_score >= max(loose_threshold, self.threshold * 0.92) and consecutive_loose_hits >= 2:
                    detected = True

                if detected:
                    self._cooldown_until = time.time() + 1.2
                    consecutive_loose_hits = 0
                    best_recent_score = 0.0
                    if self._on_detect is not None:
                        self._on_detect(WakeWordEvent(phrase='Hey Jarvis', score=best_score))

            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='int16',
                blocksize=blocksize,
                device=device,
                callback=callback,
            ):
                self._log(
                    f'Wake word listener armed at threshold {self.threshold:.2f} '
                    f'(extra sensitive mode on). Say "Hey Jarvis".'
                )
                while not self._stop_event.is_set():
                    time.sleep(0.1)
        except Exception as exc:
            self._log(f"Wake word listener failed: {exc}")
        finally:
            self._running = False
