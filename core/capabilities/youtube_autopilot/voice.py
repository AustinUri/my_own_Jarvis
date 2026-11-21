"""Offline narration using local Piper; deliberately no remote speech API."""
from __future__ import annotations
import shutil
import subprocess
import tempfile
from pathlib import Path

def piper_narrate(episode:dict, output:Path, *, model:str, scene_seconds:float=7.0, piper_bin:str='piper'):
    if not model or not Path(model).is_file():raise RuntimeError('A real Piper English voice model path is required')
    if not shutil.which(piper_bin):raise RuntimeError('Piper executable is required to generate quality local speech')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):raise RuntimeError('FFmpeg + ffprobe required')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='jarvis-tts-') as temp:
        folder=Path(temp);parts=[]
        for i,s in enumerate(episode['scenes']):
            spoken=folder/f'{i:02d}-spoken.wav';part=folder/f'{i:02d}-fixed.wav'
            subprocess.run([piper_bin,'--model',model,'--output_file',str(spoken)],input=s['narration']+'\n',text=True,check=True,capture_output=True)
            dur=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(spoken)],text=True).strip())
            if dur>scene_seconds-.5:raise RuntimeError(f'Scene {i+1} spoken too long: {dur:.1f}s > {scene_seconds-.5:.1f}s. Increase scene_seconds or shorten the script.')
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(spoken),'-af','apad','-t',str(scene_seconds),'-ar','44100','-ac','1',str(part)],check=True)
            parts.append(part)
        concat=folder/'concat.txt'
        concat.write_text(''.join("file '"+p.name+"'\n" for p in parts),encoding='utf-8')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c:a','pcm_s16le',str(output)],cwd=folder,check=True)
    return output
