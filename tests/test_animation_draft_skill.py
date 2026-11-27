from contextlib import redirect_stdout
from io import StringIO
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent.jarvis_agent import JarvisAgent
from core.config import AppConfig
from core.capabilities.router import requests_local_episode
from core.capabilities.youtube_autopilot import creative_factory, skill_runtime
from core.capabilities.youtube_autopilot.manager import setup, dump
from core.capabilities.youtube_autopilot.stage import sample_pose


class AnimationDraftSkillTests(unittest.TestCase):
    def test_firefly_keeps_flying_while_a_carried_prop_is_held(self):
        scene = {"shot":"tracking", "prop":"apple", "action":"carry"}
        end = sample_pose(scene, 1., 3.)
        hold = sample_pose(scene, 1.2, 3.)
        self.assertEqual(end.prop, hold.prop)
        self.assertNotEqual(end.firefly, hold.firefly)

    def test_explicit_agent_request_works_without_conversational_model(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = SimpleNamespace(base_dir=Path(directory))
            agent = JarvisAgent(AppConfig(), worker)
            result = {"title":"Nori & Blink", "state":"rendered_for_review",
                      "render":{"video":"review.mp4"}}
            with patch.object(skill_runtime, "execute", return_value=result) as make:
                reply = agent.process("JARVIS, create an English kids animation draft!")
            make.assert_called_once_with("create-draft", root=worker.base_dir/"var"/"youtube_autopilot",
                                         backend="auto", render=True)
            self.assertIn("review.mp4", reply.gui_text)
            self.assertTrue(requests_local_episode("תכין פרק חדש של נורי ובלינק"))
            for text in ("How do I create a kids cartoon?", "Make a cartoon about my dog",
                         "Create a website for a children's animation studio"):
                self.assertFalse(requests_local_episode(text))

    def test_caption_uses_visible_ink_bounds_or_fails_before_encoding(self):
        caption = "A little higher up the hill"
        face, layout, box = creative_factory._caption_layout(caption, 240, 420)
        for line, x, y in layout:
            left, top, right, bottom = face.getbbox(line)
            self.assertGreaterEqual(x+left, box[0])
            self.assertLessEqual(x+right, box[2])
            self.assertGreaterEqual(y+top, box[1])
            self.assertLessEqual(y+bottom, box[3])
        self.assertEqual(" ".join(row[0] for row in layout), caption)
        with self.assertRaisesRegex(ValueError, "cannot fit"):
            creative_factory._caption_layout("W"*59, 240, 420)

    def test_rejected_render_and_reaudited_story_do_not_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup(Path(directory))
            with patch.object(creative_factory, "render_draft", return_value={"mechanical_qa_error":"static scene"}):
                result = skill_runtime.execute("create-draft", root=root, backend="offline", render=True)
                with redirect_stdout(StringIO()):
                    self.assertEqual(skill_runtime.main(["create-draft", "--root", str(root), "--backend", "offline", "--render"]), 1)
            self.assertEqual(result["state"], "render_rejected")
            path = Path(result["story"])
            episode = json.loads(path.read_text(encoding="utf8"))
            report = {"animation_method":"storybook_rig", "story_digest":creative_factory.story_digest(episode),
                      "mechanical_qa":{"seconds":23}}
            dump(root/"creative_drafts"/"renders"/(episode["id"]+".review.json"), report)
            episode["scenes"][0]["caption"] = "A changed caption"
            dump(path, episode)
            audit = skill_runtime.execute("audit-draft", root=root, draft_id=episode["id"])
            self.assertIn("changed", audit["render_report"]["mechanical_qa_error"])
            self.assertFalse(audit["release_gate"]["ready_for_manual_publication_review"])
            with redirect_stdout(StringIO()):
                self.assertEqual(skill_runtime.main(["audit-draft", "--root", str(root), "--draft-id", episode["id"]]), 1)
