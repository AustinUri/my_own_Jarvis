from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import wave
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

from core.audio_utils import resolve_input_device


class WhisperEngine:
    """Local microphone recorder + transcription wrapper.

    Supports two backends:
    - faster-whisper (Python)
    - whisper.cpp (external executable)
    """

    COMMAND_VOCABULARY = [
        'jarvis', 'open', 'close', 'launch', 'run', 'search', 'google', 'youtube', 'gmail', 'github',
        'chatgpt', 'whatsapp', 'chrome', 'spotify', 'notepad', 'calculator', 'explorer', 'edge', 'discord',
        'vscode', 'desktop', 'downloads', 'documents', 'pictures', 'music', 'videos', 'time', 'date',
        'status', 'system', 'calculate', 'note', 'lock', 'computer', 'files', 'folder', 'web',
        'פתח', 'סגור', 'חפש', 'גוגל', 'יוטיוב', 'כרום', 'ספוטיפיי', 'הורדות', 'מסמכים', 'שעה', 'תאריך',
        'מחשב', 'מחשבון', 'נעילה', 'נעל', 'הערה', 'קבצים',
    ]

    DEFAULT_CUSTOM_ALIASES = {
        'krome': 'chrome',
        'crome': 'chrome',
        'chrom': 'chrome',
        'spotifai': 'spotify',
        'spotifi': 'spotify',
        'you tube': 'youtube',
        'g mail': 'gmail',
        'git hub': 'github',
        'chat gpt': 'chatgpt',
        'chat gp t': 'chatgpt',
        'jarvice': 'jarvis',
        'jarviss': 'jarvis',
        'jarvish': 'jarvis',
        'jervis': 'jarvis',
        'ג רוויס': 'ג׳רוויס',
        'גרביס': 'ג׳רוויס',
        'גירוויס': 'ג׳רוויס',
        'קרום': 'כרום',
        'ספוטיפי': 'ספוטיפיי',
        'יוטוב': 'יוטיוב',
        'גיט האב': 'github',
        'צאט גי פי טי': 'chatgpt',
    }

    def __init__(
        self,
        model_name: str = 'small',
        silence_threshold: float = 0.012,
        mic_name: str = 'Default',
        language_mode: str = 'Auto',
        accent_assist_enabled: bool = True,
        aliases_path: str | Path | None = None,
        backend: str = 'Auto',
        whisper_cpp_path: str | Path | None = None,
        base_dir: str | Path | None = None,
    ):
        self.model_name = model_name
        self.silence_threshold = silence_threshold
        self.mic_name = mic_name
        self.language_mode = language_mode
        self.accent_assist_enabled = accent_assist_enabled
        self.aliases_path = Path(aliases_path) if aliases_path else None
        self.backend = backend
        self.whisper_cpp_path = str(whisper_cpp_path or '').strip()
        self.base_dir = Path(base_dir) if base_dir else None
        self._model = None
        self._backend = None

    def transcribe_microphone_command(
        self,
        max_seconds: float = 7.0,
        silence_seconds: float = 1.1,
        threshold: float | None = None,
    ) -> tuple[str, str]:
        wav_path = self.record_command(max_seconds=max_seconds, silence_seconds=silence_seconds, threshold=threshold)
        text = self.transcribe(str(wav_path), command_mode=True)
        return text, str(wav_path)

    def record_command(
        self,
        max_seconds: float = 7.0,
        silence_seconds: float = 1.1,
        threshold: float | None = None,
    ) -> Path:
        import numpy as np
        import sounddevice as sd

        silence_threshold = self.silence_threshold if threshold is None else threshold
        sample_rate = 16000
        blocksize = 1600
        silence_blocks = max(1, int(silence_seconds / (blocksize / sample_rate)))
        max_blocks = max(1, int(max_seconds / (blocksize / sample_rate)))
        start_timeout_blocks = max(12, int(4.0 / (blocksize / sample_rate)))
        device = resolve_input_device(self.mic_name)

        frames: list[np.ndarray] = []
        speech_started = False
        silent_after_speech = 0
        lead_in: list[np.ndarray] = []

        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=blocksize, device=device) as stream:
            for index in range(max_blocks):
                data, _ = stream.read(blocksize)
                chunk = data.copy()
                normalized = chunk.astype('float32') / 32768.0
                rms = float((normalized ** 2).mean() ** 0.5)

                if not speech_started:
                    lead_in.append(chunk)
                    if len(lead_in) > 8:
                        lead_in.pop(0)

                if rms >= silence_threshold:
                    if not speech_started:
                        speech_started = True
                        frames.extend(lead_in)
                    frames.append(chunk)
                    silent_after_speech = 0
                else:
                    if speech_started:
                        frames.append(chunk)
                        silent_after_speech += 1
                        if silent_after_speech >= silence_blocks:
                            break
                    elif index >= start_timeout_blocks:
                        break

        if not frames:
            frames = lead_in[-1:] if lead_in else []

        audio = np.concatenate(frames, axis=0) if frames else np.zeros((0, 1), dtype='int16')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        tmp_path = Path(tmp.name)
        tmp.close()
        with wave.open(str(tmp_path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
        return tmp_path

    def transcribe(self, audio_path: str, command_mode: bool = False) -> str:
        backend = self._choose_backend()
        if backend == 'whisper.cpp':
            text = self._transcribe_whisper_cpp(audio_path, command_mode=command_mode)
        else:
            text = self._transcribe_faster_whisper(audio_path, command_mode=command_mode)
        self._backend = backend
        return self._repair_transcript(text, command_mode=command_mode)

    def _choose_backend(self) -> str:
        forced = (self.backend or 'Auto').strip().lower()
        if forced == 'whisper.cpp':
            return 'whisper.cpp'
        if forced == 'faster-whisper':
            return 'faster-whisper'
        return 'whisper.cpp' if self._find_whisper_cpp_executable() else 'faster-whisper'

    def _build_transcribe_kwargs(self, command_mode: bool) -> dict:
        kwargs = {
            'beam_size': 2 if self.accent_assist_enabled else 1,
            'vad_filter': True,
            'condition_on_previous_text': False,
        }
        if self.language_mode == 'English':
            kwargs['language'] = 'en'
        elif self.language_mode == 'Hebrew':
            kwargs['language'] = 'he'
        prompt = self._build_initial_prompt(command_mode)
        if prompt:
            kwargs['initial_prompt'] = prompt
        return kwargs

    def _transcribe_faster_whisper(self, audio_path: str, command_mode: bool) -> str:
        model = self._get_model()
        kwargs = self._build_transcribe_kwargs(command_mode=command_mode)
        segments, _info = model.transcribe(audio_path, **kwargs)
        return ' '.join(segment.text.strip() for segment in segments).strip()

    def _transcribe_whisper_cpp(self, audio_path: str, command_mode: bool) -> str:
        exe = self._find_whisper_cpp_executable()
        if not exe:
            raise RuntimeError(
                'whisper.cpp backend selected, but no whisper.cpp executable was found. '
                'Run scripts/setup_whisper_cpp_cpu.ps1 or switch back to faster-whisper.'
            )
        model_file = self._find_whisper_cpp_model()
        if not model_file:
            raise RuntimeError(
                f'whisper.cpp backend selected, but no model file was found for {self.model_name}. '
                'Run scripts/setup_whisper_cpp_cpu.ps1 to build/download them, or switch back to faster-whisper.'
            )
        out_base = Path(tempfile.NamedTemporaryFile(delete=False, suffix='').name)
        out_txt = out_base.with_suffix('.txt')
        cmd = [str(exe), '-m', str(model_file), '-f', str(audio_path), '-otxt', '-of', str(out_base), '-nt']
        language_arg = self._language_arg()
        if language_arg:
            cmd.extend(['-l', language_arg])
        if self.accent_assist_enabled:
            prompt = self._build_initial_prompt(command_mode)
            if prompt:
                cmd.extend(['--prompt', prompt])
        cmd.extend(['-t', str(max(4, (os.cpu_count() or 8) - 2))])
        creationflags = 0x08000000 if os.name == 'nt' else 0
        subprocess.run(cmd, check=True, capture_output=True, text=True, creationflags=creationflags)
        if out_txt.exists():
            raw = out_txt.read_text(encoding='utf-8', errors='ignore')
            return self._clean_whisper_cpp_text(raw)
        return ''


    def _clean_whisper_cpp_text(self, text: str) -> str:
        cleaned_lines: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip().replace('﻿', '')
            if not line:
                continue
            if line.startswith('- '):
                line = line[2:].strip()
            if line in {'-', '—', '…', '...'}:
                continue
            cleaned_lines.append(line)
        cleaned = ' '.join(cleaned_lines).strip()
        return cleaned

    def _language_arg(self) -> str | None:
        if self.language_mode == 'English':
            return 'en'
        if self.language_mode == 'Hebrew':
            return 'he'
        return None

    def _find_whisper_cpp_executable(self) -> Path | None:
        candidates = []
        if self.whisper_cpp_path:
            candidates.append(Path(self.whisper_cpp_path))
        if self.base_dir:
            candidates.extend([
                self.base_dir / 'third_party' / 'whisper.cpp' / 'build' / 'bin' / 'Release' / 'whisper-cli.exe',
                self.base_dir / 'third_party' / 'whisper.cpp' / 'build' / 'bin' / 'Release' / 'main.exe',
                self.base_dir / 'third_party' / 'whisper.cpp' / 'build' / 'bin' / 'whisper-cli.exe',
                self.base_dir / 'third_party' / 'whisper.cpp' / 'build' / 'bin' / 'main.exe',
                self.base_dir / 'third_party' / 'whisper.cpp' / 'whisper-cli.exe',
                self.base_dir / 'third_party' / 'whisper.cpp' / 'main.exe',
            ])
        which_cli = shutil.which('whisper-cli')
        which_main = shutil.which('main')
        if which_cli:
            candidates.append(Path(which_cli))
        if which_main:
            candidates.append(Path(which_main))
        for path in candidates:
            if path and path.exists():
                return path
        return None

    def _find_whisper_cpp_model(self) -> Path | None:
        if not self.base_dir:
            return None
        normalized = self.model_name.lower().strip()
        aliases = [normalized]
        if normalized == 'tiny':
            aliases.extend(['tiny.en'])
        elif normalized == 'base':
            aliases.extend(['base.en'])
        elif normalized == 'small':
            aliases.extend(['small.en'])
        elif normalized == 'medium':
            aliases.extend(['medium.en'])
        model_dir = self.base_dir / 'third_party' / 'whisper.cpp' / 'models'
        candidates = []
        for alias in aliases:
            candidates.extend([
                model_dir / f'ggml-{alias}.bin',
                model_dir / f'ggml-{alias}.bin',
            ])
        # Prefer multilingual file when Hebrew is selected
        if self.language_mode == 'Hebrew':
            multilingual = model_dir / f'ggml-{normalized}.bin'
            if multilingual.exists():
                return multilingual
        for path in candidates:
            if path.exists():
                return path
        # last-resort scan
        if model_dir.exists():
            for name in [f'ggml-{normalized}.bin', 'ggml-medium.bin', 'ggml-small.bin', 'ggml-base.bin']:
                candidate = model_dir / name
                if candidate.exists():
                    return candidate
        return None

    def active_backend_label(self) -> str:
        return self._backend or self._choose_backend()

    def _build_initial_prompt(self, command_mode: bool) -> str | None:
        if not self.accent_assist_enabled:
            return None
        english = (
            'Jarvis desktop commands. Say: open chrome, open spotify, open discord, open edge, open youtube, '
            'open google, open gmail, open github, open chatgpt, open downloads, open desktop, open documents, '
            'what time is it, what is the date, system status, calculate, search files, search google, create note, lock computer.'
        )
        hebrew = (
            'פקודות ג׳רוויס. פתח כרום, פתח ספוטיפיי, פתח יוטיוב, פתח גוגל, פתח גימייל, פתח הורדות, פתח מסמכים, '
            'מה השעה, מה התאריך, מצב המחשב, חפש קבצים, חפש בגוגל, כתוב הערה, נעל את המחשב.'
        )
        if self.language_mode == 'English':
            return english
        if self.language_mode == 'Hebrew':
            return hebrew
        return f'{english} {hebrew}' if command_mode else english

    def _repair_transcript(self, text: str, command_mode: bool) -> str:
        repaired = self._normalize_whitespace(text)
        repaired = repaired.replace('’', "'").replace('`', "'")
        if repaired in {'-', '—', '…', '...'}:
            return ''
        if not repaired or not self.accent_assist_enabled:
            return repaired

        lowered = repaired.lower()
        for source, target in self._iter_alias_map():
            pattern = re.compile(rf'(?<!\w){re.escape(source)}(?!\w)', re.IGNORECASE)
            lowered = pattern.sub(target, lowered)

        if command_mode and not re.search(r'[֐-׿]', lowered):
            lowered = self._fuzzy_repair_english_command(lowered)
        if command_mode and re.search(r'[֐-׿]', lowered):
            lowered = self._repair_hebrew_command(lowered)

        return self._normalize_whitespace(lowered)

    def _repair_hebrew_command(self, text: str) -> str:
        replacements = {
            'קרום': 'כרום',
            'גוגל כרום': 'כרום',
            'ספוטיפי': 'ספוטיפיי',
            'ספוטיפייי': 'ספוטיפיי',
            'יוטוב': 'יוטיוב',
            'יוטיובי': 'יוטיוב',
            'הורדה': 'הורדות',
            'מסמך': 'מסמכים',
            'תפתח לי': 'פתח',
            'תסגור לי': 'סגור',
            'תנעל לי': 'נעל',
            'מה השאות': 'מה השעה',
            'מה תאריך': 'מה התאריך',
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        return text

    def _fuzzy_repair_english_command(self, text: str) -> str:
        tokens = re.findall(r"[a-zA-Z']+|[^a-zA-Z']+", text)
        repaired_tokens: list[str] = []
        for token in tokens:
            if not re.fullmatch(r"[a-zA-Z']+", token):
                repaired_tokens.append(token)
                continue
            lowered = token.lower()
            if len(lowered) <= 2:
                repaired_tokens.append(lowered)
                continue
            best = self._best_match(lowered, self.COMMAND_VOCABULARY)
            if best and self._similarity(lowered, best) >= 0.74:
                repaired_tokens.append(best)
            else:
                repaired_tokens.append(lowered)
        repaired = ''.join(repaired_tokens)
        return repaired.replace('you tube', 'youtube').replace('g mail', 'gmail').replace('git hub', 'github')

    def _best_match(self, token: str, vocabulary: Iterable[str]) -> str | None:
        best_word = None
        best_score = 0.0
        for word in vocabulary:
            score = self._similarity(token, word)
            if score > best_score:
                best_score = score
                best_word = word
        return best_word

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def _iter_alias_map(self) -> list[tuple[str, str]]:
        alias_map = dict(self.DEFAULT_CUSTOM_ALIASES)
        if self.aliases_path and self.aliases_path.exists():
            try:
                data = json.loads(self.aliases_path.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
                            alias_map[key.strip().lower()] = value.strip().lower()
            except (OSError, json.JSONDecodeError):
                pass
        return sorted(alias_map.items(), key=lambda item: len(item[0]), reverse=True)

    def _get_model(self):
        if self._model is not None:
            return self._model

        from faster_whisper import WhisperModel

        try:
            self._model = WhisperModel(self.model_name, device='cuda', compute_type='int8_float16')
            self._backend = 'faster-whisper:cuda'
        except Exception:
            self._model = WhisperModel(self.model_name, device='cpu', compute_type='int8')
            self._backend = 'faster-whisper:cpu'
        return self._model
