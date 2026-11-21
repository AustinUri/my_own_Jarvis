"""Small, read-only lead scout. Browser transport is injected; no AI or outreach.

Bing results are discovery evidence, not proof of ownership or absence of a site.
Only fixed search URLs and recognized D.co.il listing/profile paths are opened.
External business links are recorded, not visited during discovery.
Explicitly selected sites can be inspected with --audit-site.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import ipaddress
import re
import subprocess
import socket
from urllib.parse import parse_qs, urlencode, urldefrag, urlsplit

from core.capabilities.browser_runtime import read_page
from core.capabilities.workflows import compose

# All search/provider policy lives here; change these without touching the browser.
DIRECTORIES = ("easy.co.il", "b144.co.il", "t.co.il", "openinghours.co.il", "zips.co.il",
               "revieweuro.com", "saparim.co.il", "autoyas.com", "garage1.co.il",
               "israelbusinessguide.com", "d.co.il", "mymusach.co.il", "caro.co.il",
               "index.webezier.com", "midrag.co.il")
BOOKING = ("calmark.io", "calmark.co.il", "lee.co.il", "booksy.com", "fresha.com", "b.me.app")
SOCIAL = ("facebook.com", "instagram.com", "tiktok.com", "wa.me", "whatsapp.com")
SCORE_WEIGHTS = {"no_official_site": 30, "active_listing": 15, "public_contact": 15,
                 "social_only": 15, "conversion_potential": 10, "verified_services": 10,
                 "clear_location": 5}


def host(url: str) -> str:
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
            return ""
        return (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def belongs(domain: str, choices: tuple[str, ...]) -> bool:
    return any(domain == item or domain.endswith("." + item) for item in choices)


def unwrap_bing(url: str) -> str:
    """Decode known Bing redirect formats locally; never fetch them."""
    original = url
    try:
        for _ in range(3):
            parsed = urlsplit(url)
            if not belongs(host(url), ("bing.com",)):
                break
            query = parse_qs(parsed.query)
            if parsed.path == "/ck/a":
                value = query.get("u", [""])[0]
                if not value.startswith("a1"):
                    return original
                value = value[2:]
                url = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True).decode("utf-8")
            elif parsed.path == "/alink/link":
                url = query.get("url", [""])[0]
            else:
                break
        return url if host(url) and not any(c.isspace() or ord(c) < 32 for c in url) else original
    except (ValueError, UnicodeError, binascii.Error):
        return original


def classify(url: str) -> str:
    domain = host(url)
    if not domain or belongs(domain, ("bing.com", "google.com", "google.co.il")):
        return "unknown"
    for kind, choices in (("directory", DIRECTORIES), ("booking", BOOKING), ("social", SOCIAL)):
        if belongs(domain, choices):
            return kind
    return "possible_official_site"  # Never assert that an unfamiliar domain belongs to the business.


def search_url(query: str) -> str:
    return "https://www.bing.com/search?" + urlencode({"q": query})


def identity(name: str) -> str:
    # Preserve Hebrew; strip only punctuation, whitespace and case.
    return re.sub(r"[^\w]+", " ", name.casefold()).strip()


def candidates(links: list[dict]) -> list[dict]:
    """Local result cards expose Website/Directions labels, including no-site listings."""
    found = {}
    for link in links:
        label = link["label"].replace('\\"', '"')
        prefix, _, name = label.partition(" ")
        if prefix not in ("Website", "Directions") or not name.strip():
            continue
        key = identity(name)
        if not key:
            continue
        entry = found.setdefault(key, {"business_name": name, "listed_links": []})
        if prefix == "Website":
            url = unwrap_bing(link["url"])
            item = {"url": url, "kind": classify(url)}
            if item not in entry["listed_links"]:
                entry["listed_links"].append(item)
    # Prefer no listed dedicated site, but never confuse missing evidence with no site.
    return sorted(found.values(), key=lambda e: any(x["kind"] == "possible_official_site" for x in e["listed_links"]))


def easy_listing(link: dict) -> tuple[str, str, str] | None:
    """Extract name and address from a structured Easy result title only."""
    url = urldefrag(unwrap_bing(link["url"]))[0]
    if not belongs(host(url), ("easy.co.il",)) or not re.fullmatch(r"/page/\d+/?", urlsplit(url).path):
        return None
    title, separator, brand = link["label"].partition(" | ")
    if not separator or not identity(brand).startswith(("איזי", "easy")):
        return None
    parts = title.rsplit(" - ", 2)
    if len(parts) != 3 or len(identity(parts[0])) < 2:
        return None
    return parts[0].strip(), parts[1].strip(), url


def city_hint(address: str, city: str) -> str:
    """Address tail hint; a neighborhood before a city is allowed, not proof."""
    tail = identity(address.rsplit(",", 1)[-1])
    target = identity(city)
    if target and (tail == target or ("," in address and tail.endswith(" " + target))):
        return "match"
    return "other" if "," in address else "unknown"


def search_name(name: str, city: str) -> str:
    """Remove a directory's appended city, without changing the displayed name."""
    return re.sub(r"\s+(?:ב)?" + re.escape(city) + r"$", "", name.strip(), flags=re.I).strip() or name


def location_evidence(links: list[dict], name: str, city: str) -> dict:
    """A city hint, not verified geography. Conflicting hints require review."""
    key = identity(name.split("|")[0])
    hints = []
    for link in links:
        listing = easy_listing(link)
        if not listing:
            continue
        listed_name, address, url = listing
        if f" {key} " not in f" {identity(listed_name)} ":
            continue
        # Easy's structured title commonly ends the address with ', CITY'.
        # Without a comma, accept only an exact city match; otherwise unknown.
        state = city_hint(address, city)
        hint = {"address_hint": address, "url": url, "match": state}
        if hint not in hints:
            hints.append(hint)
    states = {h["match"] for h in hints}
    status = ("conflicting" if {"match", "other"} <= states else
              "city_hint_match" if "match" in states else
              "other_city_hint" if "other" in states else "unknown")
    return {"status": status, "evidence": hints[:5]}


def directory_candidates(links: list[dict], city: str) -> list[dict]:
    """Fallback for individual Easy listings with a matching city hint."""
    found = {}
    for link in links:
        listing = easy_listing(link)
        if not listing:
            continue
        name, address, url = listing
        if city_hint(address, city) != "match":
            continue
        found.setdefault(identity(name), {"business_name": name, "listed_links": [],
                                          "discovery_sources": [{"title": link["label"][:180],
                                                                 "url": url, "kind": "directory"}]})
    return list(found.values())


def evidence(links: list[dict], name: str, *, limit: int = 6) -> list[dict]:
    """Return only name-matching result labels, not full browser trees."""
    key = identity(name.split("|")[0])
    if len(key) < 3:
        return []
    result = []
    seen = set()
    for link in links:
        if key not in identity(link["label"]):
            continue
        url = urldefrag(unwrap_bing(link["url"]))[0]
        domain = host(url)
        if not domain or classify(url) == "unknown" or url in seen:
            continue
        seen.add(url)
        result.append({"title": link["label"][:180], "url": url, "kind": classify(url)})
    # Put different hosts first, without claiming they are independent sources.
    distinct, repeats, hosts = [], [], set()
    for item in result:
        domain = host(item["url"]).removeprefix("www.")
        (repeats if domain in hosts else distinct).append(item)
        hosts.add(domain)
    return (distinct + repeats)[:limit]



def directory_path(url: str, *, listing: bool = False) -> str | None:
    """Only known public D.co.il paths; strip tracking, fragments and queries."""
    try:
        parsed = urlsplit(url)
        if host(url) not in ("d.co.il", "www.d.co.il") or parsed.port is not None:
            return None
        pattern = r"/h-c\d+-e\d+-p\d+-l\d+-city\d+/" if listing else r"/\d+/\d+/"
        if not re.fullmatch(pattern, parsed.path):
            return None
        return "https://www.d.co.il" + parsed.path
    except ValueError:
        return None


def directory_entries(links: list[dict], city: str) -> list[dict]:
    """Group name and map links by profile URL, not by display order."""
    entries = {}
    for link in links:
        url = directory_path(link["url"])
        if not url:
            continue
        fragment = urlsplit(link["url"]).fragment
        label = link["label"].replace('\\"', '"').strip().strip('"')
        entry = entries.setdefault(url, {"business_name": "", "profile_url": url,
                                         "address_hints": []})
        if fragment == "page-block-map" and label:
            if label not in entry["address_hints"]:
                entry["address_hints"].append(label)
        elif not fragment and label and not entry["business_name"]:
            if not re.match(r"^(?:דירוג|Read more|קרא עוד|לפרטים|פרטים נוספים|נווט|מפה|חוות דעת|ביקורות|Website|Directions)(?:\s|$)", label, re.I):
                entry["business_name"] = label
    result = []
    for entry in entries.values():
        if not entry["business_name"]:
            continue
        hints = [{"address_hint": a, "url": entry["profile_url"], "match": city_hint(a, city)}
                 for a in entry["address_hints"]]
        states = {h["match"] for h in hints}
        status = ("conflicting" if {"match", "other"} <= states else
                  "city_hint_match" if "match" in states else
                  "other_city_hint" if "other" in states else "unknown")
        entry["location"] = {"status": status, "evidence": hints}
        result.append(entry)
    return result


def whatsapp_contact(url: str) -> bool:
    """A phone-directed link, not a share button or generic WhatsApp homepage."""
    parsed = urlsplit(url)
    domain = host(url)
    if domain in ("wa.me", "www.wa.me"):
        return bool(re.fullmatch(r"/\+?[0-9]{7,15}/?", parsed.path))
    if domain in ("api.whatsapp.com", "web.whatsapp.com", "whatsapp.com", "www.whatsapp.com"):
        phone = parse_qs(parsed.query).get("phone", [""])[0]
        return parsed.path.rstrip("/") == "/send" and bool(re.fullmatch(r"\+?[0-9]{7,15}", phone))
    return False


def publisher_social(url: str) -> bool:
    """Known publisher accounts and non-account social navigation links."""
    domain = host(url)
    path = urlsplit(url).path.strip("/").casefold()
    return ((belongs(domain, ("facebook.com",)) and path in ("d.co.il", "sharer", "sharer/sharer.php"))
            or (belongs(domain, ("instagram.com",)) and path == "dapey.zahav"))


def digital_signals(profile_links: list[dict], search_links: list[dict], name: str, *, origin_label: str = "directory_profile") -> dict:
    """Evidence of public links only. No claim of ownership, absence or automation."""
    signals = {key: [] for key in ("website", "whatsapp", "booking", "social")}
    items = []
    for source in evidence(search_links, name, limit=150):
        items.append((source["title"], source["url"], "name_search"))
    for link in profile_links:
        label = link["label"]
        # Do not collect generic footer/social/share/advertising links.
        if re.search(r"(?:אתר(?: הבית| העסק| האינטרנט)?|website|whatsapp|וואטסאפ|ווטסאפ|ווצאפ|ווטסאפ|קביעת תור|הזמנת תור|booking|facebook|instagram|פייסבוק|אינסטגרם)", label, re.I) and not re.search(r"share|שיתוף|שתף|פרסומ|advertis", label, re.I):
            if origin_label == "directory_profile" and re.fullmatch(r"(?:אינסטגרם|פייסבוק|instagram|facebook)\s*[-–]?\s*(?:לוגו|logo)", label.strip(), re.I):
                continue
            items.append((label, link["url"], origin_label))
    seen = set()
    for label, raw, origin in items:
        url = urldefrag(unwrap_bing(raw))[0]
        kind = classify(url)
        if not host(url) or publisher_social(url):
            continue
        if whatsapp_contact(url):
            key = "whatsapp"
        elif belongs(host(url), ("whatsapp.com", "wa.me")):
            continue
        elif kind == "booking":
            key = "booking"
        elif kind == "social":
            key = "social"
        elif kind == "possible_official_site" and (origin == "name_search" or re.search(r"אתר|website", label, re.I)):
            key = "website"
        else:
            continue
        if (key, url) not in seen and len(signals[key]) < 5:
            seen.add((key, url))
            signals[key].append({"url": url, "label": label[:180], "source": origin})
    return {key: {"status": "link_found_unverified" if values else "not_found_in_checked_links",
                  "evidence": values} for key, values in signals.items()} | {
        "whatsapp_automation": {"status": "unknown", "evidence": []}}


def audit_directory(city: str, category: str, directory_url: str, *, limit: int = 2,
                    headed: bool = False, reader=read_page) -> dict:
    """Bounded directory-first discovery; read only public listing and profile pages.

    Search-result snippets and directory labels are hints, not verified facts.
    """
    listing_url = directory_path(directory_url, listing=True)
    if not listing_url or not city.strip() or not category.strip() or not 1 <= limit <= 5:
        raise ValueError("Expected a D.co.il city/category listing URL and limit 1–5")
    city, category = city.strip()[:100], category.strip()[:100]
    output = {"city_requested": city, "category_requested": category,
              "mode": "directory_audit", "status": "review_required", "searches": [],
              "candidates": [], "location_review": [], "unique_directory_entries": 0,
              "workflow": "website-factory", "stage": "discovery",
              "skills_planned": list(compose("website-factory")[0].skills)}

    def read(url: str, *, directory: bool = False, listing: bool = False) -> dict:
        page = reader(url, headed=headed, include_links=True)
        status = page["status"]
        if directory and status == "read" and directory_path(page.get("final_url", ""), listing=listing) != url:
            status = "unexpected_redirect"
        output["searches"].append({"url": url, "status": status,
                                   "links_truncated": page.get("links_truncated", False)})
        if page.get("cleanup_error"):
            raise RuntimeError("Browser cleanup failed; stopping discovery")
        return dict(page, status=status)

    page = read(listing_url, directory=True, listing=True)
    if page["status"] != "read":
        output["status"] = "blocked_or_unavailable"
        return output
    entries = directory_entries(page.get("links", []), city)
    output["unique_directory_entries"] = len(entries)
    output["location_review"] = [e for e in entries if e["location"]["status"] != "city_hint_match"][:5]
    for entry in [e for e in entries if e["location"]["status"] == "city_hint_match"][:limit]:
        profile = read(entry["profile_url"], directory=True)
        if profile["status"] != "read":
            output["status"] = "blocked_or_unavailable"
            break
        name = search_name(entry["business_name"], city)
        results = read(search_url(f'{name} {city}'))
        if results["status"] != "read":
            output["status"] = "blocked_or_unavailable"
            break
        links = results.get("links", [])
        location = location_evidence(links, name, city)
        if location["status"] in ("other_city_hint", "conflicting"):
            entry["location"]["status"] = "conflicting"
            entry["location"]["evidence"].extend(location["evidence"])
            output["location_review"].append(entry)
            continue
        signals = digital_signals(profile.get("links", []), links, name)
        partial = bool(profile.get("links_truncated") or results.get("links_truncated"))
        if partial:
            for signal in signals.values():
                if signal["status"] == "not_found_in_checked_links":
                    signal["status"] = "unknown_incomplete_scan"
        entry.update({"digital_presence": signals, "website_status": "UNCERTAIN",
                      "possible_official_site": bool(signals["website"]["evidence"]),
                      "lead_score": None, "demo_ready": False,
                      "sources_to_review": [{"title": entry["business_name"], "url": entry["profile_url"], "kind": "directory"}] + evidence(links, name, limit=6),
                      "verification_notes": "Directory profile and name search checked. Links are unverified; absence, ownership, activity and independent evidence require review."})
        output["candidates"].append(entry)
    if not output["candidates"] and output["status"] == "review_required":
        output["status"] = "location_review_required" if output["location_review"] else "no_candidates_extracted"
    return output

def public_site(url: str) -> None:
    """Reject obvious private targets before navigation. Not a network sandbox."""
    domain = host(url)
    parsed = urlsplit(url)
    if (not domain or parsed.port not in (None, 80, 443) or "." not in domain
            or classify(url) != "possible_official_site"):
        raise ValueError("Select an explicit public business homepage, not a directory or private address")
    addresses = socket.getaddrinfo(domain, parsed.port or (443 if parsed.scheme == "https" else 80),
                                   type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Non-public website address rejected")


def audit_site(url: str, *, headed: bool = False, reader=read_page, validate=public_site) -> dict:
    """Read one user-selected site. No forms, outreach, or compliance claims."""
    validate(url)
    page = reader(url, headed=headed, include_links=True, inspect_site=True)
    if page.get("cleanup_error"):
        raise RuntimeError("Browser cleanup failed; stopping audit")
    final = page.get("final_url", "")
    result = {"requested_url": url, "final_url": final, "status": page["status"],
              "ownership_verified": False, "inspection_scope": "one_mobile_viewport_homepage"}
    if page["status"] != "read":
        return result
    # A redirect is already navigated by the browser. Do not use private/network-shared
    # destinations as evidence, or silently attribute a different host to the business.
    validate(final)
    result["same_host"] = host(url).removeprefix("www.") == host(final).removeprefix("www.")
    result["https"] = urlsplit(final).scheme == "https"
    result["page_checks"] = page.get("inspection")
    result["inspection_error"] = page.get("inspection_error")
    result["digital_presence"] = digital_signals(page.get("links", []), [], "", origin_label="website")
    # A site builder credit or an internal page is not another business website.
    result["digital_presence"]["website"] = {
        "status": "homepage_reached_identity_unverified",
        "evidence": [{"url": final, "label": "Selected homepage", "source": "website"}],
    }
    if page.get("links_truncated"):
        for signal in result["digital_presence"].values():
            if signal["status"] == "not_found_in_checked_links":
                signal["status"] = "unknown_incomplete_scan"
    result["links_truncated"] = page.get("links_truncated", False)
    result["limitations"] = ["Homepage only; links and identity not verified", "No speed benchmark, visual judgment, accessibility compliance or automation verification"]
    return result


def reviewed_score(facts: dict) -> int:
    """Site Scout exact weights, only for explicitly verified facts supplied by a reviewer."""
    if facts.get("social_only") is True and facts.get("no_official_site") is not True:
        raise ValueError("social_only requires verified no_official_site")
    return sum(weight for key, weight in SCORE_WEIGHTS.items() if facts.get(key) is True)


def discover(city: str, category: str, *, limit: int = 2, headed: bool = False,
             reader=read_page) -> dict:
    if not 1 <= limit <= 5 or not city.strip() or not category.strip():
        raise ValueError("Provide city, category and limit 1–5")
    city, category = city.strip()[:100], category.strip()[:100]
    searches = []

    def search(query: str) -> dict:
        url = search_url(query)
        page = reader(url, headed=headed, include_links=True)
        searches.append({"url": url, "status": page["status"],
                         "links_truncated": page.get("links_truncated", False)})
        if page.get("cleanup_error"):
            raise RuntimeError("Browser cleanup failed; stopping discovery")
        return page

    first = search(f"{category} {city}")
    output = {"city_requested": city, "category_requested": category, "searches": searches,
              "status": "review_required", "candidates": [], "location_review": [],
              "workflow": "website-factory", "stage": "discovery",
              "skills_planned": list(compose("website-factory")[0].skills)}
    if first["status"] != "read":
        output["status"] = "blocked_or_unavailable"
        return output
    entries = candidates(first.get("links", []))
    # Some result layouts do not include local Website/Directions cards.
    # Try individual directory entries already returned, then one targeted search.
    if not entries:
        entries = directory_candidates(first.get("links", []), city)
    if not entries:
        fallback = search(f"site:easy.co.il/page/ {category} {city}")
        if fallback["status"] != "read":
            output["status"] = "blocked_or_unavailable"
            return output
        entries = directory_candidates(fallback.get("links", []), city)
    for entry in entries[:limit + 2]:
        if len(output["candidates"]) >= limit:
            break
        name = entry["business_name"]
        # A narrower name search collects potential independent source URLs.
        # They are NOT independent verified evidence until someone opens them.
        page = search(f'{name.split("|")[0].strip()} {city}')
        if page["status"] != "read":
            output["status"] = "blocked_or_unavailable"
            break
        location = location_evidence(first.get("links", []) + page.get("links", []) +
                                     [{"label": x["title"], "url": x["url"]}
                                      for x in entry.get("discovery_sources", [])], name, city)
        entry["location"] = location
        # Inspect all returned matching links for risk flags before limiting output.
        all_sources = evidence(page.get("links", []), name, limit=150)
        possible = any(x["kind"] == "possible_official_site" for x in entry["listed_links"] + all_sources)
        sources = list(entry.get("discovery_sources", []))
        seen = {x["url"] for x in sources}
        for source in all_sources:
            if source["url"] not in seen:
                sources.append(source)
                seen.add(source["url"])
        entry.update({"sources_to_review": sources[:6],
                      "website_status": "UNCERTAIN", "possible_official_site": possible,
                      "lead_score": None, "demo_ready": False,
                      "verification_notes": "Search results only. Confirm location, activity, contact and website ownership using two independent sources."})
        if location["status"] == "city_hint_match":
            output["candidates"].append(entry)
        else:
            output["location_review"].append(entry)
    if not output["candidates"] and output["status"] == "review_required":
        output["status"] = "location_review_required" if output["location_review"] else "no_candidates_extracted"
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("city")
    parser.add_argument("category")
    parser.add_argument("--limit", type=int, default=2, choices=range(1, 6))
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--directory-url", help="Public D.co.il city/category listing for a digital presence audit")
    parser.add_argument("--audit-site", action="append", default=[], help="Explicit public homepage to inspect; repeat up to three times, separate from directory discovery")
    parser.add_argument("--analyze", action="store_true", help="Rank measured homepage findings using the loaded local model")
    parser.add_argument("--model", choices=("qwen", "gemma"), default="qwen")
    args = parser.parse_args()
    if args.analyze and not args.audit_site:
        parser.error("--analyze requires --audit-site")
    try:
        if args.audit_site:
            if args.directory_url or len(args.audit_site) > 3:
                raise ValueError("Select up to three sites; do not combine with --directory-url")
            audits = []
            for url in args.audit_site:
                try:
                    audit = audit_site(url, headed=args.headed)
                except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                    audit = {"requested_url": url, "status": "error", "error": str(exc)[:300]}
                audits.append(audit)
                if audit["status"] != "read":
                    break
            result = {"mode": "website_audit", "city_requested": args.city, "category_requested": args.category,
                      "status": "review_required" if len(audits) == len(args.audit_site) and all(a["status"] == "read" for a in audits) else "audit_incomplete",
                      "audits": audits}
        else:
            result = (audit_directory(args.city, args.category, args.directory_url, limit=args.limit, headed=args.headed)
                  if args.directory_url else discover(args.city, args.category, limit=args.limit, headed=args.headed))
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "error", "error": str(exc)[:500]}, ensure_ascii=False))
        return 1
    analysis_ok = True
    if args.analyze:
        from core.capabilities.opportunity_analysis import analyze
        for audit in result["audits"]:
            audit["opportunity_analysis"] = analyze(audit, model_kind=args.model)
            analysis_ok &= audit["opportunity_analysis"]["status"] in ("ranked", "ranked_rules", "no_measured_findings")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "review_required" and analysis_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
