from contextlib import redirect_stdout
from io import StringIO
import json
import tempfile
import random
import unittest
from pathlib import Path
from unittest.mock import patch
from core.capabilities.youtube_autopilot.creative_factory import create_story,frame,main,offline_story,_signature,STORIES
from core.capabilities.youtube_autopilot.manager import setup,config,read
from PIL import ImageChops,ImageStat
class CreativeFactoryV04Tests(unittest.TestCase):
    def test_cli_signals_rejected_and_failed_renders(self):
        target = "core.capabilities.youtube_autopilot.creative_factory.render_draft"
        for mode in ("create", "worker"):
            for rejected in (True, False):
                with self.subTest(mode=mode, rejected=rejected), tempfile.TemporaryDirectory() as root:
                    args = [mode, "--root", root, "--backend", "offline", "--render"]
                    if mode == "worker":
                        args.extend(["--max-cycles", "1"])
                    with patch(target) as render, redirect_stdout(StringIO()) as output:
                        if rejected:
                            render.return_value = {"video": "review.mp4", "mechanical_qa_error": "Static scene"}
                        else:
                            render.side_effect = RuntimeError("Encoder unavailable")
                        self.assertEqual(main(args), 1)
                    self.assertIn("render_rejected" if rejected else "render_failed", output.getvalue())

    def test_each_available_opening_prop_gets_a_turn(self):
        prop_count = len({beats[0][3] for _, _, beats in STORIES})
        for seed in range(10):
            seen = []
            rng = random.Random(seed)
            for _ in range(prop_count):
                seen.append(offline_story(None, seen, rng))
            self.assertEqual(len({ep['scenes'][0]['prop'] for ep in seen}), prop_count)

    def test_generates_unique_stories_and_visual_plans(self):
        with tempfile.TemporaryDirectory() as t:
            root=setup(Path(t))
            items=[create_story(root,backend='offline') for _ in range(5)]
            titles=[e['title'] for e,p in items]
            self.assertEqual(len(titles),len(set(titles)))
            self.assertEqual(len({_signature(e) for e,p in items}),len(items))
            self.assertEqual(len({e['scenes'][0]['prop'] for e,p in items}),len(items))
            for e,p in items:
                self.assertTrue(p.exists())
                self.assertEqual(len(e['scenes']),6)
                self.assertTrue(all('shot' in sc and 'setting' in sc for sc in e['scenes']))
            self.assertFalse(config(root).get('autopublish_enabled'))
            self.assertEqual(read(root/'jobs.json',[]),[])
    def test_finite_offline_library_refuses_repeating_episodes(self):
        with tempfile.TemporaryDirectory() as t:
            root=setup(Path(t))
            for i in range(len(STORIES)):
                create_story(root,backend='offline')
            with self.assertRaisesRegex(RuntimeError,'library exhausted'):
                create_story(root,backend='offline')
    def test_storyboard_dynamic_and_story_specific(self):
        with tempfile.TemporaryDirectory() as t:
            root=setup(Path(t));one,_=create_story(root,backend='offline');two,_=create_story(root,backend='offline')
            a=frame(1,one,w=240,h=420);b=frame(4,one,w=240,h=420)
            c=frame(1,two,w=240,h=420)
            motion=sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
            diff=sum(ImageStat.Stat(ImageChops.difference(a,c)).mean)/3
            self.assertGreater(motion,0.5)
            self.assertGreater(diff,1.5)
    def test_no_credentials_or_upload_needed_for_local_stories(self):
        with tempfile.TemporaryDirectory() as t:
            root=setup(Path(t))
            e,p=create_story(root,backend='offline')
            self.assertTrue(p.exists())
            self.assertFalse((root/'creative_drafts'/'renders'/f'{e["id"]}.mp4').exists())
            self.assertFalse(config(root)['autopublish_enabled'])
if __name__=='__main__':unittest.main()
