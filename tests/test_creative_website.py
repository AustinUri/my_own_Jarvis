"""Focused tests for AI-composed but claim-locked React previews."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.capabilities import creative_website as cw
from core.capabilities import website_factory as wf
from core.capabilities.verified_facts import BusinessFacts


def fact(value, status='approved_for_demo'):
    return {'value': value, 'status': status, 'source': {'kind':'synthetic', 'reference':'test fixture'}}


def business(name='Test Garage', city='Haifa', category='Garage', language='en', services=()):
    return {'version': 1, 'language':language,
            'facts': {'name':fact(name),'category':fact(category),'city':fact(city),
                      'address':fact('Fake Avenue 9','unverified'), 'phone':fact('+972501234567','unverified')},
            'services':[fact(s) for s in services]}


def design_plan(with_services=False, accent=False):
    def field(value, role): return {'kind':'field','field':value,'role':role}
    def sec(id,layout,tone,items): return {'id':id,'layout':layout,'tone':tone,'items':items}
    sections = [sec('hero','split' if not accent else 'mosaic','background',[
        {'kind':'group','layout':'offset','items':[field('category','eyebrow'),field('name','display')]},
        {'kind':'graphic','variant':'typographic'}, {'kind':'cta'}]),
        sec('about','wide','surface',[field('city','body'),field('category','heading')])]
    if with_services:
        sections.append(sec('services','mosaic','background',[{'kind':'services','variant':'grid'}]))
    sections.append(sec('contact','stack','surface',[{'kind':'contact'}]))
    return {'version':1,'palette':{'background':'#F6F5F2','surface':'#FFFFFF','text':'#17212B','accent':'#1E40AF','on_accent':'#FFFFFF'},
            'style':{'typography':'editorial' if accent else 'industrial','corners':'sharp','spacing':'airy'},
            'sections':sections}


class ContractTests(unittest.TestCase):
    def test_valid_nested_creative_plan(self):
        p = cw.validate_plan(design_plan(), BusinessFacts.parse(business()))
        self.assertEqual(len(p['sections']),3)
        self.assertGreater(cw._count_nodes(p['sections'][0]['items']),3)

    def test_rejects_unverified_slots_and_services(self):
        f=BusinessFacts.parse(business())
        p=design_plan(); p['sections'][1]['items'].append({'kind':'field','field':'address','role':'body'})
        with self.assertRaisesRegex(ValueError, 'Unapproved field'): cw.validate_plan(p,f)
        p=design_plan(with_services=True)
        with self.assertRaisesRegex(ValueError,'[Ss]ervice'): cw.validate_plan(p,f)

    def test_rejects_invented_claims_and_markup(self):
        f=BusinessFacts.parse(business())
        for mutate in (
            lambda p: p.update({'claims':['50% discount']}),
            lambda p: p['sections'][0]['items'][1].update({'text':'Lifetime warranty'}),
            lambda p: p['sections'][0]['items'][0]['items'][0].update({'field':'Herzliya'}),
            lambda p: p['sections'][0]['items'].append({'kind':'script','url':'http://evil'}),
            lambda p: p['sections'][0]['items'].append({'kind':'field','field':'price','role':'body'}),
            lambda p: p['sections'][0]['items'].append({'kind':'group','layout':'stack','items':[]}),
        ):
            p=design_plan(); mutate(p)
            with self.subTest(p=p),self.assertRaises(ValueError): cw.validate_plan(p,f)

    def test_rejects_contrast_duplicate_sections_and_depth(self):
        f=BusinessFacts.parse(business())
        p=design_plan();p['palette']['text']=p['palette']['background']
        with self.assertRaisesRegex(ValueError,'contrast'):cw.validate_plan(p,f)
        p=design_plan();p['sections'].append(p['sections'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):cw.validate_plan(p,f)
        p=design_plan()
        node=p['sections'][0]['items'][0]
        for i in range(5): node={'kind':'group','layout':'stack','items':[node]}
        p['sections'][0]['items'][0]=node
        with self.assertRaisesRegex(ValueError,'depth'):cw.validate_plan(p,f)

    def test_render_never_embeds_model_authored_claims(self):
        f=BusinessFacts.parse(business(services=('Oil change','Brake service')))
        p=design_plan(with_services=True)
        sources=cw.render(f,p)
        self.assertIn('Oil change',sources['src/site-data.ts'])
        self.assertNotIn('Fake Avenue', ''.join(sources.values()))
        self.assertNotIn('+972501234567', ''.join(sources.values()))
        self.assertIn('prefers-reduced-motion',sources['src/styles.css'])
        self.assertIn(':focus-visible',sources['src/styles.css'])
        self.assertIn('skip',sources['src/App.tsx'])
        self.assertNotIn('Lifetime warranty', ''.join(sources.values()))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        manifest=self.root/'workspace_ui'/'package.json';manifest.parent.mkdir()
        manifest.write_text(json.dumps({'dependencies':{'react':'18.3.1','react-dom':'18.3.1'},
                'devDependencies':{x:'1.2.3' for x in ('vite','typescript','@types/react','@types/react-dom')}}))
        self.manifest=manifest
        self.original_manifest=manifest.read_bytes()
        self.select=Mock(return_value='qwen-local')
        self.infer=Mock(return_value=json.dumps(design_plan()))
        self.loader=Mock(side_effect=lambda ref:{'text':'SKILL: '+ref,'sha256':'sha-'+ref})

    def prep(self, slug='demo', facts=None):
        d=facts or business()
        project=self.root/'.jarvis'/'website-demos'/slug
        design_dir=project/'design';design_dir.mkdir(parents=True)
        for stage in wf.STAGES:
            output='UNTRUSTED DESIGN: Herzliya, free shipping, lifetime warranty.'
            (design_dir/(stage+'.json')).write_text(json.dumps({'identity':{'stage':stage},
                'completion_checked':True,'output':output,'output_sha256':wf.sc.digest(output)}))
        (project/'src').mkdir()
        (project/'src'/'App.tsx').write_text('Previous JARVIS site build preserved')
        (project/'verified-preview').mkdir()
        (project/'verified-preview'/'src.tsx').write_text('Verified previous remains untouched')
        f=project/'facts.json';f.write_text(json.dumps(d,ensure_ascii=False))
        return project,f

    def job(self,slug,facts,**kwargs):
        return cw.run(slug,facts,approved=kwargs.pop('approved',True), facts_approved=kwargs.pop('facts_approved',True),
            root=self.root, select=self.select, infer=self.infer, loader=self.loader, **kwargs)

    def test_model_composes_and_writes_only_creative_preview(self):
        project,f=self.prep()
        result=self.job('demo',f)
        self.assertTrue(result['react_generated'])
        self.assertEqual(result['composition_source'],'local_model')
        self.assertFalse(result['publication_approved'])
        self.assertFalse(result['built'])
        self.assertEqual(result['output_directory'],str(project/'creative-preview'))
        self.assertIn('SKILL: ui-ux-pro-max',self.infer.call_args.args[1])
        self.assertIn('SKILL: anti-slop/antislop-ui',self.infer.call_args.args[1])
        source=(project/'creative-preview/src/App.tsx').read_text()
        self.assertIn('layout-',source)
        self.assertEqual((project/'src/App.tsx').read_text(),'Previous JARVIS site build preserved')
        self.assertEqual((project/'verified-preview/src.tsx').read_text(),'Verified previous remains untouched')
        self.assertEqual(self.manifest.read_bytes(),self.original_manifest)
        self.assertEqual(self.job('demo',f),result)
        self.select.assert_called_once()
        self.infer.assert_called_once()

    def test_business_injection_cases_fail_before_save(self):
        for slug,doc,attack in [
            ('garage',business(name='Elias Garage',city='Haifa'),{'kind':'field','field':'Herzliya','role':'body'}),
            ('barber',business(name='Barber',city='Netanya'),{'kind':'field','field':'50% off','role':'body'}),
            ('bakery',business(name='Bakery',city='London'),{'kind':'field','field':'free delivery','role':'body'})]:
            with self.subTest(slug=slug):
                project,f=self.prep(slug,doc)
                p=design_plan();p['sections'][1]['items'].append(attack)
                self.infer.return_value=json.dumps(p)
                with self.assertRaisesRegex(ValueError,'No valid creative plan'):
                    self.job(slug,f)
                self.assertFalse((project/'creative-preview/src/App.tsx').exists())
                self.assertFalse((project/'creative-preview/creative-plan.json').exists())
        self.assertEqual(self.manifest.read_bytes(),self.original_manifest)

    def test_retries_once_then_success(self):
        project,f=self.prep('retry')
        bad=design_plan();bad['sections'][1]['items'].append({'kind':'field','field':'unverified','role':'body'})
        self.infer.side_effect=[json.dumps(bad),json.dumps(design_plan())]
        result=self.job('retry',f)
        self.assertTrue(result['react_generated']);self.assertEqual(self.infer.call_count,2)

    def test_change_in_approved_facts_refuses_overwrite(self):
        project,f=self.prep('update');self.job('update',f)
        raw=json.loads(f.read_text());raw['facts']['city']['value']='Tel Aviv';f.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError,'checkpoint differs'):
            self.job('update',f)

    def test_human_edit_refuses_overwrite(self):
        project,f=self.prep('edit');self.job('edit',f)
        (project/'creative-preview/src/styles.css').write_text('user authored file')
        with self.assertRaisesRegex(ValueError,'Existing creative output differs'):
            self.job('edit',f)

    def test_requires_explicit_approvals_no_model_selection(self):
        project,f=self.prep('blocked')
        with self.assertRaisesRegex(ValueError,'approval'):
            self.job('blocked',f,approved=False)
        self.select.assert_not_called()

    def test_explicit_plan_bypasses_ai(self):
        project,f=self.prep('explicit')
        p=project/'input-plan.json';p.write_text(json.dumps(design_plan(accent=True)))
        result=self.job('explicit',f,plan_file=p)
        self.assertEqual(result['composition_source'],'explicit')
        self.select.assert_not_called()
        self.infer.assert_not_called()

    def test_symlink_output_refused(self):
        project,f=self.prep('link')
        outside=self.root/'outside';outside.mkdir()
        try: (project/'creative-preview').symlink_to(outside,target_is_directory=True)
        except OSError: self.skipTest('No symlink support')
        with self.assertRaisesRegex(ValueError,'Redirected path'):
            self.job('link',f)
        self.assertEqual(list(outside.iterdir()),[])

    def test_cli_routes_creative_only_with_fact_file(self):
        with patch('sys.argv',['website_factory','--slug','demo','--creative','--facts-file','demo.json',
            '--approve-facts','--approve-design']),patch('core.capabilities.creative_website.run') as model_run:
            model_run.return_value={'ok':True}
            self.assertEqual(wf.main(),0)
            model_run.assert_called_once()
        with patch('sys.argv',['website_factory','--slug','demo','--creative']),patch('core.capabilities.creative_website.run') as model_run:
            self.assertEqual(wf.main(),1)
            model_run.assert_not_called()


if __name__ == '__main__':unittest.main()

class SkillSelectionTests(unittest.TestCase):
    def test_small_skill_included_fully(self):
        s='## Typography\n- Use readable Hebrew lettering\n'
        e=cw.skill_excerpt(s,max_bytes=100)
        self.assertEqual(e['selection'],s)
        self.assertEqual(e['selection_method'],'full')

    def test_large_skill_uses_audited_relevant_lines(self):
        s='## Typography\n- Use contrast and responsive spacing\n'+('Non-specific background prose.\n'*500)
        e=cw.skill_excerpt(s,max_bytes=150)
        self.assertEqual(e['selection_method'],'explicit_relevant_lines')
        self.assertLess(e['included_bytes'],e['original_bytes'])
        self.assertIn('responsive spacing',e['selection'])
        self.assertNotIn('Non-specific background prose.',e['selection'])

class ContrastRepairTests(unittest.TestCase):
    def test_repairs_only_model_button_text(self):
        f=BusinessFacts.parse(business())
        p=design_plan();p['palette']['on_accent']=p['palette']['accent']
        fixed,reason=cw.validate_model_plan(p,f)
        self.assertEqual(reason,'local_model_contrast_corrected')
        self.assertGreaterEqual(cw.vw.contrast(fixed['palette']['on_accent'],fixed['palette']['accent']),4.5)
        self.assertEqual(fixed['palette']['accent'],p['palette']['accent'])
        p=design_plan();p['palette']['text']=p['palette']['background']
        with self.assertRaisesRegex(ValueError,'text/background'):
            cw.validate_model_plan(p,f)


class LocalModelReliabilityTests(unittest.TestCase):
    def test_dynamic_contract_whitelists_only_approved_fields(self):
        facts=BusinessFacts.parse(business())
        contract=cw.prompt_contract(facts)
        self.assertIn('"field":"name|category|city"', contract)
        self.assertNotIn('"field":"name|category|city|address|tagline"',contract)
        self.assertIn('DO NOT create a services section',contract)
        self.assertIn('exactly the properties',contract)

    def test_only_schema_known_unapproved_optional_fields_may_be_omitted(self):
        facts=BusinessFacts.parse(business())
        p=design_plan()
        p['sections'][0]['items'].append({'kind':'field','field':'tagline','role':'body'})
        p['sections'][1]['items'].append({'kind':'field','field':'address','role':'small'})
        good, origin=cw.validate_model_plan(p,facts)
        self.assertEqual(origin,'local_model_optional_omitted')
        self.assertEqual(good['sections'][0]['items'],design_plan()['sections'][0]['items'])
        self.assertEqual(good['sections'][1]['items'],design_plan()['sections'][1]['items'])
        self.assertEqual(p['sections'][0]['items'][-1]['field'],'tagline') # original unchanged
        for payload in (('Herzliya','body'),('50% off','small'),('price','body')):
            bad=design_plan()
            bad['sections'][1]['items'].append({'kind':'field','field':payload[0],'role':payload[1]})
            with self.subTest(payload=payload),self.assertRaisesRegex(ValueError,'[Ii]nvalid field'):
                cw.validate_model_plan(bad,facts)

    def test_optional_omission_cannot_hide_untrusted_extra_properties(self):
        facts=BusinessFacts.parse(business())
        bad=design_plan()
        bad['sections'][0]['items'].append({'kind':'field','field':'tagline','role':'body','text':'Lifetime warranty'})
        with self.assertRaisesRegex(ValueError,'Unexpected or missing'):
            cw.validate_model_plan(bad,facts)

    def test_three_attempts_with_compact_repair_and_real_checkpoint(self):
        case=PipelineTests('test_model_composes_and_writes_only_creative_preview')
        case.setUp()
        try:
            project,f=case.prep('compactretry')
            first=design_plan();first['sections'][0]['items'].append({'kind':'field','field':'50% off','role':'body'})
            second=design_plan();second['sections'][0]['items'][1]['copy']='Invented claim'
            case.infer.side_effect=[json.dumps(first),json.dumps(second),json.dumps(design_plan())]
            result=case.job('compactretry',f)
            self.assertTrue(result['react_generated'])
            self.assertEqual(case.infer.call_count,3)
            self.assertIn('SKILL: ui-ux-pro-max', case.infer.call_args_list[0].args[1])
            self.assertNotIn('SKILL: ui-ux-pro-max', case.infer.call_args_list[1].args[1])
            self.assertIn('Allowed fields EXACTLY:', case.infer.call_args_list[1].args[1])
            self.assertTrue((project/'creative-preview/creative-plan.json').exists())
            self.assertEqual(case.job('compactretry',f),result)
            self.assertEqual(case.infer.call_count,3)
        finally:
            case.tearDown() if hasattr(case,'tearDown') else None
            case.doCleanups()

    def test_known_unapproved_optional_still_enforces_required_nodes(self):
        facts=BusinessFacts.parse(business())
        bad=design_plan()
        bad['sections'][1]['items']=[{'kind':'field','field':'tagline','role':'body'}]
        with self.assertRaisesRegex(ValueError,'[Ii]nvalid group|Missing hero|about identity'):
            cw.validate_model_plan(bad,facts)
