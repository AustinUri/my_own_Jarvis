"""Mechanical QA for original children's shorts. Does NOT replace human review."""
from __future__ import annotations
import json
import math
import re
import shutil
import subprocess
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from .episodes import validate_episode
from .visual_contract import audit_storyboard
from .voice import speech_envelope

BLOCKED=re.compile(r'\b(peppa|piggy|disney|cocomelon|paw patrol|violent|weapon|blood|scary|kill|poison|subscribe|click here|buy now)\b', re.I)

def inspect_story(ep):
    validate_episode(ep)
    data=json.dumps(ep,ensure_ascii=False)
    if BLOCKED.search(data):raise ValueError('Story requires human review: sensitive, marketing, or copyrighted reference')
    for index, scene in enumerate(ep['scenes'], 1):
        if len(scene['narration'].split()) > 23:
            raise ValueError(f'Scene {index}: narration too long. Shorten this line to at most 23 words.')
    if len(set(s['caption'].casefold() for s in ep['scenes']))<len(ep['scenes']):raise ValueError('Repeated captions')
    return True

def motion_audit(video:Path,length:float):
    """Find near-static scenes; intentionally a BLOCKING lower bound, not artistic approval.

    Measures differences between samples *inside* scenes to avoid giving hard
    scene cuts free credit. Frame differences are only a crude motion proxy.
    """
    if not shutil.which('ffmpeg'):raise RuntimeError('ffmpeg required for motion QA')
    pairs=[]
    # Within-scene offsets for a 6-scene video; avoid checking only cuts.
    for fraction in [0.,1/6,2/6,3/6,4/6,5/6]:
        st=length*fraction
        pairs.append((st+length/42.,st+length/14.))
    differences=[]
    for ta,tb in pairs:
        imgs=[]
        for t in (ta,tb):
            p=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(round(t,3)),'-i',str(video),'-frames:v','1','-vf','scale=160:284','-f','image2pipe','-vcodec','mjpeg','-'],capture_output=True,timeout=15)
            if p.returncode or not p.stdout:raise ValueError('Failed to sample animation frames')
            imgs.append(Image.open(BytesIO(p.stdout)).convert('RGB'))
        s=ImageStat.Stat(ImageChops.difference(imgs[0],imgs[1]))
        differences.append(sum(s.mean)/3)
    score=sum(differences)/len(differences)
    lively=sum(v>=3.0 for v in differences)
    if score<3.0 or lively<3:
        raise ValueError(f'Insufficient animated motion: motion_score={score:.2f}; animated_scenes={lively}/6. Manual creative review required.')
    return {'motion_score':round(score,2),'animated_scenes':lively,'frames_compared':12}

def _inspect_media(video, min_seconds, min_size=(360, 640)):
    if not shutil.which('ffprobe'):raise RuntimeError('ffprobe is required')
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)],text=True))
    streams=data['streams'];v=next((s for s in streams if s.get('codec_type')=='video'),None)
    a=next((s for s in streams if s.get('codec_type')=='audio'),None)
    if not v or not a:raise ValueError('The render needs a video stream and a narration track')
    if int(v['width']) < min_size[0] or int(v['height']) < min_size[1]:
        raise ValueError('Rendered size too low')
    length=float(data['format']['duration'])
    if not min_seconds<=length<=180:raise ValueError('Invalid video duration')
    if Path(video).stat().st_size<50_000:raise ValueError('Suspiciously small video file')
    return v, a, length


def _report(video, stream, length, motion):
    return {'seconds': round(length, 1),
            'resolution': f"{stream['width']}x{stream['height']}", 'audio': True,
            'size_bytes': Path(video).stat().st_size, 'motion_audit': motion,
            'human_approval_required': True}


def inspect_render(video:Path,min_seconds:float=20):
    stream, _, length = _inspect_media(video, min_seconds)
    return _report(video, stream, length, motion_audit(Path(video), length))


def _narration_audit(video, scenes, timeline, fps):
    if len(scenes) != len(timeline) or not timeline:
        raise ValueError('Narration timeline does not cover all scenes')
    rate = 8000
    audio = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(video),
                                     '-map', '0:a:0', '-ac', '1', '-ar', str(rate),
                                     '-f', 's16le', '-'], timeout=60)
    frame = 0
    correlations = []
    for index, (scene, cue) in enumerate(zip(scenes, timeline), 1):
        if cue['narration'] != scene['narration']:
            raise ValueError(f'Scene {index}: narration text changed since recording')
        if cue['start_frame'] != frame or cue['frame_count'] <= 0:
            raise ValueError(f'Scene {index}: gap or overlap in narration timeline')
        seconds = cue['speech_seconds']
        if not 0 < seconds <= cue['frame_count'] / fps:
            raise ValueError(f'Scene {index}: spoken line extends past picture cut')
        start_sample = round(frame * rate / fps)
        stop_sample = start_sample + round(seconds * rate)
        recorded = cue['speech_envelope']
        heard = speech_envelope(audio[start_sample * 2:stop_sample * 2], rate)
        if abs(len(recorded) - len(heard)) > 1 or len(heard) < 2:
            raise ValueError(f'Scene {index}: incomplete encoded narration')
        pairs = list(zip(recorded, heard))
        power = math.sqrt(sum(x*x for x, _ in pairs) * sum(y*y for _, y in pairs))
        similarity = sum(x*y for x, y in pairs) / power if power else 0.
        if max(heard) < 64 or similarity < .93:
            raise ValueError(f'Scene {index}: encoded audio differs from the Piper recording')
        correlations.append(round(similarity, 3))
        frame += cue['frame_count']
        # AAC can ring briefly after a cut. The rest of the reaction hold must be quiet.
        tail = audio[(stop_sample + rate // 10) * 2:round(frame * rate / fps) * 2]
        if max(speech_envelope(tail, rate), default=0) > max(100, max(recorded) * .05):
            raise ValueError(f'Scene {index}: unexpected audio after narration')
    return correlations


def _sample_frames(video, indices, size):
    select = '+'.join(f'eq(n,{i})' for i in indices)
    w, h = size
    data = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-i', str(video), '-an', '-vf',
        f"select='{select}',scale={w}:{h}:flags=bilinear", '-fps_mode', 'passthrough',
        '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'], timeout=90)
    stride = w * h * 3
    if len(data) != stride * len(indices):
        raise ValueError('Encoded video is missing storyboard frames')
    return [Image.frombytes('RGB', size, data[p:p+stride]) for p in range(0, len(data), stride)]


def _sample_shots(video, timeline):
    indices = [cue['start_frame'] + int((cue['frame_count'] - 1) * frac)
               for cue in timeline for frac in (.13, .38, .63, .87)]
    if len(set(indices)) != len(indices):
        raise ValueError('Scene is too short to sample motion')
    w, h = 112, 160
    # Keep the picture area. Changing titles or subtitles cannot earn motion credit.
    pictures = [image.crop((3, int(.12*h), w-3, int(.82*h)))
                for image in _sample_frames(video, indices, (w, h))]
    return [pictures[i:i+4] for i in range(0, len(pictures), 4)]


def _prop_audit(video, scenes, timeline, fps, width, height):
    from .creative_factory import _draw_scene

    size = (min(360, width), round(height * min(360, width) / width))
    offsets = [min(cue['frame_count']-1, round(.60 * cue['speech_seconds'] * fps))
               for cue in timeline]
    indices = [cue['start_frame'] + offset for cue, offset in zip(timeline, offsets)]
    decoded = _sample_frames(video, indices, size)
    checks = []
    for i, (scene, cue, offset, image) in enumerate(zip(scenes, timeline, offsets, decoded)):
        args = scene, offset / fps, cue['speech_seconds'], width, height
        expected = _draw_scene(*args).resize(size, Image.Resampling.BILINEAR)
        empty = _draw_scene(*args, include_prop=False).resize(size, Image.Resampling.BILINEAR)
        contrast = ImageChops.difference(expected, empty).convert('L')
        mask = contrast.point(lambda level: 255 if level >= 24 else 0)
        pixels = mask.histogram()[255]
        if pixels < 6:
            raise ValueError(f"Scene {i+1}: story prop {scene['prop']!r} has no readable silhouette")
        present_error = ImageStat.Stat(ImageChops.difference(image, expected), mask).mean
        absent_error = ImageStat.Stat(ImageChops.difference(image, empty), mask).mean
        # True prop pixels should closely match the colored silhouette. Scenery
        # and codec noise alone must not count as evidence of the featured object.
        error = sum(present_error) / 3
        tolerance = max(14, .42 * ImageStat.Stat(contrast, mask).mean[0])
        if error > tolerance or sum(absent_error) / 3 < 1.6 * error:
            raise ValueError(f"Scene {i+1}: encoded picture is missing expected prop {scene['prop']!r}")
        checks.append({'scene': i+1, 'prop': scene['prop'], 'frame': indices[i],
                       'visible_pixels': pixels, 'mean_color_error': round(error, 2)})
    return checks


def _movement(first, second):
    # A slow tracking pan moves the whole background. Measure the motion left
    # after aligning the low-resolution frames horizontally to the nearest pixel.
    width, height = first.size
    border = 4
    fixed = first.crop((border, 0, width - border, height))
    changed = []
    for offset in range(-border, border + 1):
        moved = second.crop((border + offset, 0, width - border + offset, height))
        diff = ImageChops.difference(fixed, moved).convert('L')
        changed.append(sum(diff.histogram()[14:]) / (diff.width * diff.height))
    return min(changed)


def _picture_audit(shots):
    motion = []
    compositions = []
    for index, samples in enumerate(shots, 1):
        changes = [_movement(first, second) for first, second in zip(samples, samples[1:])]
        if max(changes) < .02 or sum(changes) / len(changes) < .012:
            raise ValueError(f'Scene {index}: insufficient on-screen motion')
        motion.append([round(v, 3) for v in changes])
        compositions.append([im.resize((16, 20), Image.Resampling.BOX) for im in samples])

    for index, shot in enumerate(compositions):
        similar = 1
        for j, other in enumerate(compositions):
            if index == j:
                continue
            distance = sum(sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3
                           for a, b in zip(shot, other)) / len(shot)
            if abs(index - j) == 1 and distance < 1.1:
                raise ValueError(f'Scenes {min(index,j)+1} and {max(index,j)+1}: repeated composition')
            if distance < 4:
                similar += 1
        if similar > len(shots) / 2:
            raise ValueError('Majority of scenes repeat the same composition')
    return {'animated_scenes': len(shots), 'frames_compared': len(shots) * 4,
            'changed_pixel_fractions': motion}


def inspect_draft_render(video: Path, episode: dict, timeline: list[dict], fps: int):
    """Check the delivered MP4 against the edit and the original Piper recordings."""
    storyboard = audit_storyboard(episode)
    if not storyboard['ok']:
        raise ValueError('Storyboard failed: ' + ', '.join(storyboard['issues']))
    stream, audio, length = _inspect_media(video, min_seconds=1, min_size=(240, 420))
    expected = sum(cue['frame_count'] for cue in timeline)
    if Fraction(stream['avg_frame_rate']) != fps or int(stream['nb_frames']) != expected:
        raise ValueError('Encoded video frame count or rate differs from narration timeline')
    if (abs(float(audio['duration']) - expected / fps) > max(.06, 1 / fps)
            or abs(float(audio.get('start_time', 0)) - float(stream.get('start_time', 0))) > .05):
        raise ValueError('Audio stream does not span the picture timeline')
    narration = _narration_audit(video, episode['scenes'], timeline, fps)
    report = _report(video, stream, length, _picture_audit(_sample_shots(video, timeline)))
    report['prop_samples'] = _prop_audit(video, episode['scenes'], timeline, fps,
                                        int(stream['width']), int(stream['height']))
    report['narration_envelope_similarity'] = narration
    if any('foley' in edit for edit in timeline):
        if audio.get('channels') != 2:
            raise ValueError('The storyboard calls for a stereo sound-effects mix')
        from .foley import audit_foley
        stereo = subprocess.check_output(['ffmpeg','-v','error','-i',str(video),'-map','0:a:0',
                                          '-ac','2','-ar','8000','-f','s16le','-'], timeout=60)
        report['sound_effects'] = audit_foley(stereo, episode['scenes'], timeline, fps)
    report['artistic_quality_verified'] = False
    return report
