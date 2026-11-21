"""First-party project skill registration and video release boundaries (v0.6)."""
import unittest
import tempfile
from unittest.mock import patch
import core.capabilities.activator as activator
from pathlib import Path
from core.capabilities.registry import get_capability, capability_available
from core.capabilities.router import route_capabilities, available_capabilities
from core.capabilities.activator import skills_for
from core.capabilities.youtube_autopilot.skill_runtime import execute
from core.capabilities.youtube_autopilot.visual_contract import audit_storyboard, publication_gate

class RepoProjectSkillTests(unittest.TestCase):
    def test_first_party_skill_definitions_in_repo(self):
        for name in ('youtube-video-factory', 'website-factory'):
            c = get_capability(name)
            self.assertIsNotNone(c)
            self.assertEqual(c.source, 'jarvis-project')
            self.assertTrue(capability_available(name))
            self.assertTrue((c.local_path / 'SKILL.md').is_file())
            found = skills_for(name)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]['source'], 'jarvis-project')

    def test_project_activation_is_idempotent_and_preserves_manual_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder) / 'skills'
            manifest = Path(folder) / 'active.json'
            with patch.object(activator,'SKILLS_DIR',store), patch.object(activator,'ACTIVE_MANIFEST',manifest):
                first=activator.activate('youtube-video-factory')
                self.assertTrue((first/'SKILL.md').is_file())
                self.assertEqual(first,activator.activate('youtube-video-factory'))
                (first/'SKILL.md').write_text('CUSTOM USER EDIT',encoding='utf-8')
                with self.assertRaises(activator.ActivationError):
                    activator.activate('youtube-video-factory')

    def test_video_route_not_website_research(self):
        for text in ('Create an English kids animation', 'תייצר סרטון ילדים מקורי'):
            route = route_capabilities(text)
            self.assertEqual(route.domain,'video-production')
            self.assertIn('youtube-video-factory',available_capabilities(route))

    def test_website_route_not_generic_browser(self):
        for text in ('Build a website for a business', 'בנה אתר לעסק בנתניה'):
            route = route_capabilities(text)
            self.assertEqual(route.domain,'website-production')
            self.assertIn('website-factory',available_capabilities(route))

    def test_existing_generic_route_preserved(self):
        self.assertEqual(route_capabilities('Debug this Python service').domain,'coding')

    def test_skill_adapter_exposes_no_upload_action(self):
        data = execute('capabilities')
        self.assertFalse(data['uploads_allowed'])
        self.assertNotIn('publish',data['actions'])
        with self.assertRaises(ValueError):
            execute('publish')

    def test_missing_visual_story_object_blocks_creative_gate(self):
        scenes=[dict(narration='We find a sleepy moth beside the lantern',caption='Find the lantern',
                     setting='woodland',shot=('wide' if i%2 else 'medium'),
                     action=('enter' if i%2 else 'discover'),prop='moon') for i in range(6)]
        scenes[2]['action']='follow'
        ep={'title':'Night Lantern', 'description':'A moth needs the lantern', 'scenes':scenes}
        report=audit_storyboard(ep)
        self.assertFalse(report['ok'])
        gate=publication_gate(mechanical_passed=True,visual_contract_passed=report['ok'],
                              assets_approved=False,human_review_signed=False,
                              provenance_checked=False,animation_method='legacy_procedural')
        self.assertFalse(gate['ready_for_manual_publication_review'])

if __name__ == '__main__':unittest.main()
