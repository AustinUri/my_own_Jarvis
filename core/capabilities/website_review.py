"""Review a local Website Factory production build in an isolated Chromium session."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import threading
import uuid

from core.capabilities.browser_runtime import SITE_CHECKS, parse_inspection, resolve_browser
from core.capabilities.verified_facts import BusinessFacts, strict_json


class QuietFiles(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


DETAILS = """(async () => {
  await Promise.all(Array.from(document.images, image => image.decode()));
  await document.fonts.ready;
  const metric = (type) => new Promise(resolve => {
    if (!PerformanceObserver.supportedEntryTypes.includes(type)) return resolve(null);
    const values = [];
    const observer = new PerformanceObserver(list => values.push(...list.getEntries()));
    observer.observe({type, buffered:true});
    setTimeout(() => {
      values.push(...observer.takeRecords()); observer.disconnect();
      resolve(type === 'layout-shift'
        ? values.reduce((n,v) => n + (v.hadRecentInput ? 0 : v.value), 0)
        : values.length ? Math.round(values[values.length-1].startTime) : null);
    }, 300);
  });
  const [lcpMs,cls] = await Promise.all([metric('largest-contentful-paint'),metric('layout-shift')]);
  const links = Array.from(document.querySelectorAll('a[href]'));
  const entries = performance.getEntriesByType('resource');
  const nav = performance.getEntriesByType('navigation')[0];
  const ids = Array.from(document.querySelectorAll('[id]'), e=>e.id);
  return JSON.stringify({
    dir:document.documentElement.dir, main:document.querySelectorAll('main').length,
    text:document.body.innerText, phones:links.filter(a=>a.protocol==='tel:').map(a=>a.getAttribute('href')),
    whatsapp:links.filter(a=>a.hostname==='wa.me').map(a=>a.href),
    skip:links[0]?.getAttribute('href'), duplicateIds:ids.length!==new Set(ids).size,
    missingAnchor:links.some(a=>a.hash && !document.getElementById(decodeURIComponent(a.hash.slice(1)))),
    unnamedLinks:links.filter(a=>!((a.textContent||'').trim()||a.getAttribute('aria-label'))).length,
    blockedImages:Array.from(document.images).some(img=>!img.complete||!img.naturalWidth),
    externalResources:entries.filter(e=>new URL(e.name).origin!==location.origin).length,
    schema:JSON.parse(document.querySelector('script[type="application/ld+json"]').textContent),
    robots:document.querySelector('meta[name="robots"]')?.content,
    fcpMs:Math.round(performance.getEntriesByName('first-contentful-paint')[0]?.startTime)||null,
    loadMs:Math.round(nav.loadEventEnd), lcpMs, cls,
    transferredBytes:entries.reduce((a,e)=>a+e.transferSize,nav.transferSize),
    browser:navigator.userAgent
  });
})()"""


def review(dist: Path, evidence: Path, out: Path, executable=None):
    data = BusinessFacts.parse(strict_json(evidence.read_text(encoding='utf8'))).render_data()
    dist = dist.resolve(strict=True)
    if not (dist / 'index.html').is_file():
        raise ValueError('Select the built dist directory')
    if dist == out.resolve() or dist in out.resolve().parents:
        raise ValueError('Keep review artifacts outside the public site')
    out.mkdir(parents=True, exist_ok=False)
    cli = resolve_browser()
    env = {k: v for k, v in os.environ.items() if not k.startswith('AGENT_BROWSER_')}
    base = [cli, '--session', 'website-review-' + uuid.uuid4().hex[:10], '--allowed-domains', '127.0.0.1']
    if executable:
        base += ['--executable-path', str(executable)]

    def run(*args):
        proc = subprocess.run(base + list(args), env=env, capture_output=True, text=True,
                              encoding='utf8', errors='replace', timeout=60)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
        return proc.stdout.strip()

    report = {'conditions': 'Local Chromium over loopback, unthrottled. Each viewport is one lab navigation.',
              'dist_bytes': sum(p.stat().st_size for p in dist.rglob('*') if p.is_file()), 'viewports': {}}
    with ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietFiles, directory=str(dist))) as server:
        listener = threading.Thread(target=server.serve_forever, daemon=True)
        listener.start()
        try:
            origin = f'http://127.0.0.1:{server.server_port}'
            for label, width, height in [('desktop', 1440, 900), ('mobile', 390, 844), ('narrow', 320, 720)]:
                run('set', 'viewport', str(width), str(height))
                run('open', origin + '/?view=' + label)
                run('wait', 'h1')
                dom = parse_inspection(run('eval', SITE_CHECKS))
                details = json.loads(run('eval', DETAILS))
                if isinstance(details, str):
                    details = json.loads(details)
                visible = details.pop('text')
                schema = details.pop('schema')
                checks = {
                    'responsive': dom['viewport_width'] == width and not dom['horizontal_overflow_hint'],
                    'seo': data['name'] in dom['title'] and dom['meta_description'] and dom['viewport_meta'],
                    'structure': dom['h1_count'] == details['main'] == 1 and not details['duplicateIds'],
                    'accessibility_basics': not any((details['unnamedLinks'], details['missingAnchor'],
                                                     dom['images_missing_alt'], details['blockedImages'])),
                    'language': dom['language'] == data['language'] and
                                details['dir'] == ('rtl' if data['language'] == 'he' else 'ltr'),
                    'visible_services': all(service in visible for service in data['services']),
                    'facts': data['name'] in visible and data['city'] in visible and schema['name'] == data['name']
                             and schema.get('telephone') == data.get('phone'),
                    'contact_targets': set(details['phones']) == ({'tel:' + data['phone']} if 'phone' in data else set())
                                       and set(details['whatsapp']) == ({'https://wa.me/' + data['whatsapp'][1:]}
                                                                       if 'whatsapp' in data else set()),
                    'private_local_build': 'noindex' in details['robots'] and not details['externalResources'],
                }
                run('press', 'Tab')
                focus = run('eval', "document.activeElement.getAttribute('href')")
                checks['keyboard_skip'] = bool(details['skip'] and json.loads(focus) == details['skip'])
                run('press', 'Enter')
                checks['skip_navigates'] = json.loads(run('eval', 'location.hash')) == details['skip']
                run('eval', "document.activeElement.blur(); window.scrollTo({top:0,behavior:'instant'})")
                run('screenshot', str(out / (label + '.png')), '--full')
                report['viewports'][label] = {**dom, **details, 'checks': checks}
        finally:
            server.shutdown()
            run('close')
    report['passed'] = all(all(v['checks'].values()) for v in report['viewports'].values())
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    return report['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('dist', 'facts', 'out'):
        parser.add_argument('--' + option, type=Path, required=True)
    parser.add_argument('--browser', type=Path, help='Installed Chromium executable')
    args = parser.parse_args()
    raise SystemExit(0 if review(args.dist, args.facts, args.out.resolve(), args.browser) else 1)
