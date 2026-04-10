from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.config import AppConfig
from core.events import AssistantReply, AssistantState
from llm.brain import Brain
from stt.whisper_engine import WhisperEngine
from tools.registry import ToolRegistry
from tools.web_tools import WebAnswer
from tts.speaker import Speaker
from wakeword.listener import WakeWordEvent, WakeWordListener

WAKEWORD_PREFIX_RE = re.compile(
    r"^\s*(?:hey\s+jarvis|jarvis|wake\s+up\s+jarvis|היי\s+ג[׳']?רוויס|ג[׳']?רוויס)\s*[,，:;\-]?\s*",
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
        self.brain = Brain(config)
        self.tools = ToolRegistry(base_dir, config)
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
        self._busy = False
        self._enabled = config.assistant_enabled
        if self._enabled and self.config.wake_word_enabled:
            self._start_wake_word_listener()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def shutdown(self) -> None:
        self._stop_wake_word_listener()

    def reload_runtime_config(self) -> None:
        self.whisper.model_name = self.config.stt_model_name
        self.whisper.silence_threshold = self.config.silence_threshold
        self.whisper.mic_name = self.config.mic_name
        self.whisper.language_mode = self.config.language_mode
        self.whisper.accent_assist_enabled = self.config.accent_assist_enabled
        self.whisper.backend = self.config.stt_backend
        self.whisper.whisper_cpp_path = self.config.whisper_cpp_path
        self.brain.config = self.config
        self.tools.config = self.config
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
        if self._busy:
            self.log_ready.emit('Jarvis is already busy.')
            return
        if not text.strip():
            return
        self._busy = True
        self._stop_wake_word_listener()
        threading.Thread(target=self._run_pipeline, args=(text, True), daemon=True).start()

    def process_push_to_talk(self) -> None:
        if not self._enabled:
            self.log_ready.emit('Assistant is disabled.')
            return
        if self._busy:
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

    def _capture_then_process_voice(self, from_wake_word: bool) -> None:
        try:
            self._set_state(AssistantState.LISTENING)
            if from_wake_word:
                self.log_ready.emit('Listening for your command...')
            else:
                self.log_ready.emit(f'Push-to-talk recording started on {self.config.mic_name}.')

            transcript, wav_path = self.whisper.transcribe_microphone_command(
                max_seconds=self.config.command_max_seconds,
                silence_seconds=self.config.command_silence_seconds,
                threshold=self.config.silence_threshold,
            )
            cleaned = WAKEWORD_PREFIX_RE.sub('', transcript).strip()
            transcript = cleaned or transcript.strip()
            if not transcript:
                self.log_ready.emit('No command was captured after listening.')
                if self.config.voice_enabled:
                    miss = 'Sir, I did not catch that.' if self.config.tone_mode == 'Respectful' else "I didn't catch that."
                    self.spoken_text_ready.emit(miss)
                    self._set_state(AssistantState.SPEAKING)
                    backend = self.speaker.speak(miss)
                    self.log_ready.emit(backend)
                self._set_state(AssistantState.IDLE if self._enabled else AssistantState.DISABLED)
                return
            self.log_ready.emit(f'Voice captured from {wav_path}. STT backend: {self.whisper.active_backend_label()}')
            self._run_pipeline(transcript, restart_listener=False)
        except Exception as exc:
            self._set_state(AssistantState.ERROR)
            self.error_raised.emit(str(exc))
            self.log_ready.emit(f'Voice input error: {exc}')
        finally:
            if self._enabled and self.config.wake_word_enabled:
                self._start_wake_word_listener()
            self._busy = False

    def _run_microphone_test(self) -> None:
        try:
            self._set_state(AssistantState.LISTENING)
            self.log_ready.emit(f'Microphone test started on {self.config.mic_name}. Speak now.')
            transcript, wav_path = self.whisper.transcribe_microphone_command(max_seconds=5.0, silence_seconds=1.0, threshold=self.config.silence_threshold)
            language = self.brain.detect_language(transcript or '')
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

    def _run_pipeline(self, text: str, restart_listener: bool) -> None:
        try:
            self._set_state(AssistantState.LISTENING)
            self.log_ready.emit('Input received.')
            time.sleep(0.08)

            language = self.brain.detect_language(text)
            self._set_state(AssistantState.TRANSCRIBING)
            self.transcript_ready.emit(text, language)
            self.log_ready.emit('Transcript updated.')
            time.sleep(0.12)

            self._set_state(AssistantState.THINKING)
            reply = self.brain.build_reply(text)
            self.log_ready.emit(f'Intent: {reply.intent}')

            if reply.tool is not None:
                result = self.tools.run(reply.tool)
                reply = self._apply_tool_result(reply, result)
                self.log_ready.emit(f'Tool executed: {reply.tool.name}')
                if isinstance(result, WebAnswer):
                    self.log_ready.emit(f'Web provider: {result.provider}')

            self.response_ready.emit(reply.gui_text, reply.user_language)
            self.spoken_text_ready.emit(reply.spoken_text)

            self._set_state(AssistantState.SPEAKING)
            backend = self.speaker.speak(reply.spoken_text)
            self.log_ready.emit(backend if self.config.voice_enabled else 'Voice reply skipped.')
            if backend.startswith('TTS failed'):
                self.error_raised.emit(backend)
            time.sleep(0.05)
            self._set_state(AssistantState.IDLE if self._enabled else AssistantState.DISABLED)
        except Exception as exc:
            self._set_state(AssistantState.ERROR)
            self.error_raised.emit(str(exc))
            self.log_ready.emit(f'Error: {exc}')
        finally:
            if restart_listener and self._enabled and self.config.wake_word_enabled:
                self._start_wake_word_listener()
            self._busy = False

    def _apply_tool_result(self, reply: AssistantReply, result) -> AssistantReply:
        if isinstance(result, WebAnswer):
            candidate = AssistantReply(
                user_language=reply.user_language,
                intent=reply.intent,
                gui_text=result.to_gui_text(),
                spoken_text=result.spoken_text,
                tool=reply.tool,
                raw_user_text=reply.raw_user_text,
            )
            return self.brain._apply_personality(candidate)
        result_text = str(result)
        spoken = self._to_spoken_english(reply.intent, result_text)
        candidate = AssistantReply(
            user_language=reply.user_language,
            intent=reply.intent,
            gui_text=result_text,
            spoken_text=spoken,
            tool=reply.tool,
            raw_user_text=reply.raw_user_text,
        )
        return self.brain._apply_personality(candidate)

    def _to_spoken_english(self, intent: str, result: str) -> str:
        mapping = {
            'open_app': 'Opening complete.',
            'close_app': 'Closing complete.',
            'open_website': 'Website opened.',
            'search_web': 'Web search opened.',
            'open_folder': 'Folder opened.',
            'tell_time': result if result else 'Here is the time.',
            'tell_date': result if result else 'Here is the date.',
            'system_status': result if result else 'Here is the system status.',
            'calculate': result if result else 'Calculation completed.',
            'create_note': 'Your note was created.',
            'search_files': 'File search completed.',
            'answer_web_question': result if result else 'Here is what I found online.',
            'lock_computer': 'Locking the computer.',
            'shutdown_request': 'Shutdown is blocked until you confirm it.',
        }
        return mapping.get(intent, result[:160] if result else 'Done.')

    def _set_state(self, state: AssistantState) -> None:
        self.state_changed.emit(state.value)
