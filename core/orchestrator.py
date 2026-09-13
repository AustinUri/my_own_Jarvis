from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.config import AppConfig
from core.events import AssistantReply, AssistantState
from core.resource_governor import ResourceGovernor
from agent.jarvis_agent import JarvisAgent
from stt.whisper_engine import WhisperEngine
from tools.registry import ToolRegistry
from tts.speaker import Speaker
from wakeword.listener import WakeWordEvent, WakeWordListener

WAKEWORD_PREFIX_RE = re.compile(
    r"^\s*(?:hey\s+jarvis|jarvis|wake\s+up\s+jarvis|היי\s+ג[׳']?רוויס|ג[׳']?רוויס)\s*[,，:;\-]?\s*",
    re.IGNORECASE,
)
STOP_LISTENING_RE = re.compile(
    r"\b(?:stop listening|goodbye|go to sleep|that's all|that is all|cancel|thanks goodbye)\b|(?:תפסיק להקשיב|להפסיק להקשיב|להתראות|לך לישון|זה הכל|תודה ביי)",
    re.IGNORECASE,
)


class Orchestrator(QObject):
    state_changed = Signal(str)
    transcript_ready = Signal(str, str)
    response_ready = Signal(str, str)
    spoken_text_ready = Signal(str)
    log_ready = Signal(str)
    error_raised = Signal(str)

    def __init__(self, base_dir: Path, config: AppConfig):
        super().__init__()
        self.base_dir = base_dir
        self.config = config
        self.tools = ToolRegistry(base_dir, config)
        self.agent = JarvisAgent(config, self.tools, log=self.log_ready.emit)
        self.resource_governor = ResourceGovernor(config)
        self.speaker = Speaker(config)
        self.aliases_path = base_dir / 'memory' / 'custom_aliases.json'
        self._ensure_custom_aliases_file()
        self.whisper = WhisperEngine(
            model_name=config.stt_model_name,
            silence_threshold=config.silence_threshold,
            mic_name=config.mic_name,
            language_mode=config.language_mode,
            accent_assist_enabled=config.accent_assist_enabled,
            aliases_path=self.aliases_path,
            backend=config.stt_backend,
            whisper_cpp_path=config.whisper_cpp_path,
            base_dir=base_dir,
        )
        self.wake_listener = WakeWordListener(
            threshold=config.wake_word_threshold,
            mic_name=config.mic_name,
            vad_threshold=config.wake_vad_threshold,
        )
        self.whisper.command_min_seconds = config.command_min_seconds
        self.whisper.command_preroll_seconds = config.command_preroll_seconds
        self._busy = False
        self._agent_lock = threading.RLock()
        self._enabled = config.assistant_enabled
        self._state = AssistantState.IDLE if config.assistant_enabled else AssistantState.DISABLED
        self._queued_text_after_interrupt: str | None = None
        self._queued_voice_capture_after_interrupt = False
        self._conversation_active = False
        self._conversation_deadline = 0.0
        self._conversation_turns_left = 0
        self._conversation_source = ''
        if self._enabled and self.config.wake_word_enabled:
            self._start_wake_word_listener()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def shutdown(self) -> None:
        self._end_conversation_session()
        self._stop_wake_word_listener()

    def reload_runtime_config(self) -> None:
        self.whisper.model_name = self.config.stt_model_name
        self.whisper.silence_threshold = self.config.silence_threshold
        self.whisper.mic_name = self.config.mic_name
        self.whisper.language_mode = self.config.language_mode
        self.whisper.accent_assist_enabled = self.config.accent_assist_enabled
        self.whisper.backend = self.config.stt_backend
        self.whisper.whisper_cpp_path = self.config.whisper_cpp_path
        self.whisper.command_min_seconds = self.config.command_min_seconds
        self.whisper.command_preroll_seconds = self.config.command_preroll_seconds
        self.whisper._model = None
        self.tools.config = self.config
        self.agent.config = self.config
        self.agent.reload_config()
        self.speaker.config = self.config
        self.wake_listener.threshold = self.config.wake_word_threshold
        self.wake_listener.mic_name = self.config.mic_name
        self.wake_listener.vad_threshold = self.config.wake_vad_threshold
        self.log_ready.emit(
            f'Runtime config reloaded. Mic: {self.config.mic_name} | '
            f'STT: {self.whisper.active_backend_label()} | Tone: {self.config.tone_mode}'
        )
        if self._enabled and self.config.wake_word_enabled and not self._busy:
            self._stop_wake_word_listener()
            self._start_wake_word_listener()

    def _ensure_custom_aliases_file(self) -> None:
        self.aliases_path.parent.mkdir(parents=True, exist_ok=True)
        if self.aliases_path.exists():
            return
        alias_seed = {
            'krome': 'chrome',
            'crome': 'chrome',
            'spotifai': 'spotify',
            'you tube': 'youtube',
            'git hub': 'github',
            'g mail': 'gmail',
            'chat gpt': 'chatgpt',
            'jarvice': 'jarvis',
            'wake up services': 'wake up jarvis',
        }
        try:
            self.aliases_path.write_text(json.dumps(alias_seed, ensure_ascii=False, indent=2), encoding='utf-8')
        except OSError:
            pass

    def _configured_wake_phrases(self) -> list[str]:
        raw = self.config.wake_phrases or 'Hey Jarvis'
        phrases = [part.strip() for part in raw.split(',') if part.strip()]
        return phrases or ['Hey Jarvis']

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.config.assistant_enabled = enabled
        if not enabled:
            self._end_conversation_session()
        self._set_state(AssistantState.IDLE if enabled else AssistantState.DISABLED)
        if enabled and self.config.wake_word_enabled:
            self._start_wake_word_listener()
        else:
            self._stop_wake_word_listener()
        self.log_ready.emit('Assistant started.' if enabled else 'Assistant stopped.')

    def toggle_voice(self) -> None:
        self.config.voice_enabled = not self.config.voice_enabled
        self.log_ready.emit('Voice enabled.' if self.config.voice_enabled else 'Voice muted.')

    def toggle_wake_word(self) -> None:
        self.config.wake_word_enabled = not self.config.wake_word_enabled
        if self.config.wake_word_enabled and self._enabled:
            self._start_wake_word_listener()
            self.log_ready.emit('Wake word enabled.')
        else:
            self._stop_wake_word_listener()
            self.log_ready.emit('Wake word disabled.')

    def process_user_text(self, text: str) -> None:
        if not self._enabled:
            self.log_ready.emit('Assistant is disabled.')
            return
        if not text.strip():
            return
        if self._busy:
            if self._state == AssistantState.SPEAKING:
                self._queued_text_after_interrupt = text
                self.log_ready.emit('Follow-up queued. JARVIS will finish the current spoken reply first.')
                return
            self.log_ready.emit('Jarvis is already busy.')
            return
        self._busy = True
        self._stop_wake_word_listener()
        threading.Thread(target=self._run_pipeline, args=(text, True, True), daemon=True).start()

    def process_push_to_talk(self) -> None:
        if not self._enabled:
            self.log_ready.emit('Assistant is disabled.')
            return
        if self._busy:
            if self._state == AssistantState.SPEAKING:
                self._queued_voice_capture_after_interrupt = True
                self.log_ready.emit('Push-to-talk queued. JARVIS will finish speaking, then listen.')
                return
            self.log_ready.emit('Jarvis is already busy.')
            return
        self._busy = True
        self._stop_wake_word_listener()
        threading.Thread(target=self._capture_then_process_voice, args=(False,), daemon=True).start()

    def test_voice(self, text: str = 'Jarvis voice test. Audio output is working.') -> None:
        if self._busy:
            self.log_ready.emit('Jarvis is already busy.')
            return
        self._busy = True
        self._stop_wake_word_listener()
        threading.Thread(target=self._run_voice_test, args=(text,), daemon=True).start()

    def test_microphone(self) -> None:
        if not self._enabled:
            self.log_ready.emit('Assistant is disabled.')
            return
        if self._busy:
            self.log_ready.emit('Jarvis is already busy.')
            return
        self._busy = True
        self._stop_wake_word_listener()
        threading.Thread(target=self._run_microphone_test, daemon=True).start()


    def interrupt_current_reply(self, reason: str = 'Explicit stop requested.') -> bool:
        """Emergency/explicit stop only.

        Normal text/PTT follow-ups are queued and never cancel speech in v28.1.
        """
        if self._state != AssistantState.SPEAKING:
            return False
        backend_message = self.speaker.stop(force=True)
        self.log_ready.emit(reason)
        self.log_ready.emit(backend_message)
        return True

    def _handle_interrupt_queue(self, restart_listener: bool) -> bool:
        queued_text = self._queued_text_after_interrupt
        queued_voice = self._queued_voice_capture_after_interrupt
        self._queued_text_after_interrupt = None
        self._queued_voice_capture_after_interrupt = False
        if queued_text:
            self.log_ready.emit('Running queued follow-up command now.')
            self._run_pipeline(queued_text, restart_listener=restart_listener, finalize=True)
            return True
        if queued_voice:
            self.log_ready.emit('Listening for the queued follow-up now.')
            self._capture_then_process_voice(False)
            return True
        return False

    def _start_wake_word_listener(self) -> None:
        if not self.config.wake_word_enabled or not self._enabled or self._busy:
            return
        if self.wake_listener.running:
            return
        self.wake_listener.threshold = self.config.wake_word_threshold
        self.wake_listener.mic_name = self.config.mic_name
        self.wake_listener.vad_threshold = self.config.wake_vad_threshold
        phrases = ', '.join(self._configured_wake_phrases())
        self.log_ready.emit(f'Wake runtime armed. Preferred phrases: {phrases}.')
        if len(self._configured_wake_phrases()) > 1:
            self.log_ready.emit('Primary hotword detection is still strongest on “Hey Jarvis”. Extra phrases are groundwork for later tuning.')
        self.wake_listener.start(self._on_wake_word_detected, self.log_ready.emit)

    def _stop_wake_word_listener(self) -> None:
        if self.wake_listener.running:
            self.wake_listener.stop()

    def _conversation_enabled(self) -> bool:
        return bool(self.config.conversation_mode_enabled)

    def _begin_conversation_session(self, source: str) -> None:
        if not self._conversation_enabled():
            return
        self._conversation_active = True
        self._conversation_source = source
        self._conversation_deadline = time.monotonic() + max(10.0, float(self.config.conversation_timeout_seconds))
        self._conversation_turns_left = max(1, int(self.config.conversation_followup_max_turns))
        self.log_ready.emit(
            f'Conversation mode active for {int(self.config.conversation_timeout_seconds)} seconds '
            f'with up to {self._conversation_turns_left} follow-up turn(s).'
        )

    def _refresh_conversation_session(self) -> None:
        if not self._conversation_active:
            return
        self._conversation_deadline = time.monotonic() + max(10.0, float(self.config.conversation_timeout_seconds))

    def _end_conversation_session(self, reason: str | None = None) -> None:
        was_active = self._conversation_active
        self._conversation_active = False
        self._conversation_deadline = 0.0
        self._conversation_turns_left = 0
        self._conversation_source = ''
        if was_active and reason:
            self.log_ready.emit(reason)

    def _conversation_should_continue(self) -> bool:
        if not self._conversation_active:
            return False
        if time.monotonic() >= self._conversation_deadline:
            return False
        if self._conversation_turns_left <= 0:
            return False
        return self._enabled

    def _capture_max_seconds(self) -> float:
        if not self._conversation_active:
            return max(self.config.command_min_seconds + 0.5, self.config.command_max_seconds)
        remaining = max(1.5, self._conversation_deadline - time.monotonic())
        return min(self.config.command_max_seconds, remaining)

    def _is_stop_listening_phrase(self, transcript: str) -> bool:
        lowered = transcript.strip().lower()
        if not lowered:
            return False
        return bool(STOP_LISTENING_RE.search(lowered))

    def _idle_acknowledgement(self) -> str:
        return 'Going back to standby, sir.' if self.config.tone_mode == 'Respectful' else 'Going back to standby.'

    def _miss_acknowledgement(self) -> str:
        return 'Sir, I did not catch that.' if self.config.tone_mode == 'Respectful' else "I didn't catch that."

    def _on_wake_word_detected(self, event: WakeWordEvent) -> None:
        if not self._enabled or self._busy:
            return
        self._busy = True
        self._set_state(AssistantState.LISTENING)
        self.log_ready.emit(f'Wake word detected ({event.score:.2f}). Listening now.')
        self._play_wake_beep()
        self._stop_wake_word_listener()
        threading.Thread(target=self._capture_then_process_voice, args=(True,), daemon=True).start()

    def _play_wake_beep(self) -> None:
        try:
            import winsound

            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass
            winsound.Beep(740, 120)
            winsound.Beep(980, 140)
            winsound.Beep(1220, 160)
        except Exception:
            try:
                from PySide6.QtWidgets import QApplication
                QApplication.beep()
            except Exception:
                pass

    def _capture_voice_text(self, prompt_message: str) -> tuple[str, str]:
        self._set_state(AssistantState.LISTENING)
        self.log_ready.emit(prompt_message)
        transcript, wav_path = self.whisper.transcribe_microphone_command(
            max_seconds=self._capture_max_seconds(),
            silence_seconds=self.config.command_silence_seconds,
            threshold=self.config.silence_threshold,
        )
        cleaned = WAKEWORD_PREFIX_RE.sub('', transcript).strip()
        transcript = cleaned or transcript.strip()
        return transcript, wav_path

    def _capture_then_process_voice(self, from_wake_word: bool) -> None:
        try:
            if from_wake_word:
                self._begin_conversation_session('wake')
                prompt = 'Listening for your command...'
            else:
                prompt = f'Push-to-talk recording started on {self.config.mic_name}.'
            transcript, wav_path = self._capture_voice_text(prompt)
            if not transcript:
                self.log_ready.emit('No command was captured after listening.')
                if self.config.voice_enabled:
                    miss = self._miss_acknowledgement()
                    self.spoken_text_ready.emit(miss)
                    self._set_state(AssistantState.SPEAKING)
                    backend = self.speaker.speak(miss)
                    self.log_ready.emit(backend)
                self._set_state(AssistantState.IDLE if self._enabled else AssistantState.DISABLED)
                return
            if self._is_stop_listening_phrase(transcript):
                ack = self._idle_acknowledgement()
                self.response_ready.emit(ack, 'en')
                self.spoken_text_ready.emit(ack)
                self._set_state(AssistantState.SPEAKING)
                backend = self.speaker.speak(ack)
                self.log_ready.emit(backend)
                self._set_state(AssistantState.IDLE if self._enabled else AssistantState.DISABLED)
                return
            self.log_ready.emit(f'Voice captured from {wav_path}. STT backend: {self.whisper.active_backend_label()}')
            self._refresh_conversation_session()
            self._run_pipeline(transcript, restart_listener=False, finalize=False)
            self._run_followup_loop()
        except Exception as exc:
            self._set_state(AssistantState.ERROR)
            self.error_raised.emit(str(exc))
            self.log_ready.emit(f'Voice input error: {exc}')
        finally:
            self._end_conversation_session()
            if self._enabled and self.config.wake_word_enabled:
                self._start_wake_word_listener()
            self._busy = False

    def _run_followup_loop(self) -> None:
        if not self._conversation_should_continue():
            return
        while self._conversation_should_continue():
            remaining = max(0, int(round(self._conversation_deadline - time.monotonic())))
            self.log_ready.emit(f'Conversation mode: listening for follow-up ({remaining}s left).')
            transcript, wav_path = self._capture_voice_text('Conversation mode is active. Listening for your follow-up...')
            if not transcript:
                self.log_ready.emit('Conversation follow-up timed out.')
                break
            if self._is_stop_listening_phrase(transcript):
                ack = self._idle_acknowledgement()
                self.response_ready.emit(ack, 'en')
                self.spoken_text_ready.emit(ack)
                self._set_state(AssistantState.SPEAKING)
                backend = self.speaker.speak(ack)
                self.log_ready.emit(backend)
                break
            self._conversation_turns_left -= 1
            self._refresh_conversation_session()
            self.log_ready.emit(f'Follow-up captured from {wav_path}. Turns left: {self._conversation_turns_left}')
            self._run_pipeline(transcript, restart_listener=False, finalize=False)

    def _run_microphone_test(self) -> None:
        try:
            self._set_state(AssistantState.LISTENING)
            self.log_ready.emit(f'Microphone test started on {self.config.mic_name}. Speak now.')
            transcript, wav_path = self.whisper.transcribe_microphone_command(max_seconds=5.0, silence_seconds=1.0, threshold=self.config.silence_threshold)
            language = self.agent.detect_language(transcript or '')
            self.transcript_ready.emit(transcript or '[nothing heard]', language)
            self.log_ready.emit(f'Mic test audio saved as {wav_path}.')
            if transcript:
                response = 'Sir, microphone test completed.' if self.config.tone_mode == 'Respectful' else 'Microphone test completed.'
                spoken = 'Sir, microphone looks good.' if self.config.tone_mode == 'Respectful' else 'Microphone looks good.'
                self.response_ready.emit(response, 'en')
                self.spoken_text_ready.emit(spoken)
                self._set_state(AssistantState.SPEAKING)
                backend = self.speaker.speak(spoken)
                self.log_ready.emit(backend)
            else:
                response = 'Sir, microphone test heard nothing.' if self.config.tone_mode == 'Respectful' else 'Microphone test heard nothing.'
                spoken = "Sir, I could not hear anything from the microphone." if self.config.tone_mode == 'Respectful' else "I couldn't hear anything from the microphone."
                self.response_ready.emit(response, 'en')
                self.log_ready.emit('Mic test heard nothing.')
                if self.config.voice_enabled:
                    self.spoken_text_ready.emit(spoken)
                    self._set_state(AssistantState.SPEAKING)
                    backend = self.speaker.speak(spoken)
                    self.log_ready.emit(backend)
        except Exception as exc:
            self._set_state(AssistantState.ERROR)
            self.error_raised.emit(str(exc))
            self.log_ready.emit(f'Microphone test failed: {exc}')
        finally:
            self._set_state(AssistantState.IDLE if self._enabled else AssistantState.DISABLED)
            if self._enabled and self.config.wake_word_enabled:
                self._start_wake_word_listener()
            self._busy = False

    def _run_voice_test(self, text: str) -> None:
        try:
            self.spoken_text_ready.emit(text)
            self._set_state(AssistantState.SPEAKING)
            backend = self.speaker.speak(text)
            self.log_ready.emit(backend)
            if backend.startswith('TTS failed'):
                self.error_raised.emit(backend)
        finally:
            time.sleep(0.05)
            self._set_state(AssistantState.IDLE if self._enabled else AssistantState.DISABLED)
            if self._enabled and self.config.wake_word_enabled:
                self._start_wake_word_listener()
            self._busy = False

    def _run_pipeline(self, text: str, restart_listener: bool, finalize: bool = True) -> None:
        try:
            self._set_state(AssistantState.LISTENING)
            self.log_ready.emit('Input received.')
            time.sleep(0.05)

            language = self.agent.detect_language(text)
            self._set_state(AssistantState.TRANSCRIBING)
            self.transcript_ready.emit(text, language)
            self.log_ready.emit('Transcript updated.')
            time.sleep(0.05)

            self._set_state(AssistantState.THINKING)
            resource_state = self.resource_governor.snapshot()
            if resource_state.state in {"protected", "pause"}:
                # V28 protects the machine by reducing background fan-out, but it never
                # rejects the user's foreground conversation merely because VRAM is high.
                self.log_ready.emit(resource_state.reason)
            with self._agent_lock:
                reply = self.agent.process(text)
            self.log_ready.emit(f'Intent: {reply.intent}')
            if reply.provider:
                self.log_ready.emit(f'AI provider: {reply.provider}')
            for tool_name in reply.tool_trace:
                self.log_ready.emit(f'Agent tool: {tool_name}')

            self.response_ready.emit(reply.gui_text, reply.user_language)
            self.spoken_text_ready.emit(reply.spoken_text)

            self._set_state(AssistantState.SPEAKING)
            backend = self.speaker.speak(reply.spoken_text)
            self.log_ready.emit(backend if self.config.voice_enabled else 'Voice reply skipped.')
            if backend.startswith('TTS failed'):
                self.error_raised.emit(backend)
            if backend.startswith('Speech interrupted'):
                self.log_ready.emit('Reply interruption completed at a sentence boundary.')
            time.sleep(0.05)
            self._set_state(AssistantState.IDLE if self._enabled else AssistantState.DISABLED)
        except Exception as exc:
            self._set_state(AssistantState.ERROR)
            self.error_raised.emit(str(exc))
            self.log_ready.emit(f'Error: {exc}')
        finally:
            if finalize:
                if self._handle_interrupt_queue(restart_listener=restart_listener):
                    return
                if restart_listener and self._enabled and self.config.wake_word_enabled:
                    self._start_wake_word_listener()
                self._busy = False

    def process_remote_text(self, text: str, source: str = "phone") -> dict:
        """Run a trusted remote turn and return the answer to the phone.

        The desktop speaker is intentionally not used; the Android client may speak
        the returned text locally. Shared agent memory keeps phone/PC context aligned.
        """
        clean = (text or "").strip()
        if not clean:
            return {"ok": False, "error": "Question is empty."}
        try:
            language = self.agent.detect_language(clean)
            self.log_ready.emit(f"Remote JARVIS request received from {source}.")
            with self._agent_lock:
                reply = self.agent.process(clean)
            self.transcript_ready.emit(f"[PHONE] {clean}", language)
            self.response_ready.emit(reply.gui_text, reply.user_language)
            return {"ok": True, "text": reply.gui_text, "spoken_text": reply.spoken_text,
                    "language": reply.user_language, "intent": reply.intent,
                    "provider": reply.provider, "tool_trace": list(reply.tool_trace)}
        except Exception as exc:
            self.log_ready.emit(f"Remote JARVIS request failed: {exc}")
            return {"ok": False, "error": str(exc)}

    def clear_conversation_memory(self) -> None:
        self.agent.clear_memory()

    def ai_provider_status(self) -> str:
        return self.agent.provider_status()

    def _set_state(self, state: AssistantState) -> None:
        self._state = state
        self.state_changed.emit(state.value)
