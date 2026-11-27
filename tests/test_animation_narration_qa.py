import math
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw

from core.capabilities.youtube_autopilot import quality, voice


class NarratedTimelineTests(unittest.TestCase):
    def test_piper_lines_control_cuts_and_muxed_audio_must_match(self):
        scenes = [{'narration': 'Stop by the stream.'}, {'narration': 'Now fly home.'}]
        rate = 8000

        def speak(line, model, binary, path):
            duration, period = (.63, .28) if line == scenes[0]['narration'] else (2.34, .47)
            samples = array('h', (int(12000 * math.sin(2 * math.pi * 200 * i / rate))
                                  if (i / rate) % period < .14 else 0
                                  for i in range(round(duration * rate))))
            if sys.byteorder != 'little':
                samples.byteswap()
            with wave.open(str(path), 'wb') as recording:
                recording.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
                recording.writeframes(samples.tobytes())

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'episode.wav'
            model = Path(folder) / 'voice.onnx'
            model.touch()
            with patch.object(voice, '_synthesize', side_effect=speak):
                timeline = voice.piper_draft_narrate({'scenes': scenes}, path, model=str(model),
                                                     fps=17, piper_bin=sys.executable, scene_seconds=1.)
            self.assertEqual(timeline[1]['start_frame'], timeline[0]['frame_count'])
            self.assertGreater(timeline[1]['frame_count'], timeline[0]['frame_count'])
            with wave.open(str(path), 'rb') as track:
                self.assertEqual(track.getnframes(), round(sum(c['frame_count'] for c in timeline) * rate / 17))
                audio = track.readframes(track.getnframes())
        with patch.object(quality.subprocess, 'check_output', return_value=audio):
            self.assertEqual(quality._narration_audit(path, scenes, timeline, 17), [1., 1.])
            with self.assertRaisesRegex(ValueError, 'text changed'):
                quality._narration_audit(path, list(reversed(scenes)), timeline, 17)
        with patch.object(quality.subprocess, 'check_output', return_value=audio[::-1]):
            with self.assertRaisesRegex(ValueError, 'differs'):
                quality._narration_audit(path, scenes, timeline, 17)


class EncodedPictureTests(unittest.TestCase):
    def setUp(self):
        self.shots = []
        for color in ('#354f52', '#e76f51', '#264653', '#ffb703', '#8338ec', '#2a9d8f'):
            shot = []
            for x in (3, 12, 22, 29):
                sample = Image.new('RGB', (64, 64), color)
                ImageDraw.Draw(sample).ellipse((x, 20, x+16, 45), fill='white')
                shot.append(sample)
            self.shots.append(shot)

    def test_each_scene_must_move(self):
        self.assertEqual(quality._picture_audit(self.shots)['animated_scenes'], 6)
        self.shots[3] = [self.shots[3][0]] * 4
        with self.assertRaisesRegex(ValueError, 'Scene 4: insufficient'):
            quality._picture_audit(self.shots)

    def test_repeated_moving_composition_fails(self):
        self.shots[3] = self.shots[2]
        with self.assertRaisesRegex(ValueError, 'repeated composition'):
            quality._picture_audit(self.shots)

    def test_camera_pan_alone_is_a_static_scene(self):
        backplate = Image.new('RGB', (64, 64), 'orange')
        brush = ImageDraw.Draw(backplate)
        for x in range(0, 64, 7):
            brush.line((x, 5, x + 7, 50), fill='black', width=3)
        self.shots[1] = [ImageChops.offset(backplate, offset, 0) for offset in (0, 3, 6, 9)]
        with self.assertRaisesRegex(ValueError, 'Scene 2: insufficient'):
            quality._picture_audit(self.shots)

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg required to test encoded prop visibility')
    def test_encoded_prop_must_match_the_storyboard(self):
        from core.capabilities.youtube_autopilot.creative_factory import _draw_scene

        scene = {'action': 'watch', 'prop': 'apple', 'shot': 'wide',
                 'caption': 'Round and red', 'setting': 'orchard'}
        cue = {'start_frame': 0, 'frame_count': 10, 'speech_seconds': 1.}
        with tempfile.TemporaryDirectory() as folder:
            for visible in (True, False):
                with self.subTest(visible=visible):
                    frame = _draw_scene(scene, .6, 1., 240, 420, include_prop=visible)
                    video = Path(folder) / f'{visible}.mp4'
                    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'rawvideo',
                                    '-pix_fmt', 'rgb24', '-s', '240x420', '-r', '10',
                                    '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(video)],
                                   input=frame.tobytes()*10, check=True)
                    if visible:
                        checks = quality._prop_audit(video, [scene], [cue], 10, 240, 420)
                        self.assertEqual(checks[0]['frame'], 6)
                    else:
                        with self.assertRaisesRegex(ValueError, 'missing expected prop'):
                            quality._prop_audit(video, [scene], [cue], 10, 240, 420)
