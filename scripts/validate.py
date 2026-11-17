#!/usr/bin/env python3
"""Check the built site. Does not request any URL."""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import links

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site")
DATA = json.load(open(os.path.join(ROOT, "data", "links.json"), encoding="utf-8"))
errors = []


def fail(msg):
    errors.append(msg)


known = set()
for product in DATA["products"]:
    for offer in product["offers"]:
        price = offer.get("price")
        if isinstance(price, (int, float)) and not isinstance(price, bool):
            known.add(f"{float(price):.2f}")

html_files = []
for dirpath, _, names in os.walk(OUT):
    for name in names:
        if name.endswith(".html"):
            html_files.append(os.path.join(dirpath, name))

if not html_files:
    fail("no html")

money_re = re.compile(r"\$(\d{1,4}\.\d{2})")
href_re = re.compile(r'href="([^"]+)"')
img_re = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"')
ld_re = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
sid_re = re.compile(r'data-sid="([^"]*)"')
h3_re = re.compile(r"<h3>(.*?)</h3>", re.S)

for path in html_files:
    text = open(path, encoding="utf-8").read()
    rel = os.path.relpath(path, OUT)
    for host in links.TRACKING_DOMAINS + links.BLOCKED_DOMAINS:
        if host in text.lower():
            fail(f"{rel}: contains {host}")
    for match in money_re.finditer(text):
        if match.group(1) not in known:
            fail(f"{rel}: dollar {match.group(1)} is not a stored price")
    for href in href_re.findall(text):
        if links.is_tracking_url(href) or links.is_blocked_url(href):
            fail(f"{rel}: bad href {href}")
    for src in img_re.findall(text):
        if links.is_tracking_url(src) or links.is_blocked_url(src):
            fail(f"{rel}: bad image {src}")
        if src.startswith("/media/products/"):
            if not os.path.isfile(os.path.join(OUT, src.lstrip("/"))):
                fail(f"{rel}: missing hosted image {src}")
        if href.startswith("http") and "sid=" in href:
            fail(f"{rel}: sid on a live URL before CJ approval {href}")
    for sid in sid_re.findall(text):
        if not re.fullmatch(r"[a-z0-9_-]{1,64}", sid):
            fail(f"{rel}: bad sid {sid}")
    for raw in ld_re.findall(text):
        try:
            node = json.loads(raw)
        except json.JSONDecodeError as exc:
            fail(f"{rel}: json-ld {exc}")
            continue
        blob = json.dumps(node)
        if "aggregateRating" in blob or "ratingValue" in blob or "reviewCount" in blob:
            fail(f"{rel}: rating schema")
        def walk(obj):
            if isinstance(obj, dict):
                if obj.get("@type") == "Offer" or (isinstance(obj.get("@type"), list) and "Offer" in obj["@type"]):
                    price = obj.get("price")
                    if price not in known:
                        fail(f"{rel}: offer price {price}")
                    if "availability" in obj and obj["availability"] not in (
                        "https://schema.org/OutOfStock",
                        "https://schema.org/InStock",
                    ):
                        fail(f"{rel}: bad availability")
                    if obj.get("availability") == "https://schema.org/InStock":
                        fail(f"{rel}: InStock was not verified")
                if obj.get("@type") == "FAQPage":
                    questions = [q.get("name") for q in obj.get("mainEntity") or []]
                    visible = [html.unescape(re.sub("<.*?>", "", h)) for h in h3_re.findall(text)]
                    if questions != visible:
                        fail(f"{rel}: FAQPage does not match visible questions {questions!r} vs {visible!r}")
                for value in obj.values():
                    walk(value)
            elif isinstance(obj, list):
                for value in obj:
                    walk(value)
        walk(node)

prefix = os.environ.get("PATH_PREFIX", "").rstrip("/")
expected_host = os.environ.get("SITE_URL", "https://sunglassdealsdaily.com").rstrip("/")
missing_links = []
for path in html_files:
    text = open(path, encoding="utf-8").read()
    rel = os.path.relpath(path, OUT)
    if "aministan.github.io" in text or "/sunglassdealsdaily/" in text:
        fail(f"{rel}: still points at the github.io project path")
    for href in href_re.findall(text):
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if prefix:
            if not href.startswith(prefix + "/") and href.rstrip("/") != prefix:
                continue
            rest = href[len(prefix):]
        else:
            if not href.startswith("/"):
                continue
            rest = href
        if href.endswith((".xml", ".txt", ".png", ".svg", ".json")):
            target = os.path.join(OUT, rest.lstrip("/"))
        else:
            target = os.path.join(OUT, rest.strip("/"), "index.html")
            if rest.strip("/") == "":
                target = os.path.join(OUT, "index.html")
        if not os.path.exists(target):
            missing_links.append(f"{rel} -> {href}")
if missing_links:
    fail("broken internal links:\n" + "\n".join(missing_links[:30]))

if os.path.exists(os.path.join(OUT, "CNAME")):
    fail("CNAME should not be written yet")

robots = open(os.path.join(OUT, "robots.txt"), encoding="utf-8").read()
if f"Sitemap: {expected_host}/sitemap.xml" not in robots:
    fail(f"robots sitemap is not {expected_host}/sitemap.xml")
home = open(os.path.join(OUT, "index.html"), encoding="utf-8").read()
if f'rel="canonical" href="{expected_host}/"' not in home:
    fail(f"homepage canonical is not {expected_host}/")
sitemap = open(os.path.join(OUT, "sitemap.xml"), encoding="utf-8").read()
if expected_host not in sitemap:
    fail("sitemap is not on the custom domain")
if sitemap.count("<loc>") < 40:
    fail("sitemap looks short")
if "404" in sitemap:
    fail("404 is in the sitemap")

if errors:
    print("\n".join(errors))
    raise SystemExit(f"{len(errors)} validation errors")
print(f"validate ok: {len(html_files)} html files, {len(known)} stored prices")
