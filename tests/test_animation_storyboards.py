import json
import random
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from core.capabilities.youtube_autopilot import creative_factory as factory
from core.capabilities.youtube_autopilot.manager import setup
from core.capabilities.youtube_autopilot.visual_contract import audit_storyboard


class AnimationStoryboardTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = setup(Path(folder.name))
        self.episode = factory.offline_story(self.root, [], random.Random(1))

    def test_same_story_in_other_words_and_new_title_is_rejected(self):
        rewritten = deepcopy(self.episode)
        rewritten['title'] = "Nori & Blink: Our Day"
        for scene in rewritten['scenes']:
            scene['narration'] += " So it goes!"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            factory._check_candidate(rewritten, [self.episode])

    def test_invalid_stage_directions_and_fictional_object_declarations_are_rejected(self):
        for change, reason in [
            ({'action': 'juggle'}, 'unsupported action'),
            ({'prop': 'toaster'}, 'unsupported prop'),
            ({'action': 'carry', 'prop': 'rainbow'}, 'unavailable'),
            ({'prop': 'rainbow', 'visible_objects': ['apple']}, 'featured prop'),
            ({'narration': 'Nori walks toward the little boats.'}, 'absent'),
            ({'narration': 'Nori cheers for everyone.'}, 'no cue'),
            ({'action': 'carry', 'narration': 'Blink carries the apple home.'}, 'Nori performs'),
            ({'action': 'enter', 'narration': 'Nori enters and hops on the path.'}, 'additional movement'),
            ({'action': 'wave', 'narration': 'Nori waves to Blink and places the apple down.'}, 'additional movement'),
        ]:
            with self.subTest(change=change):
                ep = deepcopy(self.episode)
                ep['scenes'][0].update(change)
                audit = audit_storyboard(ep)
                self.assertFalse(audit['ok'])
                self.assertIn(reason, str(audit['issues']))

    def test_local_writer_retries_an_invalid_plan_without_random_substitution(self):
        invalid = deepcopy(self.episode)
        invalid['scenes'][0]['action'] = 'juggle'
        corrected = deepcopy(self.episode)
        corrected['scenes'][0]['action'] = 'enters'

        def reply(ep):
            return BytesIO(json.dumps({'choices': [{'message': {'content': json.dumps(ep)}}]}).encode())

        with patch.object(factory, '_local_model_reachable', return_value=True), \
                patch.object(factory.urllib.request, 'build_opener') as opener:
            call = opener.return_value.open
            call.side_effect = [reply(invalid), reply(corrected)]
            saved, _ = factory.create_story(self.root, backend='local-ai', seed=4)
        self.assertEqual(saved['creative']['backend'], 'lmstudio_qwen')
        self.assertEqual(call.call_count, 2)
        retry = json.loads(call.call_args.args[0].data)
        self.assertEqual(retry['response_format']['type'], 'json_schema')
        self.assertEqual(retry['messages'][-2]['role'], 'assistant')
        self.assertIn('unsupported action', retry['messages'][-1]['content'])
        self.assertEqual(saved['scenes'][0]['action'], self.episode['scenes'][0]['action'])

    def test_story_writer_never_calls_an_external_endpoint_or_follows_redirects(self):
        with patch.object(factory.socket, 'create_connection') as connect:
            self.assertFalse(factory._local_model_reachable({'lmstudio_url': 'https://example.org/v1'}))
            self.assertFalse(factory._local_model_reachable({'lmstudio_url': 'https://localhost@example.org'}))
            connect.assert_not_called()
        self.assertIsNone(factory._NoRedirects().redirect_request(None, None, 302, '', {}, 'https://example.org'))

    def test_narrator_describes_the_action_and_piper_receives_original_dialogue(self):
        planned = deepcopy(self.episode)
        for scene in planned['scenes']:
            scene.pop('narration')
            scene['dialogue'] = 'Is it my turn now?'
        response = BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(planned)}}]}).encode())
        with patch.object(factory, '_local_model_reachable', return_value=True), \
                patch.object(factory.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value = response
            saved, _ = factory.create_story(self.root, backend='local-ai')
        carry = next(s for s in saved['scenes'] if s['action'] == 'carry')
        self.assertIn('the apple', carry['narration'])
        self.assertTrue(carry['narration'].endswith(carry['dialogue']))
        self.assertTrue(audit_storyboard(saved)['ok'])

    def test_concurrent_workers_save_unique_complete_stories(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(factory.create_story, self.root, 'offline') for _ in range(8)]
            episodes = [future.result()[0] for future in futures]
        self.assertEqual(len({ep['creative']['plot_id'] for ep in episodes}), 8)
        self.assertEqual(len(list((self.root / 'creative_drafts').glob('*.json'))), 8)
        self.assertEqual(len({tuple(s['action'] for s in ep['scenes']) for ep in episodes}), 8)

    def test_fully_used_older_library_can_generate_new_edition_without_overwrites(self):
        drafts = self.root / 'creative_drafts'
        drafts.mkdir()
        for index in range(12):
            old = {'title': f'An earlier adventure {index}', 'scenes': [{'narration': 'Once upon a time.'}],
                   'creative': {'backend': 'offline_curated', 'plot_id': index, 'version': 4}}
            (drafts / f'old-{index}.json').write_text(json.dumps(old), encoding='utf8')
        ep, path = factory.create_story(self.root, 'offline', seed=1)
        self.assertEqual(ep['creative']['edition'], factory.OFFLINE_EDITION)
        self.assertEqual(len(list(drafts.glob('old-*.json'))), 12)
        self.assertTrue(path.exists())
