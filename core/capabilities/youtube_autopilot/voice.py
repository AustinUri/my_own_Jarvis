"""Offline narration using local Piper; deliberately no remote speech API."""
from __future__ import annotations
import shutil
import subprocess
import tempfile
import math
import sys
import wave
from array import array
from pathlib import Path


def _synthesize(narration, model, piper_bin, path):
    subprocess.run([piper_bin, '--model', model, '--output_file', str(path)],
                   input=narration + '\n', text=True, check=True, capture_output=True)


def speech_envelope(pcm: bytes, rate: int) -> list[int]:
    """RMS in 50 ms windows, comparable before and after AAC encoding."""
    samples = array('h')
    samples.frombytes(pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    levels = []
    for i in range(math.ceil(len(samples) * 20 / rate)):
        block = samples[round(i * rate / 20):round((i + 1) * rate / 20)]
        if block:
            levels.append(math.isqrt(sum(s * s for s in block) // len(block)))
    return levels


def piper_draft_narrate(episode, output: Path, *, model: str, fps: int,
                        scene_seconds: float = 7., piper_bin: str = 'piper') -> list[dict]:
    """Record each line, then place scene boundaries on exact video frames."""
    if not Path(model).is_file() or not shutil.which(piper_bin):
        raise RuntimeError('A local Piper executable and voice model are required')
    if fps <= 0 or not math.isfinite(scene_seconds) or scene_seconds <= 0:
        raise ValueError('Positive frame rate and scene duration required')
    output.parent.mkdir(parents=True, exist_ok=True)
    timeline = []
    start_frame = 0
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='piper-') as folder:
        joined = Path(folder) / 'episode.wav'
        with wave.open(str(joined), 'wb') as track:
            for index, scene in enumerate(episode['scenes']):
                line = scene['narration']
                spoken = Path(folder) / f'scene-{index}.wav'
                _synthesize(line, model, piper_bin, spoken)
                with wave.open(str(spoken), 'rb') as clip:
                    if clip.getsampwidth() != 2 or clip.getnchannels() != 1:
                        raise ValueError('Piper must produce mono 16-bit PCM')
                    rate = clip.getframerate()
                    pcm = clip.readframes(clip.getnframes())
                if index == 0:
                    track.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
                if rate != track.getframerate():
                    raise ValueError('Piper changed sample rate between lines')
                levels = speech_envelope(pcm, rate)
                if max(levels, default=0) < 64:
                    raise ValueError(f'Scene {index + 1}: silent Piper recording')
                seconds = len(pcm) / (2 * rate)
                # Short lines leave space for the reaction; long lines are never cut.
                hold = min(.85, .12 * scene_seconds)
                count = math.ceil(fps * max(min(3., scene_seconds), seconds + hold))
                end_sample = round((start_frame + count) * rate / fps)
                track.writeframesraw(pcm)
                track.writeframesraw(b'\0\0' * (end_sample - track.tell()))
                timeline.append({'start_frame': start_frame, 'frame_count': count,
                                 'narration': line, 'speech_seconds': seconds,
                                 'speech_envelope': levels})
                start_frame += count
        joined.replace(output)
    return timeline

def piper_narrate(episode:dict, output:Path, *, model:str, scene_seconds:float=7.0, piper_bin:str='piper'):
    if not model or not Path(model).is_file():raise RuntimeError('A real Piper English voice model path is required')
    if not shutil.which(piper_bin):raise RuntimeError('Piper executable is required to generate quality local speech')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):raise RuntimeError('FFmpeg + ffprobe required')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='jarvis-tts-') as temp:
        folder=Path(temp);parts=[]
        for i,s in enumerate(episode['scenes']):
            spoken=folder/f'{i:02d}-spoken.wav';part=folder/f'{i:02d}-fixed.wav'
            _synthesize(s['narration'], model, piper_bin, spoken)
            dur=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(spoken)],text=True).strip())
            if dur>scene_seconds-.5:raise RuntimeError(f'Scene {i+1} spoken too long: {dur:.1f}s > {scene_seconds-.5:.1f}s. Increase scene_seconds or shorten the script.')
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(spoken),'-af','apad','-t',str(scene_seconds),'-ar','44100','-ac','1',str(part)],check=True)
            parts.append(part)
        concat=folder/'concat.txt'
        concat.write_text(''.join("file '"+p.name+"'\n" for p in parts),encoding='utf-8')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c:a','pcm_s16le',str(output.resolve())],cwd=folder,check=True)
    return output
