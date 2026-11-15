#!/usr/bin/env python3
"""Outbound link rules for SunglassDealsDaily.

Scripts may read a merchant product URL as text. They must never request a
Commission Junction (or other network) click URL. A price check, when one is
added later, fetches the plain retailer URL stored on the product.
"""
import re
import urllib.parse

TRACKING_DOMAINS = (
    "anrdoezrs.net",
    "jdoqocy.com",
    "tkqlhce.com",
    "dpbolvw.net",
    "kqzyfj.com",
    "emjcd.com",
    "awin1.com",
    "click.linksynergy.com",
    "linksynergy.com",
)
# Retailers this site does not link, even as a plain URL.
BLOCKED_DOMAINS = (
    "amazon.com",
    "amazon.co.uk",
    "ebay.com",
    "walmart.com",
    "nordstromrack.com",
    "nordstrom.com",
    "sephora.com",
)
REDIRECT_PREFIXES = ("/go/", "/out/", "/redirect/", "/r/")
_CJ_CLICK = re.compile(r"/click-\d+-\d+")
_SID_OK = re.compile(r"^[a-z0-9_-]{1,64}$")


def host_of(url):
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower().rstrip(".")
    except Exception:
        return ""


def host_is(host, domain):
    host = (host or "").lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def is_tracking_host(host):
    return any(host_is(host, domain) for domain in TRACKING_DOMAINS)


def is_tracking_url(url):
    if not isinstance(url, str) or not url:
        return False
    if is_tracking_host(host_of(url)):
        return True
    low = url.lower()
    return any(domain in low for domain in TRACKING_DOMAINS)


def is_blocked_url(url):
    host = host_of(url)
    return any(host_is(host, domain) for domain in BLOCKED_DOMAINS)


def is_redirect_path(path):
    path = path or "/"
    if not path.startswith("/"):
        path = "/" + path
    for prefix in REDIRECT_PREFIXES:
        if path == prefix.rstrip("/") or path.startswith(prefix):
            return True
    return False


def _sid_part(value):
    part = re.sub(r"[^a-z0-9_-]+", "-", (value or "").lower())
    part = re.sub(r"-{2,}", "-", part).strip("-")
    return part


def make_sid(page_type, page_slug, placement, product=""):
    """{pagetype}-{slug}-{placement}. Charset [a-z0-9-_], at most 64 characters.

    A hub link can pass the product slug. That product slug is kept ahead of
    the page slug when the id has to be shortened. The placement is never the
    part that is cut.
    """
    typ = _sid_part(page_type) or "site"
    place = _sid_part(placement) or "link"
    extra = "" if typ == "deal" else _sid_part(product)
    slug = "-".join(bit for bit in (extra, _sid_part(page_slug)) if bit)
    sid = "-".join(bit for bit in (typ, slug, place) if bit)
    if len(sid) <= 64 and _SID_OK.match(sid):
        return sid
    budget = 64 - len(typ) - len(place) - 2
    cut = ""
    if slug and budget >= 1:
        cut = slug[:budget].rstrip("-")
        if len(slug) > budget and "-" in cut:
            cut = cut.rsplit("-", 1)[0]
        cut = cut.strip("-")
    sid = "-".join(bit for bit in (typ, cut, place) if bit)
    sid = sid[:64].strip("-")
    if not _SID_OK.match(sid):
        raise ValueError(f"sid failed the charset check: {sid!r}")
    return sid


def add_sid(url, sid):
    """Put sid first on a CJ click URL. Leave every other parameter byte-for-byte."""
    sid_q = urllib.parse.quote(sid, safe="-_")
    frag = ""
    if "#" in url:
        url, frag = url.split("#", 1)
        frag = "#" + frag
    if "?" not in url:
        return url + "?sid=" + sid_q + frag
    base, query = url.split("?", 1)
    parts = [part for part in query.split("&") if part and not part.startswith("sid=")]
    tail = ("&" + "&".join(parts)) if parts else ""
    return base + "?sid=" + sid_q + tail + frag


def wrap_cj(click_base, plain_url, sid):
    """String-only CJ deep link. Does not request the click URL."""
    if not click_base:
        return plain_url
    if not isinstance(click_base, str) or not click_base.startswith("https://"):
        raise ValueError("cj.click_base must be an https URL or null")
    if not is_tracking_url(click_base):
        raise ValueError("cj.click_base is set but is not a known network click host")
    parsed = urllib.parse.urlparse(click_base)
    if not _CJ_CLICK.search(parsed.path or ""):
        raise ValueError("cj.click_base is missing a /click-<pid>-<ad> path")
    if is_tracking_url(plain_url) or is_blocked_url(plain_url):
        raise ValueError("refusing to wrap a tracking or blocked target")
    base = add_sid(click_base, sid)
    path = urllib.parse.urlparse(plain_url)
    if (path.path or "") in ("", "/") and not path.query and not path.fragment:
        return base
    joiner = "&" if "?" in base else "?"
    return base + joiner + "url=" + urllib.parse.quote(plain_url, safe="")


def outbound(url, merchant, page_type, page_slug, placement, product=""):
    """Return (href, sid). Plain merchant URL until that merchant has a click_base."""
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError(f"outbound URL must be https: {url!r}")
    if is_blocked_url(url):
        raise ValueError(f"blocked merchant URL: {url}")
    if is_tracking_url(url):
        raise ValueError(f"product URL is already a tracking link: {url}")
    sid = make_sid(page_type, page_slug, placement, product)
    click = None
    if isinstance(merchant, dict):
        click = (merchant.get("cj") or {}).get("click_base") or None
    if click:
        return wrap_cj(click, url, sid), sid
    return url, sid


if __name__ == "__main__":
    sid = make_sid("deal", "ray-ban-wayfarer-rb2140", "cta")
    assert sid == "deal-ray-ban-wayfarer-rb2140-cta", sid
    long = make_sid("best", "polarized-sunglasses-under-200", "grid", "oakley-holbrook")
    assert len(long) <= 64 and long.endswith("-grid") and long.startswith("best-"), long
    assert "oakley-holbrook" in long
    plain = "https://www.oakley.com/en-us/product/W0OO9102"
    href, _sid = outbound(plain, {"cj": {"click_base": None}}, "deal", "oakley-holbrook", "cta")
    assert href == plain
    wrapped = wrap_cj("https://www.anrdoezrs.net/click-1-2", plain, "deal-oakley-holbrook-cta")
    assert wrapped.startswith("https://www.anrdoezrs.net/click-1-2?sid=deal-oakley-holbrook-cta&url=")
    assert is_tracking_url(wrapped)
    assert is_blocked_url("https://www.amazon.com/dp/test")
    print("links ok", sid)
