import json
import tempfile
import unittest
from pathlib import Path
from core.capabilities.youtube_autopilot.episodes import EPISODES,validate_episode
from core.capabilities.youtube_autopilot.renderer import cartoon_frame
from core.capabilities.youtube_autopilot.manager import setup,plan,config,read,switch,run_one
from core.capabilities.youtube_autopilot.quality import inspect_story

class TestAutoPilot(unittest.TestCase):
    def test_all_original_stories_valid(self):
        for ep in EPISODES:inspect_story(ep)
    def test_cartoon_frame_dimensions(self):
        frame=cartoon_frame(1,EPISODES[0],w=360,h=640)
        self.assertEqual(frame.size,(360,640))
    def test_opt_in_rejects_accidental_enable(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=setup(Path(tmp)); self.assertFalse(config(r)['autopublish_enabled'])
            with self.assertRaises(ValueError):switch(r,True,'yes')
            self.assertFalse(config(r)['autopublish_enabled'])
    def test_unique_no_duplicate_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=setup(Path(tmp)); self.assertEqual(len(plan(r)),3)
            self.assertEqual(len(plan(r)),0)
            js=read(r/'jobs.json',[])
            self.assertEqual(len(set(j['id'] for j in js)),3)
            self.assertTrue(all(j['publish_at'] for j in js))
    def test_preview_without_voice_is_never_uploadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=setup(Path(tmp));plan(r)
            c=config(r);c.update({'width':360,'height':640,'fps':8,'scene_seconds':0.5})
            (r/'config.json').write_text(json.dumps(c),encoding='utf-8')
            x=run_one(r,preview=True)
            self.assertEqual(x['state'],'needs_voice')
            self.assertTrue(Path(x['video_path']).exists())
if __name__=='__main__':unittest.main()
