"""Run from JARVIS root: python -m unittest discover -s tests -p test_youtube_animation_v03.py"""
import unittest
from PIL import ImageChops, ImageStat
from core.capabilities.youtube_autopilot.episodes import EPISODES
from core.capabilities.youtube_autopilot.renderer import cartoon_frame

class TestYoutubeAnimationV03(unittest.TestCase):
    def test_scenes_change_and_actions_move(self):
        ep=EPISODES[0]
        a=cartoon_frame(1.0,ep,secs=7,w=360,h=640)
        b=cartoon_frame(3.0,ep,secs=7,w=360,h=640)
        c=cartoon_frame(23,ep,secs=7,w=360,h=640)
        self.assertEqual(a.size,(360,640))
        self.assertEqual(b.size,(360,640))
        self.assertGreater(sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3,3)
        self.assertGreater(sum(ImageStat.Stat(ImageChops.difference(b,c)).mean)/3,5)
    def test_can_render_all_story_kinds(self):
        for ep in EPISODES:
            for ix in range(len(ep['scenes'])):
                image=cartoon_frame(ix*7+3.0,ep,secs=7,w=360,h=640)
                self.assertEqual(image.size,(360,640))

if __name__=='__main__':unittest.main()
