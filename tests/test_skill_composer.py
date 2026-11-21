import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock

from core.capabilities import skill_composer as sc
from services import local_ai_runtime as rt


def fixture_skill(ref):
    text = f'Actual test skill instructions for {ref}: use a distinct color system.'
    return {'id': ref, 'path': ref + '/SKILL.md', 'sha256': sc.digest(text), 'text': text}


class ComposerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.select = Mock(side_effect=lambda kind, **kw: kind)
        self.infer = Mock(side_effect=lambda kind, model, prompt: 'design output ' + kind + '\n' + sc.END_MARKER)

    def run_job(self, **kwargs):
        return sc.run('Verified demo brief', 'test-react', review=True, allow_switch=True,
                      root=self.root, loader=fixture_skill, select=self.select, infer=self.infer, **kwargs)

    def test_unmarked_result_retries_and_never_saves(self):
        self.infer.side_effect = ['unfinished sentence', 'still unfinished']
        with self.assertRaisesRegex(ValueError, 'checkpoint not saved'):
            self.run_job()
        self.assertEqual(self.infer.call_count, 2)
        target = sc.safe_target(self.root, 'test-react')
        self.assertEqual(list(target.glob('*.json')), [])

    def test_marker_retry_returns_clean_content(self):
        infer = Mock(side_effect=['unfinished', 'Complete.\n' + sc.END_MARKER])
        self.assertEqual(sc.infer_checked(infer, 'qwen', 'model', 'prompt'), 'Complete.')
        self.assertEqual(infer.call_count, 2)

    def test_engine_passed_to_art_direction_and_checkpoint_bound(self):
        result = self.run_job(engine_guidance='engine says steel blue')
        self.assertTrue(result['design_engine_guidance_used'])
        self.assertIn('engine says steel blue', self.infer.call_args_list[0].args[2])
        self.assertNotIn('engine says steel blue', self.infer.call_args_list[1].args[2])
        with self.assertRaisesRegex(ValueError, 'Checkpoint changed'):
            self.run_job(engine_guidance='different guidance')

    def test_checkpoint_tamper_rejected(self):
        result = self.run_job()
        path = Path(result['output_directory']) / 'art-direction.json'
        data = json.loads(path.read_text())
        data['output'] = 'changed'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'Checkpoint changed'):
            self.run_job()

    def test_engine_output_bounded(self):
        path = self.root / 'engine.txt'
        path.write_text('Design recommendations', encoding='utf-8')
        self.assertEqual(sc.read_engine_output(path), 'Design recommendations')
        path.write_bytes(b'x' * (sc.MAX_ENGINE_BYTES + 1))
        with self.assertRaises(ValueError): sc.read_engine_output(path)

    def test_real_instruction_text_and_stage_order(self):
        result = self.run_job()
        self.assertEqual(result['completed'], ['art-direction', 'design-system', 'content', 'critique'])
        self.assertEqual([c.args[0] for c in self.select.call_args_list], ['qwen', 'qwen', 'qwen', 'gemma'])
        self.assertIn('Actual test skill instructions', self.infer.call_args_list[0].args[2])
        self.assertIn('design output qwen', self.infer.call_args_list[-1].args[2])
        self.assertFalse(result['react_generated'])
        self.assertEqual(len(list(Path(result['output_directory']).glob('*.json'))), 4)

    def test_resume_after_review_failure(self):
        self.infer.side_effect = [v + '\n' + sc.END_MARKER for v in ('a', 'b', 'c')] + [RuntimeError('gemma failed')]
        with self.assertRaises(RuntimeError): self.run_job()
        self.select.reset_mock()
        self.infer.reset_mock(side_effect=True)
        self.infer.return_value = 'review\n' + sc.END_MARKER
        self.run_job()
        self.select.assert_called_once_with('gemma', allow_switch=True)

    def test_plan_no_writes_or_inference(self):
        self.assertEqual(self.run_job(plan_only=True)['status'], 'skills_resolved')
        self.assertFalse((self.root / '.jarvis').exists())
        self.select.assert_not_called()

    def test_preflight_missing_skill(self):
        with self.assertRaises(ValueError):
            sc.run('brief', 'test', review=True, allow_switch=True, root=self.root,
                   loader=Mock(side_effect=ValueError('missing')), select=self.select)
        self.assertFalse((self.root / '.jarvis').exists())
        self.select.assert_not_called()

    def test_resume_refuses_changed_brief(self):
        self.run_job()
        with self.assertRaises(ValueError):
            sc.run('different brief', 'test-react', review=True, allow_switch=True, root=self.root,
                   loader=fixture_skill, select=self.select, infer=self.infer)

    def test_path_traversal(self):
        with self.assertRaises(ValueError): sc.safe_target(self.root, '../escape')

    def test_budget(self):
        skill = fixture_skill('anything')
        skill['text'] = 'x' * (sc.MAX_PROMPT_BYTES + 1)
        with self.assertRaises(ValueError): sc.build_prompt('task', 'brief', [skill], [])

    def test_oversized_critique_splits_and_resumes_design(self):
        initial = sc.run('Verified demo brief', 'test-react', review=False,
            allow_switch=True, root=self.root, loader=fixture_skill, select=self.select, infer=self.infer)
        target = Path(initial['output_directory'])
        before = {p.name: p.read_bytes() for p in target.glob('*.json')}
        self.select.reset_mock(); self.infer.reset_mock()
        def loader(ref):
            skill = fixture_skill(ref)
            if ref.startswith('anti-slop/'):
                skill['text'] = ref + 'x' * 34000
                skill['sha256'] = sc.digest(skill['text'])
            return skill
        result = sc.run('Verified demo brief', 'test-react', review=True, allow_switch=True,
                        root=self.root, loader=loader, select=self.select, infer=self.infer)
        self.select.assert_called_once_with('gemma', allow_switch=True)
        self.assertEqual(self.infer.call_count, 2)
        for call in self.infer.call_args_list:
            prompt = call.args[2]
            self.assertLessEqual(len(prompt.encode('utf-8')), sc.MAX_PROMPT_BYTES)
            self.assertIn('art-direction', prompt)
            self.assertIn('design-system', prompt)
            self.assertIn('content', prompt)
        self.assertEqual(result['completed'][-1], 'critique')
        self.assertIn('Review 2/2', json.loads((target / 'critique.json').read_text())['output'])
        for name, data in before.items():
            self.assertEqual((target / name).read_bytes(), data)

    def test_large_review_falls_back_to_individual_artifacts(self):
        skills = [dict(fixture_skill(ref), text=ref + 'x' * 46000) for ref in ('a/b', 'c/d')]
        prior = [{'stage': stage, 'output': stage + 'y' * 9000} for stage in ('art', 'design', 'content')]
        prompts = sc.stage_prompts('critique', 'review', 'brief', skills, prior)
        self.assertEqual(len(prompts), 6)
        for skill in skills:
            for artifact in prior:
                self.assertTrue(any(skill['text'] in p and artifact['output'] in p for p in prompts))
        self.assertTrue(all(len(p.encode('utf-8')) <= sc.MAX_PROMPT_BYTES for p in prompts))
        with self.assertRaises(sc.PromptBudgetError):
            sc.stage_prompts('content', 'review', 'brief', skills, prior)

    def test_all_stage_refs_resolve_through_real_loader(self):
        packs = self.root / 'packs'
        index = []
        caps = {}
        for _, _, refs, _ in sc.STAGES:
            for ref in refs:
                package, sep, skill = ref.partition('/')
                self.assertTrue(sep and package and skill, ref)
                pack = packs / package
                path = pack / skill / 'SKILL.md'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('Actual fixture instructions: ' + ref, encoding='utf-8')
                index.append({'source': package, 'name': skill, 'path': path.relative_to(packs).as_posix()})
                caps[package] = SimpleNamespace(trust='reviewed', local_path=pack)
        index_path = packs / '_skill-index.json'
        index_path.write_text(json.dumps(index), encoding='utf-8')
        with patch.object(sc.activator, 'PACKS', packs), \
             patch.object(sc.activator, 'INDEX', index_path), \
             patch.object(sc.activator, 'get_capability', side_effect=caps.get), \
             patch.object(sc, 'get_capability', side_effect=caps.get), \
             patch.object(sc, 'capability_state', return_value='ready'):
            result = sc.run('brief', 'test-react', review=True, allow_switch=False,
                            root=self.root, plan_only=True, select=self.select, infer=self.infer)
        self.assertEqual(result['status'], 'skills_resolved')
        self.assertEqual(len(result['stages']), 4)
        self.select.assert_not_called()
        self.infer.assert_not_called()

    def test_malformed_skill_reference_has_useful_error(self):
        for ref in ('impeccable', '/humanizer', 'humanizer/', 'a/b/c'):
            with self.assertRaisesRegex(ValueError, 'expected package/skill'):
                sc.load_skill(ref)

    def test_catalog_read_actual_file_and_reject_escape(self):
        pack = self.root / 'packs' / 'demo'
        pack.mkdir(parents=True)
        (pack / 'SKILL.md').write_text('actual design instructions', encoding='utf-8')
        with patch.object(sc.activator, 'PACKS', pack.parent), \
             patch.object(sc, 'get_capability', return_value=SimpleNamespace(trust='reviewed', local_path=pack)), \
             patch.object(sc, 'capability_state', return_value='ready'), \
             patch.object(sc.activator, 'catalog', return_value=[{'name': 'demo', 'path': 'demo/SKILL.md'}]):
            self.assertEqual(sc.load_skill('demo/demo')['text'], 'actual design instructions')
            (pack.parent / 'SKILL.md').write_text('outside', encoding='utf-8')
            with patch.object(sc.activator, 'catalog', return_value=[{'name': 'demo', 'path': 'SKILL.md'}]):
                with self.assertRaises(ValueError): sc.load_skill('demo/demo')


class ModelSwitchTests(unittest.TestCase):
    def setUp(self):
        self.q = rt.MODEL_KEYS['qwen']; self.g = rt.MODEL_KEYS['gemma']
        self.rows = [{'identifier': self.q, 'status': 'idle', 'queued': 0}]
        self.calls = []
        def call(args, timeout):
            self.calls.append(args[1:]);
            if args[1] == 'unload': self.rows.clear()
            return SimpleNamespace(returncode=0, stdout=json.dumps(self.rows))
        def load(kind, **kw):
            key = rt.MODEL_KEYS[kind]
            if not self.rows: self.rows.append({'identifier': key, 'status': 'idle', 'queued': 0})
            return key
        for n, v in [('BASE_URL', 'http://127.0.0.1:1234'), ('server_online', Mock(return_value=True)),
                     ('require_local_ai_available', Mock()), ('_lms', Mock(return_value='lms')),
                     ('_run', Mock(side_effect=call)), ('ensure_model', Mock(side_effect=load))]:
            p = patch.object(rt, n, v); p.start(); self.addCleanup(p.stop)

    def test_switch_exact_idle_model(self):
        self.assertEqual(rt.prepare_exclusive_model('gemma', allow_switch=True), self.g)
        self.assertIn(['unload', self.q], self.calls)
        self.assertEqual([r['identifier'] for r in self.rows], [self.g])

    def test_no_switch_without_opt_in(self):
        with self.assertRaises(RuntimeError): rt.prepare_exclusive_model('gemma')
        self.assertNotIn(['unload', self.q], self.calls)

    def test_busy_missing_status_unknown_and_multiple(self):
        for rows in ([{'identifier': self.q, 'status': 'generating', 'queued': 0}],
                     [{'identifier': self.q}], [{'identifier': self.q, 'status': 'idle', 'queued': 2}],
                     [{'identifier': 'unknown', 'status': 'idle', 'queued': 0}],
                     [{'identifier': self.q}, {'identifier': self.g}]):
            self.rows[:] = rows
            with self.assertRaises(RuntimeError): rt.prepare_exclusive_model('gemma', allow_switch=True)
        self.assertFalse(any(c[0] == 'unload' for c in self.calls))
        rt.ensure_model.assert_not_called()

    def test_same_model_no_unload(self):
        self.assertEqual(rt.prepare_exclusive_model('qwen'), self.q)
        self.assertFalse(any(c[0] == 'unload' for c in self.calls))

    def test_external_endpoint_refused(self):
        with patch.object(rt, 'BASE_URL', 'https://example.com'):
            with self.assertRaises(RuntimeError): rt.prepare_exclusive_model('qwen')
        self.assertEqual(self.calls, [])

    def test_gaming_blocks(self):
        rt.require_local_ai_available.side_effect = RuntimeError('gaming')
        with self.assertRaises(RuntimeError): rt.prepare_exclusive_model('gemma', allow_switch=True)
        self.assertEqual(self.calls, [])


if __name__ == '__main__': unittest.main()
