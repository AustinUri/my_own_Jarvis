import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from core.capabilities import website_factory as wf

APP = 'export default function App() { return <main dir="rtl"><h1>מוסך</h1></main>; }\n'
CSS = 'main { max-width: 72rem; }\na:focus-visible { outline: 2px solid; }\n@media (prefers-reduced-motion: reduce) { * { animation: none; } }\n'

class WebsiteFactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root / '.jarvis' / 'website-demos' / 'test-site'
        (self.target / 'design').mkdir(parents=True)
        for stage in wf.STAGES:
            content = 'reviewed ' + stage
            self.put(self.target / 'design' / (stage + '.json'), {
                'identity': {'stage': stage}, 'completion_checked': True,
                'output': content, 'output_sha256': wf.sc.digest(content)})
        (self.root / 'workspace_ui').mkdir()
        self.manifest = self.root / 'workspace_ui' / 'package.json'
        self.put(self.manifest, {'dependencies': {'react': '18.3.1', 'react-dom': '18.3.1'},
                 'devDependencies': dict.fromkeys(('@types/react', '@types/react-dom', 'typescript', 'vite'), '1.2.3')})
        self.original = self.manifest.read_bytes()
        self.select = Mock(return_value='local-qwen')
        self.infer = Mock(side_effect=[APP + wf.MARKER, CSS + wf.MARKER])
        self.loader = Mock(side_effect=lambda ref: {'text': 'actual tested ' + ref, 'sha256': wf.sc.digest(ref)})

    @staticmethod
    def put(path, data):
        path.write_text(json.dumps(data), encoding='utf-8')

    def run_job(self, approved=True, facts='Verified automotive repair garage in Haifa'):
        return wf.run('test-site', facts, 'מוסך', approved=approved, allow_switch=True,
                      root=self.root, loader=self.loader, select=self.select, infer=self.infer, unverified_draft=True)

    def test_creates_tsx_scaffold_no_changes_to_jarvis(self):
        result = self.run_job()
        self.assertTrue(result['react_generated'])
        self.assertFalse(result['built'])
        self.assertFalse(result['executed'])
        self.assertEqual((self.target / 'src/App.tsx').read_text(), APP)
        self.assertEqual((self.target / 'src/styles.css').read_text(), CSS)
        self.assertEqual(self.manifest.read_bytes(), self.original)
        self.select.assert_called_once_with('qwen', allow_switch=True)
        self.assertIn('actual tested anti-slop/antislop-code', self.infer.call_args_list[0].args[1])
        self.assertIn('reviewed critique', self.infer.call_args_list[0].args[1])
        self.assertIn('export default function App()', self.infer.call_args_list[1].args[1])
        self.assertIn('noindex,nofollow', (self.target / 'index.html').read_text())

    def test_requires_explicit_review(self):
        with self.assertRaisesRegex(ValueError, 'approve-design'): self.run_job(approved=False)
        self.select.assert_not_called()
        self.assertFalse((self.target / 'src').exists())

    def test_rejects_legacy_or_modified_design(self):
        path = self.target / 'design/content.json'
        data = json.loads(path.read_text())
        data['output'] = 'tampered'
        self.put(path, data)
        with self.assertRaisesRegex(ValueError, 'Invalid or legacy'): self.run_job()
        self.select.assert_not_called()

    def test_resumes_app_without_model_regeneration(self):
        self.infer.side_effect = [APP + wf.MARKER, 'unmarked', 'unmarked']
        with self.assertRaisesRegex(ValueError, 'styles.css not saved'): self.run_job()
        self.assertEqual((self.target / 'src/App.tsx').read_text(), APP)
        self.assertFalse((self.target / 'src/styles.css').exists())
        self.infer.reset_mock(side_effect=True)
        self.infer.return_value = CSS + wf.MARKER
        self.run_job()
        self.assertEqual(self.infer.call_count, 1)
        self.run_job()
        self.assertEqual(self.infer.call_count, 1)

    def test_never_overwrites_changed_source(self):
        self.run_job()
        path = self.target / 'src/App.tsx'
        path.write_text('manual edit')
        with self.assertRaisesRegex(ValueError, 'refusing overwrite'): self.run_job()
        self.assertEqual(path.read_text(), 'manual edit')

    def test_rejects_untracked_existing_files(self):
        (self.target / 'index.html').write_text('previous site')
        with self.assertRaisesRegex(ValueError, 'Existing output'): self.run_job()
        self.select.assert_not_called()

    def test_rejects_changed_facts(self):
        self.run_job()
        with self.assertRaisesRegex(ValueError, 'Build inputs changed'): self.run_job(facts='different')

    def test_refuses_symlink_source_directory(self):
        outside = self.root / 'outside'
        outside.mkdir()
        try:
            (self.target / 'src').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('symlink permission unavailable')
        with self.assertRaisesRegex(ValueError, 'Redirected path'): self.run_job()
        self.select.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])

    def test_source_heuristics(self):
        for invalid in ('unfinished', APP + '\n```\n' + wf.MARKER,
                        'import x from "external";\n' + APP + wf.MARKER,
                        APP + 'fetch("/data");\n' + wf.MARKER):
            with self.assertRaises(ValueError): wf.extract_source(invalid, 'App.tsx')
        with self.assertRaises(ValueError): wf.extract_source('body{}\n' + wf.MARKER, 'styles.css')

if __name__ == '__main__': unittest.main()
