import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from core.capabilities import website_factory as wf
from core.capabilities import verified_website as vw
from core.capabilities.verified_facts import BusinessFacts, strict_json


def entry(value, status='approved_for_demo'):
    return {'value': value, 'status': status, 'source': {'kind': 'synthetic', 'reference': 'fictional test fixture'}}


def document(name='Test Garage', city='Haifa', category='Garage', language='en'):
    return {'version':1,'language':language,'facts':{'name':entry(name),'city':entry(city),'category':entry(category)},'services':[]}


def layout(hero='split', art='lines'):
    return {'hero':hero,'art':art,'sections':['about','services','contact'],
            'palette':{'background':'#F6F5F2','surface':'#FFFFFF','text':'#17212B','accent':'#1E40AF','on_accent':'#FFFFFF'},
            'density':'airy','corners':'sharp'}


class FactTests(unittest.TestCase):
    def test_unknown_conflicting_missing_fields_not_rendered(self):
        d=document(); d['facts']['phone']=entry('+972501234567','unverified'); d['facts']['address']=entry('Unknown address','conflicting'); d['services']=[entry('Oil change'),entry('Lifetime warranty','unverified')]
        f=BusinessFacts.parse(d)
        self.assertEqual(f.render_data(),{'language':'en','name':'Test Garage','city':'Haifa','category':'Garage','services':['Oil change']})
        self.assertFalse(f.report()['publication_approved'])
        self.assertEqual(f.report()['withheld_services'],1)

    def test_required_unknown_fails(self):
        d=document(); d['facts']['city']['status']='unverified'
        with self.assertRaises(ValueError): BusinessFacts.parse(d)

    def test_duplicate_json_keys_fail(self):
        with self.assertRaisesRegex(ValueError,'Duplicate key'): strict_json('{"city":"A","city":"B"}')

    def test_bad_source_and_phone_fail(self):
        d=document(); d['facts']['phone']=entry('javascript:alert(1)')
        with self.assertRaises(ValueError): BusinessFacts.parse(d)
        d=document(); d['facts']['city']['source']={'kind':'official_site','reference':'not-a-url'}
        with self.assertRaises(ValueError): BusinessFacts.parse(d)

    def test_unknown_claim_field_fail(self):
        d=document(); d['facts']['warranty']=entry('Lifetime warranty')
        with self.assertRaises(ValueError): BusinessFacts.parse(d)

    def test_approved_phone_safe_and_string_is_data(self):
        d=document(name='</script><script>alert(1)</script>'); d['facts']['phone']=entry('+972501234567')
        rendered=vw.render(BusinessFacts.parse(d),layout())
        self.assertIn('"phone": "+972501234567"',rendered['src/site-data.ts'])
        self.assertNotIn('<script>',rendered['src/App.tsx'])
        self.assertIn("href={'tel:' + facts.phone}",rendered['src/App.tsx'])

    def test_visual_contract_rejects_text_code_and_low_contrast(self):
        for key,value in [('hero','Herzliya'),('art','<script>'),('tagline','Lifetime warranty'),('sections',['about','about','contact'])]:
            with self.subTest(key=key):
                d=layout();d[key]=value
                with self.assertRaises(ValueError): vw.layout_contract(d)
        d=layout();d['palette']['accent']='#FFFFFF'
        with self.assertRaisesRegex(ValueError,'contrast'): vw.layout_contract(d)
        d=layout();d['palette']['accent']='red; content:"fake"'
        with self.assertRaises(ValueError): vw.layout_contract(d)


class WebsiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        manifest=self.root/'workspace_ui/package.json';manifest.parent.mkdir()
        manifest.write_text(json.dumps({'dependencies':{'react':'18.3.1','react-dom':'18.3.1'},'devDependencies':dict.fromkeys(('@types/react','@types/react-dom','typescript','vite'),'1.2.3')}))
        self.original=manifest.read_bytes()
        self.select=Mock(return_value='local-qwen');self.infer=Mock(return_value=json.dumps(layout()))
        self.loader=Mock(return_value={'text':'test skill instructions','sha256':'skillhash'})

    def fixture(self, slug, d):
        target=self.root/'.jarvis/website-demos'/slug
        (target/'design').mkdir(parents=True)
        for stage in wf.STAGES:
            output='Untrusted design text: Herzliya, 50% discount, free shipping, lifetime warranty.'
            (target/'design'/f'{stage}.json').write_text(json.dumps({'identity':{'stage':stage},'completion_checked':True,'output':output,'output_sha256':wf.sc.digest(output)}))
        facts=target/'facts.json';facts.write_text(json.dumps(d))
        output=target/'verified-preview'
        output.mkdir()
        return output,facts

    def job(self,slug,facts,**kw):
        return vw.run(slug,facts,approved=kw.pop('approved',True),facts_approved=kw.pop('facts_approved',True),root=self.root,select=self.select,infer=self.infer,loader=self.loader,**kw)

    def test_three_businesses_model_injection_blocked(self):
        cases=[('garage',document('מוסך לדוגמה','חיפה','מוסך','he'),'city','הרצליה'),('barber',document('Example Barber','Netanya','Barber'),'discount','50% discount'),('bakery',document('Example Bakery','London','Bakery'),'shipping','Free shipping')]
        for slug,d,key,value in cases:
            with self.subTest(slug=slug):
                target,facts=self.fixture(slug,d); bad=layout();bad[key]=value
                self.infer.side_effect=[json.dumps(bad),json.dumps(layout())]
                r=self.job(slug,facts)
                source='\n'.join(p.read_text() for p in (target/'src').glob('*'))
                self.assertTrue(r['react_generated']);self.assertFalse(r['publication_approved'])
                self.assertNotIn(value,source);self.assertNotIn('Lifetime warranty',source)
                self.assertIn('test skill instructions',self.infer.call_args.args[1])
        self.assertEqual(self.select.call_count,3)
        self.assertEqual((self.root/'workspace_ui/package.json').read_bytes(),self.original)

    def test_legacy_react_output_remains_untouched(self):
        output, facts = self.fixture('existing', document())
        project = output.parent
        (project / 'src').mkdir()
        (project / 'src' / 'App.tsx').write_text('original hand-edited React source', encoding='utf-8')
        (project / 'index.html').write_text('legacy scaffold', encoding='utf-8')
        (project / '.build-state.json').write_text('legacy checkpoint', encoding='utf-8')
        result = self.job('existing', facts)
        self.assertEqual(result['output_directory'], str(output))
        self.assertEqual((project / 'src' / 'App.tsx').read_text(), 'original hand-edited React source')
        self.assertEqual((project / 'index.html').read_text(), 'legacy scaffold')
        self.assertEqual((project / '.build-state.json').read_text(), 'legacy checkpoint')
        self.assertTrue((output / 'src' / 'App.tsx').exists())

    def test_model_low_contrast_accent_text_is_repaired_and_saved(self):
        output, facts = self.fixture('contrast', document())
        bad = layout()
        bad['palette']['on_accent'] = bad['palette']['accent']
        self.infer.return_value = json.dumps(bad)
        first = self.job('contrast', facts)
        self.assertTrue(first['react_generated'])
        self.assertEqual(first['layout_source'], 'local_model_contrast_corrected')
        checkpoint = json.loads((output/'verified-layout.json').read_text())
        self.assertEqual(checkpoint['layout_source'], 'local_model_contrast_corrected')
        palette = checkpoint['layout']['palette']
        self.assertGreaterEqual(vw.contrast(palette['on_accent'], palette['accent']), 4.5)
        self.assertEqual(palette['accent'], bad['palette']['accent'])
        self.assertEqual(self.infer.call_count, 1)
        self.assertEqual(self.job('contrast', facts), first)
        self.assertEqual(self.infer.call_count, 1)

    def test_model_low_contrast_non_accent_text_still_fails(self):
        output, facts = self.fixture('contrast-other', document())
        bad = layout()
        bad['palette']['text'] = bad['palette']['background']
        self.infer.return_value = json.dumps(bad)
        with self.assertRaisesRegex(ValueError, 'No valid visual contract'):
            self.job('contrast-other', facts)
        self.assertEqual(self.infer.call_count, 2)
        self.assertFalse((output/'verified-layout.json').exists())
        self.assertFalse((output/'src').exists())

    def test_no_valid_layout_no_source_saved(self):
        target,facts=self.fixture('bad',document());bad=layout();bad['phone']='+972501234567'
        self.infer.return_value=json.dumps(bad)
        with self.assertRaisesRegex(ValueError,'No valid visual contract'): self.job('bad',facts)
        self.assertFalse((target/'src').exists());self.assertFalse((target/'verified-layout.json').exists());self.assertFalse((target.parent/'.skill-composer.running').exists())

    def test_resume_preserves_files_and_refuses_changed_facts(self):
        target,facts=self.fixture('resume',document()); first=self.job('resume',facts); second=self.job('resume',facts)
        self.assertEqual(first,second);self.infer.assert_called_once()
        facts.write_text(json.dumps(document(city='Tel Aviv')))
        with self.assertRaisesRegex(ValueError,'checkpoint differs'):self.job('resume',facts)

    def test_refuses_changed_source(self):
        target,facts=self.fixture('modified',document());self.job('modified',facts)
        p=target/'src/App.tsx';p.write_text('user code')
        with self.assertRaisesRegex(ValueError,'Existing source differs'):self.job('modified',facts)
        self.assertEqual(p.read_text(),'user code')

    def test_no_approval_no_model(self):
        _,facts=self.fixture('approval',document())
        with self.assertRaisesRegex(ValueError,'Explicit human'):self.job('approval',facts,facts_approved=False)
        self.select.assert_not_called()

    def test_invalid_facts_no_model(self):
        d=document();d['facts']['city']['status']='conflicting';_,facts=self.fixture('invalid',d)
        with self.assertRaises(ValueError):self.job('invalid',facts)
        self.select.assert_not_called()

    def test_explicit_layout_no_model(self):
        target,facts=self.fixture('explicit',document()); path=target/'layout-input.json';path.write_text(json.dumps(layout('centered','rings')))
        r=self.job('explicit',facts,layout_file=path)
        self.assertEqual(r['layout_source'],'explicit');self.select.assert_not_called();self.infer.assert_not_called()
        self.assertIn('lang="en" dir="ltr"',(target/'index.html').read_text())

    def test_direct_legacy_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, 'unverified_draft'):
            wf.run('legacy','facts','title',approved=True,root=self.root,select=self.select)
        self.select.assert_not_called()

    def test_refuses_redirected_output(self):
        target,facts=self.fixture('redirect',document())
        outside=self.root/'outside';outside.mkdir()
        try:
            (target/'src').symlink_to(outside,target_is_directory=True)
        except OSError:
            self.skipTest('symlink permission unavailable')
        with self.assertRaisesRegex(ValueError,'Redirected path'): self.job('redirect',facts)
        self.select.assert_not_called()
        self.assertEqual(list(outside.iterdir()),[])

    def test_old_cli_requires_explicit_legacy_flag(self):
        with patch('sys.argv',['website_factory','--slug','example','--facts','old','--title','old','--approve-design']),patch.object(wf,'run') as old:
            self.assertEqual(wf.main(),1);old.assert_not_called()
