import base64
import subprocess
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from core.capabilities import browser_runtime as browser
from core.capabilities import lead_discovery as scout


def bing(target):
    encoded = base64.urlsafe_b64encode(target.encode()).decode().rstrip('=')
    return 'https://www.bing.com/ck/a?' + urlencode({'u': 'a1' + encoded})


class ScoutTests(unittest.TestCase):
    def test_nested_redirect(self):
        target = 'https://calmark.io/p/3V9ko'
        wrapped = bing('https://www.bing.com/alink/link?' + urlencode({'url': target}))
        self.assertEqual(scout.unwrap_bing(wrapped), target)
        self.assertEqual(scout.classify(scout.unwrap_bing(wrapped)), 'booking')
        self.assertEqual(scout.classify('https://calmark.io.fake.example/'), 'possible_official_site')
        self.assertEqual(scout.classify('https://www.instagram.com/shop'), 'social')
        self.assertEqual(scout.classify('https://easy.co.il/page/1'), 'directory')
        self.assertEqual(scout.unwrap_bing(bing('file:///etc/passwd')), bing('file:///etc/passwd'))
        self.assertEqual(scout.unwrap_bing('https://www.bing.com/ck/a?u=a1!'), 'https://www.bing.com/ck/a?u=a1!')

    def test_candidates_prioritize_booking_and_no_link(self):
        links = [{'label': label, 'url': url} for label, url in (
            ('Website Barber A', 'https://barbera.example'),
            ('Website Barber B', 'https://calmark.io/p/abc'),
            ('Directions Barber B', 'https://bing.com/maps'),
            ('Directions Barber C', 'https://bing.com/maps'))]
        entries = scout.candidates(links)
        self.assertEqual([e['business_name'] for e in entries], ['Barber B', 'Barber C', 'Barber A'])
        self.assertEqual(entries[1]['listed_links'], [])

    def test_discovery_returns_evidence_not_false_verification(self):
        calls = []
        def reader(url, **kwargs):
            calls.append((url, kwargs))
            links = ([{'label': 'Website Yakir barber | מספרה', 'url': bing('https://calmark.io/p/abc')}]
                     if len(calls) == 1 else [
                         {'label': 'Yakir barber - משה הס 7, נתניה - מספרה | איזי', 'url': bing('https://easy.co.il/page/1')},
                         {'label': 'Yakir barber - B144', 'url': 'https://b144.co.il/business/1'},
                         {'label': 'Unrelated business', 'url': 'https://unrelated.example'}])
            return {'status': 'read', 'links': links, 'cleanup_error': None}
        result = scout.discover('נתניה', 'מספרות גברים', limit=1, reader=reader)
        candidate = result['candidates'][0]
        self.assertEqual(candidate['website_status'], 'UNCERTAIN')
        self.assertIsNone(candidate['lead_score'])
        self.assertFalse(candidate['demo_ready'])
        self.assertEqual(len(candidate['sources_to_review']), 2)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(scout.host(url) == 'www.bing.com' and kw['include_links'] for url, kw in calls))

    def test_block_stops_search(self):
        with patch.object(scout, 'search_url', wraps=scout.search_url) as search:
            result = scout.discover('Netanya', 'barber', reader=lambda *a, **k: {'status': 'possible_block'})
        self.assertEqual(result['status'], 'blocked_or_unavailable')
        self.assertEqual(search.call_count, 1)
        self.assertEqual(result['candidates'], [])

    def test_directory_hosts_and_fragment_dedup(self):
        self.assertEqual(scout.classify('https://il.revieweuro.com/center/test'), 'directory')
        self.assertEqual(scout.classify('https://saparim.co.il/salon/test'), 'directory')
        self.assertEqual(scout.classify('https://revieweuro.com.fake.example/'), 'possible_official_site')
        links = [{'label': 'Yakir barber', 'url': url} for url in (
            'https://easy.co.il/page/1#:~:text=example', 'https://easy.co.il/page/1',
            'https://il.revieweuro.com/center/test', 'https://lee.co.il/b/test')]
        result = scout.evidence(links, 'Yakir barber')
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['url'], 'https://easy.co.il/page/1')
        self.assertFalse(any(x['kind'] == 'possible_official_site' for x in result))

    def test_directory_candidates_reject_category_wrong_city_and_unknown_host(self):
        links = [{'label': title, 'url': url} for title, url in (
            ('מוסך בדיקה - העצמאות 1, חיפה - מוסך | איזי', 'https://easy.co.il/page/123'),
            ('מוסך אחר - נתניה - מוסך | איזי', 'https://easy.co.il/page/124'),
            ('מוסכים בחיפה | איזי', 'https://easy.co.il/list/Garages'),
            ('מוסך מזויף - חיפה - מוסך | איזי', 'https://easy.co.il.fake.example/page/123'))]
        entries = scout.directory_candidates(links, 'חיפה')
        self.assertEqual([x['business_name'] for x in entries], ['מוסך בדיקה'])
        self.assertEqual(entries[0]['listed_links'], [])

    def test_fallback_search_is_bounded_and_keeps_status_uncertain(self):
        calls = []
        def reader(url, **kwargs):
            calls.append(url)
            links = ([], [{'label': 'מוסך בדיקה - חיפה - מוסך | איזי', 'url': 'https://easy.co.il/page/123'}],
                     [{'label': 'מוסך בדיקה - B144', 'url': 'https://b144.co.il/business/123'}])[len(calls)-1]
            return {'status': 'read', 'links': links}
        result = scout.discover('חיפה', 'מוסכים', limit=1, reader=reader)
        self.assertEqual(len(calls), 3)
        self.assertIn('site%3Aeasy.co.il%2Fpage%2F', calls[1])
        entry = result['candidates'][0]
        self.assertEqual(entry['website_status'], 'UNCERTAIN')
        self.assertIsNone(entry['lead_score'])
        self.assertEqual(len(entry['sources_to_review']), 2)

    def test_empty_or_blocked_fallback_stops(self):
        for status, expected in [('read', 'no_candidates_extracted'), ('possible_block', 'blocked_or_unavailable')]:
            with self.subTest(status=status):
                calls = []
                def reader(url, **kwargs):
                    calls.append(url)
                    return {'status': 'read' if len(calls) == 1 else status, 'links': []}
                result = scout.discover('חיפה', 'מוסכים', reader=reader)
                self.assertEqual(result['status'], expected)
                self.assertEqual(len(calls), 2)

    def test_possible_site_not_hidden_by_output_limit(self):
        links = [{'label': 'Barber A - Netanya - barber | Easy', 'url': f'https://easy.co.il/page/{i}'} for i in range(8)]
        links.append({'label': 'Barber A', 'url': 'https://barbera.example'})
        calls = []
        def reader(url, **kwargs):
            calls.append(url)
            return {'status': 'read', 'links': [{'label': 'Directions Barber A', 'url': 'https://bing.com/maps'}] if len(calls) == 1 else links}
        entry = scout.discover('Netanya', 'barber', limit=1, reader=reader)['candidates'][0]
        self.assertTrue(entry['possible_official_site'])
        self.assertLessEqual(len(entry['sources_to_review']), 6)

    def test_haifa_location_gate_and_directory_domains(self):
        def link(label, url):
            return {"label": label, "url": url}
        pages = iter([
            [link("Website מוסכי ורד", "https://facebook.com/garage"),
             link("Website מוסך שבתאי", "https://israelbusinessguide.com/catalog/hayfa/test"),
             link("Website מוסך יוני", "https://israelbusinessguide.com/catalog/hayfa/yoni")],
            [link("מוסכי ורד - יד חרוצים 2, נתניה - מוסך | איזי", "https://easy.co.il/page/1")],
            [link("מוסך שבתאי - מרקוני 4, חיפה - מוסך | איזי", "https://easy.co.il/page/2"),
             link("מוסך שבתאי", "https://www.d.co.il/80178161/28275/")],
            [link("רודולף מוסך יוני - מרקוני 3, חיפה - מוסך | איזי", "https://easy.co.il/page/3"),
             link("מוסך יוני", "https://mymusach.co.il/garage/test")],
        ])
        result = scout.discover("חיפה", "מוסכים", limit=3,
                                reader=lambda *a, **k: {"status": "read", "links": next(pages)})
        self.assertEqual([x["business_name"] for x in result["candidates"]], ["מוסך שבתאי", "מוסך יוני"])
        self.assertEqual(result["location_review"][0]["location"]["status"], "other_city_hint")
        self.assertTrue(all(not x["possible_official_site"] for x in result["candidates"]))
        self.assertTrue(all(x["lead_score"] is None for x in result["candidates"]))
        for domain in ("autoyas.com", "garage1.co.il", "caro.co.il", "index.webezier.com"):
            self.assertEqual(scout.classify("https://" + domain + "/test"), "directory")

    def test_location_unknown_and_conflicting(self):
        links = [{"label": f"Shop - Main 1, {city} - barber | Easy", "url": f"https://easy.co.il/page/{i}"}
                 for i, city in enumerate(("Haifa", "Netanya"))]
        self.assertEqual(scout.location_evidence(links, "Shop", "Haifa")["status"], "conflicting")
        self.assertEqual(scout.location_evidence([], "Shop", "Haifa")["status"], "unknown")
        pages = iter([[{"label": "Directions Shop", "url": "https://bing.com/maps"}], []])
        result = scout.discover("Haifa", "barber", reader=lambda *a, **k: {"status": "read", "links": next(pages)})
        self.assertEqual(result["status"], "location_review_required")
        self.assertEqual(result["candidates"], [])
        self.assertEqual(len(result["location_review"]), 1)

    def test_dco_directory_groups_fragments_and_filters_locations(self):
        rows = []
        for suffix, name, address in (("24843430", "מוסך שפיק רפול וטל רכבים", "שד' ההסתדרות 200, חיפה"),
                                      ("80178161", 'מוסך שבתאי שמר ק.ס. בע"מ', "מרקוני 4, חיפה"),
                                      ("80336499", "מוסך הנטר", "מוצקין 11, טירת כרמל")):
            url = f"https://www.d.co.il/{suffix}/28275/"
            rows.extend([{"label": name, "url": url},
                         {"label": "דירוג 4.5 מתוך 5", "url": url + "#page-block-reviews"},
                         {"label": address, "url": url + "#page-block-map"}])
        rows.append({"label": "Fake", "url": "https://www.d.co.il.fake.example/1/2/"})
        entries = scout.directory_entries(rows, "חיפה")
        self.assertEqual(len(entries), 3)
        self.assertEqual([x["location"]["status"] for x in entries],
                         ["city_hint_match", "city_hint_match", "other_city_hint"])
        self.assertEqual(entries[1]["business_name"], 'מוסך שבתאי שמר ק.ס. בע"מ')
        self.assertIsNone(scout.directory_path("https://d.co.il:8080/1/2/"))
        self.assertIsNone(scout.directory_path("https://d.co.il/redirect/"))

    def test_digital_signals_do_not_equate_whatsapp_share_with_contact(self):
        profile = [{"label": title, "url": url} for title, url in (
            ("Share on WhatsApp", "https://api.whatsapp.com/send?text=share"),
            ("WhatsApp", "https://wa.me/"),
            ("אתר הבית", "https://shop.example/"),
            ("קביעת תור", "https://calmark.io/p/123"),
            ("Instagram", "https://instagram.com/shop"))]
        signals = scout.digital_signals(profile, [], "Shop")
        self.assertEqual(signals["whatsapp"]["status"], "not_found_in_checked_links")
        self.assertEqual(signals["website"]["status"], "link_found_unverified")
        self.assertEqual(signals["booking"]["status"], "link_found_unverified")
        self.assertEqual(signals["social"]["status"], "link_found_unverified")
        self.assertEqual(signals["whatsapp_automation"]["status"], "unknown")
        profile.append({"label": "WhatsApp", "url": "https://wa.me/972501234567"})
        self.assertEqual(scout.digital_signals(profile, [], "Shop")["whatsapp"]["status"], "link_found_unverified")
        self.assertFalse(scout.whatsapp_contact("https://wa.me.fake.example/972501234567"))
        self.assertTrue(scout.whatsapp_contact("https://api.whatsapp.com/send?phone=972501234567"))

    def test_directory_audit_reads_only_expected_paths_and_name_search(self):
        listing = "https://www.d.co.il/h-c28275-e0-p0-l0-city4000/"
        profile = "https://www.d.co.il/80178161/28275/"
        calls = []
        def reader(url, **kwargs):
            calls.append(url)
            if url == listing:
                links = [{"label": "מוסך שבתאי", "url": profile},
                         {"label": "מרקוני 4, חיפה", "url": profile + "#page-block-map"}]
            elif url == profile:
                links = [{"label": "WhatsApp", "url": "https://wa.me/972501234567"}]
            else:
                links = [{"label": "מוסך שבתאי", "url": "https://b144.co.il/garage/123"}]
            return {"status": "read", "final_url": url, "links": links}
        result = scout.audit_directory("חיפה", "מוסכים", listing, reader=reader)
        self.assertEqual(calls, [listing, profile, scout.search_url("מוסך שבתאי חיפה")])
        entry = result["candidates"][0]
        self.assertEqual(entry["digital_presence"]["whatsapp"]["status"], "link_found_unverified")
        self.assertEqual(entry["digital_presence"]["website"]["status"], "not_found_in_checked_links")
        self.assertEqual(entry["website_status"], "UNCERTAIN")
        self.assertIsNone(entry["lead_score"])
        self.assertFalse(entry["demo_ready"])
        self.assertEqual(len(entry["sources_to_review"]), 2)

    def test_directory_audit_block_or_redirect_stops_before_search(self):
        listing = "https://www.d.co.il/h-c28275-e0-p0-l0-city4000/"
        profile = "https://www.d.co.il/80178161/28275/"
        for bad in ({"status": "possible_block", "final_url": profile},
                    {"status": "read", "final_url": "https://other.example/"}):
            calls = []
            def reader(url, **kwargs):
                calls.append(url)
                return ({"status": "read", "final_url": url, "links": [
                    {"label": "Shop", "url": profile},
                    {"label": "Main 1, Haifa", "url": profile + "#page-block-map"}]}
                    if url == listing else bad)
            result = scout.audit_directory("Haifa", "garage", listing, reader=reader)
            self.assertEqual(result["status"], "blocked_or_unavailable")
            self.assertEqual(result["candidates"], [])
            self.assertEqual(calls, [listing, profile])

    def test_directory_audit_incomplete_and_conflicting_evidence(self):
        listing = "https://www.d.co.il/h-c28275-e0-p0-l0-city4000/"
        profile = "https://www.d.co.il/80178161/28275/"
        for conflict in (False, True):
            def reader(url, **kwargs):
                links = ([{"label": "Shop", "url": profile},
                          {"label": "Main 1, Haifa", "url": profile + "#page-block-map"}]
                         if url == listing else
                         [{"label": "Shop - Main 1, Netanya - garage | Easy", "url": "https://easy.co.il/page/123"}]
                         if url != profile and conflict else [])
                return {"status": "read", "final_url": url, "links": links, "links_truncated": url == profile}
            result = scout.audit_directory("Haifa", "garage", listing, reader=reader)
            if conflict:
                self.assertEqual(result["candidates"], [])
                self.assertEqual(result["location_review"][0]["location"]["status"], "conflicting")
            else:
                self.assertEqual(result["candidates"][0]["digital_presence"]["website"]["status"], "unknown_incomplete_scan")

    def test_publisher_social_and_neighborhood_regressions(self):
        rows = [{"label": label, "url": url} for label, url in (
            ("אינסטגרם - לוגו", "https://www.instagram.com/dapey.zahav/"),
            ("אייקון פייסבוק", "https://www.facebook.com/d.co.il"),
            ("אייקון פייסבוק", "https://www.facebook.com/realshop"))]
        signals = scout.digital_signals(rows, [], "Shop")
        self.assertEqual([x["url"] for x in signals["social"]["evidence"]], ["https://www.facebook.com/realshop"])
        self.assertEqual(scout.city_hint("דרך יפו 154, בת גלים חיפה", "חיפה"), "match")
        self.assertEqual(scout.city_hint("מוצקין 11, טירת כרמל", "חיפה"), "other")
        self.assertEqual(scout.search_name("מוסך שפיק בחיפה", "חיפה"), "מוסך שפיק")

    def test_audit_selected_site_signals_and_limits(self):
        calls = []
        def reader(url, **kwargs):
            calls.append((url, kwargs))
            return {"status": "read", "final_url": "https://shop.example/", "inspection": {"title": "Shop", "viewport_width": 390},
                    "links": [{"label": "WhatsApp", "url": "https://wa.me/972501234567"}], "links_truncated": True}
        result = scout.audit_site("http://shop.example/", reader=reader, validate=lambda u: None)
        self.assertTrue(result["https"])
        self.assertFalse(result["ownership_verified"])
        self.assertTrue(calls[0][1]["inspect_site"])
        self.assertEqual(result["digital_presence"]["whatsapp"]["status"], "link_found_unverified")
        self.assertEqual(result["digital_presence"]["booking"]["status"], "unknown_incomplete_scan")
        self.assertEqual(result["digital_presence"]["whatsapp_automation"]["status"], "unknown")

    def test_audit_block_does_not_inspect_signals(self):
        result = scout.audit_site("https://shop.example/", validate=lambda u: None,
                                  reader=lambda *a, **k: {"status": "possible_block"})
        self.assertNotIn("page_checks", result)
        self.assertEqual(result["status"], "possible_block")

    @patch.object(scout.socket, "getaddrinfo")
    def test_public_site_rejects_private_dns(self, resolver):
        resolver.return_value = [(2, 1, 6, "", ("127.0.0.1", 443))]
        with self.assertRaises(ValueError):
            scout.public_site("https://not-public.example/")
        with self.assertRaises(ValueError):
            scout.public_site("https://d.co.il/1/2/")

    def test_score_requires_explicit_verified_facts(self):
        self.assertEqual(scout.reviewed_score({key: True for key in scout.SCORE_WEIGHTS}), 100)
        self.assertEqual(scout.reviewed_score({'active_listing': True, 'public_contact': 'yes'}), 15)
        with self.assertRaises(ValueError):
            scout.reviewed_score({'social_only': True})

    @patch.object(browser, 'resolve_browser', return_value='agent-browser')
    @patch.object(browser.subprocess, 'run')
    def test_extract_before_snapshot_truncation(self, run, resolve):
        snapshot = 'x' * 9000 + '\n- link "Website B" [ref=e9, url=https://example.com]\n'
        run.side_effect = [subprocess.CompletedProcess([], 0, t, '') for t in
                           ('opened', 'https://example.com', snapshot, 'closed')]
        result = browser.read_page('https://example.com', include_links=True)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['links'], [{'label': 'Website B', 'url': 'https://example.com'}])
        self.assertEqual(run.call_args_list[2].args[0][-3:], ['snapshot', '-i', '--urls'])


if __name__ == '__main__':
    unittest.main()
