#!/usr/bin/env python3
"""Render data/links.json into site/.

Does not request any URL. Outbound hrefs come only from data/links.json.
A merchant CJ click_base, when one is filled in later, is wrapped in text.
Until then every button is the merchant's own https URL with no tracking query.
"""
import datetime
import html
import json
import os
import re
import struct
import sys
import urllib.parse
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import links

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site")
DATA = json.load(open(os.path.join(ROOT, "data", "links.json"), encoding="utf-8"))
BASE = os.environ.get("SITE_URL", "https://sunglassdealsdaily.com").rstrip("/")
_parts = urllib.parse.urlsplit(BASE)
BASE = urllib.parse.urlunsplit((_parts.scheme, _parts.netloc.lower(), _parts.path.rstrip("/"), "", ""))
PREFIX = os.environ.get("PATH_PREFIX", "").rstrip("/")
NAME = DATA["site_name"]
OWNER = DATA["owner"]
UPDATED = datetime.date.fromisoformat(DATA["updated"])
e = html.escape
PRODUCTS = DATA["products"]
BY_ID = {p["id"]: p for p in PRODUCTS}
MERCHANTS = DATA["merchants"]
GUIDES = DATA["guides"]


def die(msg):
    raise SystemExit(msg)


def money(value):
    return f"${float(value):,.2f}"


def priced(offer):
    price = offer.get("price")
    return isinstance(price, (int, float)) and not isinstance(price, bool) and price > 0


def prices_of(product):
    return [o for o in product["offers"] if priced(o)]


def lead(product):
    rows = prices_of(product)
    if not rows:
        return product["offers"][0]
    return min(rows, key=lambda o: float(o["price"]))


def merchant(product):
    mid = product["merchant"]
    if mid not in MERCHANTS:
        die(f"{product['id']}: unknown merchant {mid}")
    return MERCHANTS[mid]


def brand_slug(brand):
    return re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")


def display(product):
    return f"{product['brand']} {product['name']}"


def href_out(product, offer, page_type, page_slug, placement):
    url, sid = links.outbound(
        offer["url"], merchant(product), page_type, page_slug, placement, product["id"]
    )
    return url, sid


def ext_a(product, offer, inner, page_type, page_slug, placement, cls=""):
    url, sid = href_out(product, offer, page_type, page_slug, placement)
    klass = f' class="{cls}"' if cls else ""
    rel = "nofollow noopener"
    click = (merchant(product).get("cj") or {}).get("click_base")
    if click:
        rel = "nofollow sponsored noopener"
    return (
        f'<a{klass} rel="{rel}" target="_blank" data-sid="{e(sid)}" href="{e(url)}">{inner}</a>'
    )


def buy_label(product, offer):
    name = merchant(product)["name"]
    note = (offer.get("availability_note") or "").lower()
    if "unavailable" in note:
        return f"See {e(name)} (unavailable online)"
    if priced(offer):
        return f"Buy at {e(name)}"
    return f"Check today's price at {e(name)}"


def btn(product, offer, page_type, page_slug, placement):
    return ext_a(
        product, offer, buy_label(product, offer), page_type, page_slug, placement, cls="btn"
    )


CSS = """
*{box-sizing:border-box}
body{margin:0;font:16px/1.5 "Iowan Old Style",Palatino,"Palatino Linotype",Georgia,serif;color:#1c1915;background:#f4f1ea}
a{color:#0f4c5c}
header{background:#14181f;color:#f4f1ea;padding:14px 16px}
header a{color:#f4f1ea;text-decoration:none}
.logo{font-weight:800;font-size:20px;letter-spacing:-.4px}
.logo span{color:#e8a317}
nav{display:flex;gap:14px;flex-wrap:wrap;margin-top:6px;font-family:system-ui,sans-serif;font-size:14px}
main{max-width:1080px;margin:0 auto;padding:16px}
h1{font-size:28px;line-height:1.15;margin:8px 0}
.sub{color:#5c564c;margin:0 0 14px}
.lead-offer{background:#fff;border:1px solid #e4dccb;border-radius:14px;padding:14px;margin:0 0 12px;position:sticky;top:0;z-index:5;box-shadow:0 8px 24px rgba(20,24,31,.08)}
.lead-offer .btn{margin-top:8px}
.price{font-size:28px;font-weight:800;font-family:system-ui,sans-serif}
.price-missing{font-size:22px}
.meta{color:#6d675c;font-size:13px;font-family:system-ui,sans-serif}
.btn{display:inline-block;background:#14181f;color:#fff;text-decoration:none;font-family:system-ui,sans-serif;font-weight:700;border-radius:10px;padding:12px 16px}
.btn:hover{background:#0f4c5c}
.shot{margin:8px 0 16px;background:#fff;border:1px solid #e4dccb;border-radius:14px;padding:12px}
.shot img,.shot svg{display:block;width:min(420px,100%);height:auto;margin:0 auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.card{background:#fff;border:1px solid #e4dccb;border-radius:14px;padding:12px;display:flex;flex-direction:column;font-family:system-ui,sans-serif}
.card .nm{font-weight:700;margin:6px 0 2px}
.card .btn{margin-top:auto;text-align:center}
.card img,.card svg{width:100%;height:140px;object-fit:contain}
.box{background:#fff;border:1px solid #e4dccb;border-radius:14px;padding:14px 16px;margin:16px 0}
table{width:100%;border-collapse:collapse;background:#fff}
th,td{text-align:left;padding:8px;border-bottom:1px solid #eee;vertical-align:top;font-family:system-ui,sans-serif;font-size:14px}
.chips a{display:inline-block;margin:4px;padding:6px 10px;border-radius:999px;background:#fff;border:1px solid #e4dccb;text-decoration:none;font-family:system-ui,sans-serif;font-size:14px}
.crumbs{font-size:13px;color:#6d675c;font-family:system-ui,sans-serif}
.crumbs a{text-decoration:none}
.also{font-family:system-ui,sans-serif;font-size:14px;margin:8px 0}
footer{max-width:1080px;margin:0 auto;padding:8px 16px 28px;color:#5c564c;font-size:13px;font-family:system-ui,sans-serif}
.note{background:#fff8e8;border:1px solid #ead7a1;border-radius:12px;padding:10px 12px}
@media(max-width:640px){
  h1{font-size:22px}
  nav{flex-wrap:nowrap;overflow-x:auto}
  .btn{display:block;text-align:center}
  table,thead,tbody,tr,td{display:block}
  thead{display:none}
  td{border:0;padding:4px 8px}
  tr{border-bottom:1px solid #eee;padding:8px 0}
}
"""


def write_png(path):
    width, height = 1200, 630
    amber = bytes((232, 163, 23))
    ink = bytes((20, 24, 31))

    def row(y):
        color = amber if 250 <= y < 270 else ink
        return b"\x00" + color * width

    raw = b"".join(row(y) for y in range(height))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def shape_svg(shape):
    common = 'viewBox="0 0 320 140" role="img" aria-label="Frame shape"'
    if shape == "teardrop":
        body = '<path d="M70 70c0-36 28-52 48-52 8 22 18 52 18 52s10-30 18-52c20 0 48 16 48 52 0 28-28 48-66 48S70 98 70 70z" fill="none" stroke="#14181f" stroke-width="6"/>'
    elif shape == "round":
        body = '<circle cx="110" cy="70" r="42" fill="none" stroke="#14181f" stroke-width="6"/><circle cx="210" cy="70" r="42" fill="none" stroke="#14181f" stroke-width="6"/><path d="M152 70h16" stroke="#14181f" stroke-width="6"/>'
    elif shape == "hex":
        body = '<polygon points="78,70 100,38 150,38 172,70 150,102 100,102" fill="none" stroke="#14181f" stroke-width="6"/><polygon points="148,70 170,38 220,38 242,70 220,102 170,102" fill="none" stroke="#14181f" stroke-width="6"/>'
    elif shape == "shield":
        body = '<path d="M40 48h240c-8 48-40 72-120 72S48 96 40 48z" fill="none" stroke="#14181f" stroke-width="6"/>'
    elif shape == "browline":
        body = '<path d="M60 48h90v8H78l-8 36h70V48" fill="none" stroke="#14181f" stroke-width="6"/><path d="M170 48h90v8h-64l-8 36h70" fill="none" stroke="#14181f" stroke-width="6"/>'
    else:
        body = '<rect x="58" y="40" width="90" height="58" rx="8" fill="none" stroke="#14181f" stroke-width="6"/><rect x="172" y="40" width="90" height="58" rx="8" fill="none" stroke="#14181f" stroke-width="6"/><path d="M148 68h24" stroke="#14181f" stroke-width="6"/>'
    return f'<svg {common} xmlns="http://www.w3.org/2000/svg">{body}</svg>'


def thumb(product):
    image = None
    for offer in product["offers"]:
        if offer.get("image"):
            image = offer["image"]
            break
    if image:
        alt = e(f"{display(product)} product photo")
        return f'<img src="{e(image)}" alt="{alt}" width="420" height="280" loading="lazy">'
    return shape_svg(product.get("shape") or "square")


PAGES = []
TITLES = set()


def abs_url(path):
    path = (path or "").strip().strip("/")
    if path in ("", "."):
        return f"{BASE}{PREFIX}/"
    return f"{BASE}{PREFIX}/{path}/"


def page(path, title, desc, body, jsonld=None, index=True, image=None):
    if title in TITLES:
        die(f"duplicate title: {title}")
    if len(title) > 70:
        die(f"title too long ({len(title)}): {title}")
    TITLES.add(title)
    if len(desc) > 170:
        desc = desc[:167].rsplit(" ", 1)[0] + "."
    raw = (path or "").strip()
    if raw in ("", ".", "index.html"):
        rel = ""
        dest_kind = "home"
    elif raw.endswith(".html"):
        rel = raw
        dest_kind = "file"
    else:
        rel = raw.strip("/")
        dest_kind = "dir"
    canon = f"{BASE}{PREFIX}/{rel}" if dest_kind == "file" else abs_url(rel)
    robots = "" if index else '<meta name="robots" content="noindex">'
    img = image or f"{BASE}{PREFIX}/media/og.png"
    blocks = ""
    for node in jsonld or []:
        blocks += '<script type="application/ld+json">' + json.dumps(node, ensure_ascii=False) + "</script>"
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canon)}">
{robots}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(NAME)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canon)}">
<meta property="og:image" content="{e(img)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{e(img)}">
<link rel="icon" href="{PREFIX}/media/favicon.svg">
<style>{CSS}</style>
{blocks}
</head>
<body>
<header>
<a class="logo" href="{PREFIX}/">Sunglass<span>Deals</span>Daily</a>
<nav>
<a href="{PREFIX}/">Deals</a>
<a href="{PREFIX}/brands/">Brands</a>
<a href="{PREFIX}/polarized/">Polarized</a>
<a href="{PREFIX}/fishing/">Fishing</a>
<a href="{PREFIX}/best/polarized-sunglasses-under-200/">Under $200</a>
<a href="{PREFIX}/men/">Men</a>
<a href="{PREFIX}/women/">Women</a>
<a href="{PREFIX}/gifts/">Gifts</a>
</nav>
</header>
<main>
{body}
</main>
<footer>
<p>We may earn a commission if you buy through our links, at no extra cost to you. CJ applications for Ray-Ban, Oakley, Sunglass Hut, and Costa Del Mar are pending, so buttons currently open the merchant's own page with no tracking parameters. <a href="{PREFIX}/disclosure/">Affiliate disclosure</a>.</p>
<p><a href="{PREFIX}/about/">About</a> · <a href="{PREFIX}/privacy/">Privacy</a> · <a href="{PREFIX}/llms.txt">llms.txt</a> · <a href="{PREFIX}/sitemap.xml">Sitemap</a></p>
<p>© {UPDATED.year} {e(NAME)}. Written by {e(OWNER)}. Not affiliated with Ray-Ban, Oakley, Costa, Maui Jim, Persol, Prada, Gucci, or Sunglass Hut.</p>
</footer>
</body>
</html>
"""
    if dest_kind == "home":
        dest = os.path.join(OUT, "index.html")
    elif dest_kind == "file":
        dest = os.path.join(OUT, rel)
    else:
        dest = os.path.join(OUT, rel, "index.html")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w", encoding="utf-8").write(doc)
    if index:
        PAGES.append(canon)


def crumbs(items):
    bits = []
    ld = []
    for i, (href, label) in enumerate(items, start=1):
        if href:
            bits.append(f'<a href="{href}">{e(label)}</a>')
            ld.append({"@type": "ListItem", "position": i, "name": label, "item": href if href.startswith("http") else f"{BASE}{href}"})
        else:
            bits.append(f'<span aria-current="page">{e(label)}</span>')
            ld.append({"@type": "ListItem", "position": i, "name": label})
    html_bits = " <span aria-hidden='true'>/</span> ".join(bits)
    visible = f'<p class="crumbs">{html_bits}</p>'
    data = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": ld}
    return visible, data


def card(product, page_type, page_slug):
    offer = lead(product)
    if priced(offer):
        price = f'<p class="price">{money(offer["price"])}</p>'
    else:
        price = '<p class="price price-missing">Check today\'s price</p>'
    extra = ""
    if offer.get("availability_note"):
        extra = f'<p class="meta">{e(offer["availability_note"])}</p>'
    meta = e(offer["label"])
    return (
        f'<article class="card">{thumb(product)}'
        f'<p class="meta">{e(product["brand"])}</p>'
        f'<p class="nm"><a href="{PREFIX}/sunglasses/{product["id"]}/">{e(display(product))}</a></p>'
        f'<p class="meta">{e(product["code"])}</p>{price}<p class="meta">{meta}</p>{extra}'
        f'{btn(product, offer, page_type, page_slug, "grid")}</article>'
    )


def also_line(product, page_type, page_slug):
    same = [p for p in PRODUCTS if p["brand"] == product["brand"] and p["id"] != product["id"]][:5]
    if not same:
        return ""
    bits = []
    for other in same:
        price = ""
        rows = prices_of(other)
        if rows:
            price = " · " + money(min(float(o["price"]) for o in rows))
        bits.append(f'<a href="{PREFIX}/sunglasses/{other["id"]}/">{e(display(other))}</a>{price}')
    return '<p class="also">Also popular: ' + " · ".join(bits) + "</p>"


def similar(product):
    tags = set(product.get("tags") or [])
    rows = []
    for other in PRODUCTS:
        if other["id"] == product["id"]:
            continue
        if tags.intersection(other.get("tags") or []):
            rows.append(other)
    rows.sort(key=lambda p: (0 if prices_of(p) else 1, p["brand"], p["name"]))
    return rows[:4]


def faq_block(pairs):
    body = "".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q, a in pairs)
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in pairs
        ],
    }
    return f'<section class="box"><h2>FAQ</h2>{body}</section>', data


def price_answer(product):
    rows = prices_of(product)
    when = UPDATED.isoformat()
    if not rows:
        return (
            f"No price is stored. On {when} the merchant page did not show a number we could verify. "
            "The button opens that page so you can see today's price."
        )
    bits = []
    for offer in product["offers"]:
        if priced(offer):
            bits.append(f"{offer['label']} was {money(offer['price'])} at {merchant(product)['name']}")
        else:
            bits.append(f"{offer['label']} has no stored price")
    return f"Checked {when}. " + ". ".join(bits) + "."


def deal_faqs(product):
    return [
        (f"What size is the {display(product)} on this page?", product["size_line"]),
        (f"Is this {product['name']} polarized?", product["polarized_line"]),
        (f"What does {product['name']} cost?", price_answer(product)),
        (
            "Does the button use an affiliate tracking link?",
            "No. The button is the merchant's own product URL. Commission Junction applications for Ray-Ban (3175074), Oakley (1463156), Sunglass Hut (4025749), and Costa Del Mar (5626771) are pending. When a program is approved, that merchant's click_base in data/links.json is filled in and the build adds a sid of the form pagetype-slug-placement. The plain product URL stays in the same file.",
        ),
    ]


def offer_nodes(product):
    nodes = []
    for offer in product["offers"]:
        if not priced(offer):
            continue
        node = {
            "@type": "Offer",
            "url": offer["url"],
            "priceCurrency": offer.get("currency") or "USD",
            "price": f"{float(offer['price']):.2f}",
            "seller": {"@type": "Organization", "name": merchant(product)["name"]},
            "itemCondition": "https://schema.org/NewCondition",
        }
        note = (offer.get("availability_note") or "").lower()
        if "unavailable" in note:
            node["availability"] = "https://schema.org/OutOfStock"
        nodes.append(node)
    if not nodes:
        return None
    if len(nodes) == 1:
        return nodes[0]
    values = [float(o["price"]) for o in product["offers"] if priced(o)]
    return {
        "@type": "AggregateOffer",
        "lowPrice": f"{min(values):.2f}",
        "highPrice": f"{max(values):.2f}",
        "priceCurrency": "USD",
        "offerCount": len(nodes),
        "offers": nodes,
    }


def product_node(product, page_url):
    node = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": f"{display(product)} {product['code']}",
        "sku": product["code"],
        "brand": {"@type": "Brand", "name": product["brand"]},
        "description": product["summary"],
        "url": page_url,
    }
    image = next((o["image"] for o in product["offers"] if o.get("image")), None)
    if image:
        node["image"] = image
    offers = offer_nodes(product)
    if offers:
        node["offers"] = offers
    return node


def offer_table(product, page_type, page_slug):
    rows = []
    for offer in product["offers"]:
        pol = "Yes" if offer.get("polarized") is True else "No" if offer.get("polarized") is False else "Not stated"
        price = money(offer["price"]) if priced(offer) else "Check today's price"
        note = offer.get("availability_note") or offer.get("note") or ""
        link = ext_a(product, offer, e(merchant(product)["name"]), page_type, page_slug, "table")
        rows.append(
            "<tr>"
            f"<td>{link}</td><td>{e(offer['label'])}</td><td>{pol}</td>"
            f"<td><b>{price}</b></td><td>{e(offer.get('price_checked') or '')}</td>"
            f"<td>{e(note)}</td></tr>"
        )
    return (
        "<table><thead><tr><th>Store</th><th>Colorway</th><th>Polarized</th><th>Price</th><th>Checked</th><th>Note</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_deal(product):
    offer = lead(product)
    slug = product["id"]
    name = display(product)
    code = product["code"]
    if priced(offer):
        title = f"{name}: {money(offer['price'])}"
        if len(title) > 60:
            title = f"{product['name']} {code}: {money(offer['price'])}"
        h1 = f"{name}: {money(offer['price'])}"
        desc = (
            f"{name} {code}, {offer['label']}, is {money(offer['price'])} at {merchant(product)['name']} "
            f"as of {UPDATED.isoformat()}. Other colorways can differ. No review score is shown."
        )
    else:
        title = f"{name} {code} price"
        if len(title) > 60:
            title = f"{product['name']} {code} price"
        h1 = f"{name} {code}"
        desc = (
            f"{name} {code}. {offer['label']}. We did not verify a price on {UPDATED.isoformat()}, "
            f"so the button opens {merchant(product)['name']} for today's price."
        )
    crumb_html, crumb_ld = crumbs([
        (f"{PREFIX}/", "Home"),
        (f"{PREFIX}/brands/{brand_slug(product['brand'])}/", product["brand"]),
        (None, name),
    ])
    checked = offer.get("price_checked") or UPDATED.isoformat()
    if priced(offer):
        price_html = f'<p class="lead-price"><span class="price">{money(offer["price"])}</span></p>'
        status = f"Price checked {checked}. This number is only the colorway below."
    else:
        price_html = '<p class="lead-price"><span class="price price-missing">Check today\'s price</span></p>'
        status = "No verified price for this colorway. The button opens the merchant page."
    photo = product["offers"][0].get("image")
    if photo:
        figure = (
            f'<figure class="shot"><img src="{e(photo)}" alt="{e(name + " " + offer["label"])}" width="640" height="420">'
            f'<figcaption class="meta">Photo from {e(merchant(product)["name"])} for {e(offer["label"])}.</figcaption></figure>'
        )
    else:
        figure = (
            f'<figure class="shot">{shape_svg(product.get("shape") or "square")}'
            '<figcaption class="meta">A shape sketch, not a product photo. The merchant page has the photo.</figcaption></figure>'
        )
    faq_html, faq_ld = faq_block(deal_faqs(product))
    sims = similar(product)
    sim_html = ""
    if sims:
        sim_html = '<h2>Related frames</h2><div class="grid">' + "".join(card(p, "deal", slug) for p in sims) + "</div>"
    body = (
        crumb_html
        + f"<h1>{e(h1)}</h1>"
        + f'<p class="sub">{e(product["summary"])}</p>'
        + '<div class="lead-offer">'
        + f'<p class="meta">{e(status)}</p>'
        + f'<p class="lead-name"><b>{e(name)}</b> · {e(code)}</p>'
        + price_html
        + f'<p class="meta">{e(offer["label"])} · {e(merchant(product)["name"])}</p>'
        + btn(product, offer, "deal", slug, "cta")
        + "</div>"
        + also_line(product, "deal", slug)
        + figure
        + '<section class="box"><h2>Colorways</h2>'
        + offer_table(product, "deal", slug)
        + f'<p>{e(product["lens_line"])}</p><p>{e(product["size_line"])}</p></section>'
        + faq_html
        + sim_html
    )
    image = photo or None
    page(
        f"sunglasses/{slug}",
        title,
        desc,
        body,
        [crumb_ld, product_node(product, abs_url(f"sunglasses/{slug}")), faq_ld],
        image=image if image and image.startswith("http") else None,
    )


def guide_products(guide):
    if guide.get("ids"):
        rows = []
        for pid in guide["ids"]:
            if pid not in BY_ID:
                die(f"{guide['slug']}: missing product {pid}")
            rows.append(BY_ID[pid])
        return rows
    if guide.get("filter"):
        return [p for p in PRODUCTS if guide["filter"] in (p.get("tags") or [])]
    if guide.get("audience") == "men":
        men = [p for p in PRODUCTS if p.get("audience") == "men"]
        rest = [p for p in PRODUCTS if p.get("audience") == "unisex"]
        return men + rest
    if guide.get("audience") == "women":
        women = [p for p in PRODUCTS if p.get("audience") == "women"]
        rest = [p for p in PRODUCTS if p.get("audience") == "unisex"]
        return women + rest
    return []


def listing_ld(rows, name, page_url):
    items = []
    for i, product in enumerate(rows, start=1):
        item = {"@type": "ListItem", "position": i, "name": f"{display(product)} {product['code']}", "url": abs_url(f"sunglasses/{product['id']}")}
        items.append(item)
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "url": page_url, "itemListElement": items}


def render_listing(path, title, h1, desc, intro, rows, crumb, page_type):
    slug = path.strip("/").split("/")[-1]
    crumb_html, crumb_ld = crumbs(crumb)
    grid = "".join(card(p, page_type, slug) for p in rows) or "<p>No frames in this list.</p>"
    body = crumb_html + f"<h1>{e(h1)}</h1><p class='sub'>{e(intro)}</p><div class='grid'>{grid}</div>"
    faqs = [
        ("Where do the prices come from?", "A price is printed only when that colorway's public product page showed the number on the date in the table. Otherwise the button says check today's price."),
        ("Are these ranked by reviews?", "No. This site does not publish star ratings or review counts."),
    ]
    faq_html, faq_ld = faq_block(faqs)
    body += faq_html
    page(path, title, desc, body, [crumb_ld, listing_ld(rows, h1, abs_url(path)), faq_ld])


def render_under_200():
    path = "best/polarized-sunglasses-under-200"
    title = "Polarized sunglasses under $200"
    h1 = "Polarized sunglasses under $200"
    intro = next(g["intro"] for g in GUIDES if g["slug"] == "polarized-sunglasses-under-200")
    crumb_html, crumb_ld = crumbs([
        (f"{PREFIX}/", "Home"),
        (f"{PREFIX}/best/polarized-sunglasses-under-200/", None) if False else (f"{PREFIX}/", "Home"),
        (None, "Under $200"),
    ])
    # rebuild crumbs cleanly
    crumb_html, crumb_ld = crumbs([
        (f"{PREFIX}/", "Home"),
        (None, "Polarized under $200"),
    ])
    polarized_priced = []
    polarized_blank = []
    under_not_pol = []
    for product in PRODUCTS:
        for offer in product["offers"]:
            if offer.get("polarized") is True and priced(offer):
                polarized_priced.append((product, offer))
            elif offer.get("polarized") is True and not priced(offer):
                polarized_blank.append((product, offer))
            elif offer.get("polarized") is False and priced(offer) and float(offer["price"]) < 200:
                under_not_pol.append((product, offer))
    polarized_priced.sort(key=lambda row: float(row[1]["price"]))
    under_not_pol.sort(key=lambda row: float(row[1]["price"]))

    def line(product, offer):
        price = money(offer["price"]) if priced(offer) else "Check today's price"
        return (
            "<li><a href='{p}/sunglasses/{id}/'>{name}</a> — {label}: <b>{price}</b>. {btn}</li>".format(
                p=PREFIX,
                id=product["id"],
                name=e(display(product) + " " + product["code"]),
                label=e(offer["label"]),
                price=price,
                btn=btn(product, offer, "best", "polarized-sunglasses-under-200", "cta"),
            )
        )

    body = (
        crumb_html
        + f"<h1>{e(h1)}</h1>"
        + f"<p class='sub'>{e(intro)}</p>"
        + "<section class='box'><h2>Polarized colorways with a price we read</h2><ul>"
        + "".join(line(p, o) for p, o in polarized_priced)
        + "</ul><p class='note'>None of these polarized prices is under $200.</p></section>"
        + "<section class='box'><h2>Polarized, no price stored</h2><ul>"
        + "".join(line(p, o) for p, o in polarized_blank)
        + "</ul><p>Costa did not show a price on the pages we opened, so those frames are not called under $200 here.</p></section>"
        + "<section class='box'><h2>Under $200, and not labeled polarized</h2><ul>"
        + "".join(line(p, o) for p, o in under_not_pol)
        + "</ul><p>These colorways priced under $200. The merchant page did not call the lens polarized. A polarized colorway of the same model can cost more, as it does on Holbrook.</p></section>"
    )
    faqs = [
        ("Which polarized sunglasses were under $200?", "None of the polarized colorways we priced on November 15, 2026. The lowest polarized price we read was $225.00 for Oakley Half Jacket 2.0 XL in Prizm Deep Water Polarized."),
        ("Why is Holbrook both $174.00 and $237.00?", "Those are two colorways. Prizm Grey was $174.00 and is not labeled polarized. Prizm Black Polarized was $237.00."),
        ("Why doesn't Costa show a price?", "The Costa product pages we opened did not include a price in the text. The button opens Costa so you can see today's price."),
    ]
    faq_html, faq_ld = faq_block(faqs)
    body += faq_html
    desc = "Polarized colorways we priced on November 15, 2026 started at $225.00. No polarized price under $200 is shown, because we did not read one."
    page(path, title, desc, body, [crumb_ld, faq_ld])


def render_vs(guide):
    a = BY_ID[guide["a"]]
    b = BY_ID[guide["b"]]
    path = guide["path"]
    crumb_html, crumb_ld = crumbs([
        (f"{PREFIX}/", "Home"),
        (None, guide["h1"]),
    ])
    def cell(product):
        offer = lead(product)
        price = money(offer["price"]) if priced(offer) else "Check today's price"
        return (
            f"<td><a href='{PREFIX}/sunglasses/{product['id']}/'>{e(display(product))} {e(product['code'])}</a>"
            f"<p>{e(offer['label'])}</p><p><b>{price}</b></p>{btn(product, offer, 'vs', guide['slug'], 'table')}</td>"
        )
    points = "".join(f"<li>{e(p)}</li>" for p in guide["points"])
    body = (
        crumb_html
        + f"<h1>{e(guide['h1'])}</h1>"
        + f"<p class='sub'>{e(guide['intro'])}</p>"
        + "<div class='lead-offer'><p class='meta'>Open either model. The price sits with the buy button.</p>"
        + f"<p>{btn(a, lead(a), 'vs', guide['slug'], 'cta')} {btn(b, lead(b), 'vs', guide['slug'], 'cta')}</p></div>"
        + f"<table><thead><tr><th>{e(display(a))}</th><th>{e(display(b))}</th></tr></thead><tbody><tr>{cell(a)}{cell(b)}</tr></tbody></table>"
        + f"<section class='box'><h2>What is different</h2><ul>{points}</ul></section>"
    )
    faqs = [
        (f"How is {a['name']} different from {b['name']}?", " ".join(guide["points"])),
        ("Which one is cheaper?", price_answer(a) + " " + price_answer(b)),
    ]
    faq_html, faq_ld = faq_block(faqs)
    body += faq_html
    desc = guide["intro"]
    if len(desc) < 70:
        desc = desc + " Prices are shown only when the merchant page showed them."
    page(path, guide["title"], desc, body, [
        crumb_ld,
        product_node(a, abs_url(f"sunglasses/{a['id']}")),
        product_node(b, abs_url(f"sunglasses/{b['id']}")),
        faq_ld,
    ])


def render_home():
    priced_products = [p for p in PRODUCTS if prices_of(p)]
    priced_products.sort(key=lambda p: float(lead(p)["price"]))
    blanks = [p for p in PRODUCTS if not prices_of(p)]
    brands = []
    seen = set()
    for p in PRODUCTS:
        if p["brand"] not in seen:
            seen.add(p["brand"])
            brands.append(p["brand"])
    chips = "".join(f'<a href="{PREFIX}/brands/{brand_slug(b)}/">{e(b)}</a>' for b in brands)
    guides = "".join(
        f'<a href="{PREFIX}/{g["path"]}/">{e(g["title"])}</a>' for g in GUIDES
    )
    first = priced_products[0]
    body = (
        f"<h1>Sunglass deals for {UPDATED.strftime('%B %-d, %Y')}</h1>"
        "<p class='sub'>Each model has its own page. The price and the buy button sit above the photo. "
        "A price is printed only when that colorway's merchant page showed it. Otherwise the button says check today's price.</p>"
        '<div class="lead-offer">'
        f'<p class="meta">Lowest price we read</p>'
        f'<p class="lead-name"><b>{e(display(first))}</b> · {e(first["code"])}</p>'
        f'<p class="lead-price"><span class="price">{money(lead(first)["price"])}</span></p>'
        f'<p class="meta">{e(lead(first)["label"])}</p>'
        f'{btn(first, lead(first), "home", "index", "cta")}'
        f' <a class="btn" href="{PREFIX}/sunglasses/{first["id"]}/" style="background:#0f4c5c">See the {e(first["name"])} page</a>'
        "</div>"
        + also_line(first, "home", "index")
        + "<h2>Prices we could read</h2><div class='grid'>"
        + "".join(card(p, "home", "index") for p in priced_products)
        + "</div><h2>Check today's price</h2><p class='sub'>These model pages are up. The merchant page did not show a price we could store.</p><div class='grid'>"
        + "".join(card(p, "home", "index") for p in blanks)
        + f"</div><section class='box'><h2>Brands</h2><div class='chips'>{chips}</div></section>"
        + f"<section class='box'><h2>Guides</h2><div class='chips'>{guides}</div></section>"
    )
    desc = (
        f"Sunglass deals for Wayfarer, Aviator, Holbrook, Frogskins, Costa, Persol 714, and more. "
        f"Prices checked {UPDATED.isoformat()} only when the merchant page showed one."
    )
    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": NAME,
        "url": abs_url(""),
        "description": desc,
        "publisher": {"@type": "Organization", "name": NAME, "founder": {"@type": "Person", "name": OWNER}},
    }
    page("index.html", f"{NAME}: sunglass prices", desc, body, [website])
    # page() treats index.html as a path and would nest it. Handle homepage separately.
    # The call above uses path index.html which abs_url and dest logic mishandles.
    # Fix by rewriting homepage after. See main().


def write_homepage_fix():
    """page('index.html') would write site/index.html/index.html. Write the homepage in main instead."""
    return None


def render_static():
    about = f"""
<p class="crumbs"><a href="{PREFIX}/">Home</a> / About</p>
<h1>About {e(NAME)}</h1>
<p>{e(NAME)} is a static guide to famous sunglasses, written by {e(OWNER)}. It lists one page per model: Ray-Ban Wayfarer, Aviator, Clubmaster, Oakley Holbrook, Frogskins, Costa fishing frames, Maui Jim, Persol, Prada, and Gucci styles sold at Sunglass Hut.</p>
<p>The price and the buy button sit above the photo, which is the layout that works on our fragrance sister site. A dollar amount is stored only after we read it on the merchant's public product page. This site does not invent prices, star ratings, or reviews.</p>
<p>Commission Junction applications are pending for Ray-Ban US (advertiser 3175074), Oakley US (1463156), Sunglass Hut US (4025749), and Costa Del Mar (5626771). Until those are approved, every button is a plain link to the merchant. The product key in <code>data/links.json</code> is where a CJ deep link will be swapped in later. The sid on that future link is pagetype-slug-placement.</p>
<p>The public site is https://sunglassdealsdaily.com. Canonical URLs, the sitemap, and internal links use that host with no path prefix. The github.io address redirects here. The custom domain is set in GitHub Pages; this repo does not include a CNAME file.</p>
"""
    privacy = f"""
<p class="crumbs"><a href="{PREFIX}/">Home</a> / Privacy</p>
<h1>Privacy</h1>
<p>{e(NAME)} is a static site. It has no accounts, no newsletter, and no form. The pages themselves do not set cookies and do not embed a third-party tracker.</p>
<p>GitHub Pages, which hosts the site, receives the usual request data (IP address, user agent, and the page you asked for) in its own logs. Read GitHub's privacy statement for how that host handles logs.</p>
<p>Outbound buttons go to Ray-Ban, Oakley, Costa Del Mar, or Sunglass Hut. Those sites have their own privacy policies and may set their own cookies after you leave this site. We do not receive your payment details.</p>
<p>We do not sell personal information. There is no advertising cookie on these pages.</p>
<p>Questions: this site is published by {e(OWNER)}.</p>
"""
    disclosure = f"""
<p class="crumbs"><a href="{PREFIX}/">Home</a> / Disclosure</p>
<h1>Affiliate disclosure</h1>
<p>{e(NAME)} intends to earn a commission if you buy through our links. You do not pay extra for that. As of {UPDATED.isoformat()}, the Commission Junction applications below are pending, and no button uses a tracking domain.</p>
<ul>
<li>Ray-Ban US, CJ advertiser 3175074, application pending.</li>
<li>Oakley US, CJ advertiser 1463156, application pending.</li>
<li>Sunglass Hut US, CJ advertiser 4025749, application pending.</li>
<li>Costa Del Mar, CJ advertiser 5626771, application pending.</li>
</ul>
<p>Every product URL lives in one file, <code>data/links.json</code>, on that product's key. When a program is approved, set that merchant's <code>cj.click_base</code> to the CJ click URL. The next build wraps the plain product URL and adds a sid: <code>{{pagetype}}-{{slug}}-{{placement}}</code>. Placements used on the pages are cta, table, grid, and also. The sid is at most 64 characters and uses only letters, numbers, hyphens, and underscores.</p>
<p>A CJ product feed can fill <code>offers[].price</code> later. Match <code>advertiser_id</code> plus <code>sku</code>. The build will not invent a price if the feed row has none. <code>scripts/apply_feed.py</code> does that merge from a local file and does not call the network.</p>
<p>This site does not link to Amazon, eBay, Walmart, Nordstrom Rack, or Sephora. It does not publish star ratings or customer reviews. Prices change. The date on a price is the day we read it on the merchant page.</p>
<p>{e(NAME)} is not Ray-Ban, Oakley, Costa, Maui Jim, Persol, Prada, Gucci, or Sunglass Hut.</p>
"""
    page("about", f"About {NAME}", f"{NAME} is {OWNER}'s static sunglass deal guide. Prices are stored only when a merchant page showed them.", about, index=True)
    page("privacy", f"Privacy · {NAME}", f"Privacy policy for {NAME}. Static pages, no accounts, no tracker on the site itself.", privacy, index=True)
    page("disclosure", f"Affiliate disclosure · {NAME}", "CJ applications for Ray-Ban, Oakley, Sunglass Hut, and Costa are pending. Buttons are plain merchant URLs until a click_base is added.", disclosure, index=True)
    missing = f"""
<p class="crumbs"><a href="{PREFIX}/">Home</a></p>
<h1>Page not found</h1>
<p>That URL is not on {e(NAME)}. Try a model page or the <a href="{PREFIX}/">deal list</a>.</p>
"""
    page("404.html", "Page not found", "That page is not on SunglassDealsDaily.", missing, index=False)


def render_brands():
    brands = []
    seen = set()
    for p in PRODUCTS:
        if p["brand"] not in seen:
            seen.add(p["brand"])
            brands.append(p["brand"])
    cards = []
    for brand in brands:
        rows = [p for p in PRODUCTS if p["brand"] == brand]
        priced_rows = [p for p in rows if prices_of(p)]
        if priced_rows:
            low = min(float(lead(p)["price"]) for p in priced_rows)
            extra = f"From {money(low)}"
        else:
            extra = "Check today's price"
        cards.append(
            f'<a class="card" href="{PREFIX}/brands/{brand_slug(brand)}/"><span class="nm">{e(brand)}</span>'
            f'<span class="meta">{len(rows)} models</span><span class="price" style="font-size:18px">{e(extra)}</span></a>'
        )
    body = (
        f'<p class="crumbs"><a href="{PREFIX}/">Home</a> / Brands</p>'
        "<h1>Sunglass brands</h1>"
        "<p class='sub'>Ray-Ban and Oakley link to their own US stores. Costa links to Costa. Maui Jim, Persol, Prada, and Gucci link to the Sunglass Hut product page.</p>"
        f"<div class='grid'>{''.join(cards)}</div>"
    )
    desc = "Brand pages for Ray-Ban, Oakley, Costa Del Mar, Maui Jim, Persol, Prada, and Gucci sunglasses."
    crumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": abs_url("")},
        {"@type": "ListItem", "position": 2, "name": "Brands"},
    ]}
    page("brands", "Sunglass brands", desc, body, [crumb])
    for brand in brands:
        rows = [p for p in PRODUCTS if p["brand"] == brand]
        rows.sort(key=lambda p: (0 if prices_of(p) else 1, float(lead(p)["price"]) if prices_of(p) else 0, p["name"]))
        render_listing(
            f"brands/{brand_slug(brand)}",
            f"{brand} sunglasses",
            f"{brand} sunglasses",
            f"{brand} models on {NAME}. A price is shown only for a colorway whose product page showed one on {UPDATED.isoformat()}.",
            f"{len(rows)} {brand} models. The buy button uses the store named on each page.",
            rows,
            [(f"{PREFIX}/", "Home"), (f"{PREFIX}/brands/", "Brands"), (None, brand)],
            "brand",
        )


def write_robots_and_sitemap():
    robots = (
        "User-agent: *\nAllow: /\n"
        "Disallow: /go/\nDisallow: /out/\nDisallow: /redirect/\nDisallow: /r/\n\n"
        f"Sitemap: {BASE}{PREFIX}/sitemap.xml\n"
    )
    open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write(robots)
    urls = "".join(
        f"<url><loc>{e(u)}</loc><lastmod>{UPDATED.isoformat()}</lastmod></url>" for u in PAGES
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + urls + "</urlset>\n"
    )
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(xml)
    lines = [
        f"# {NAME}",
        f"> Famous sunglasses with a price only when the merchant page showed one. Updated {UPDATED.isoformat()}.",
        "",
        "## Models",
    ]
    for p in PRODUCTS:
        offer = lead(p)
        price = money(offer["price"]) if priced(offer) else "price not stored"
        lines.append(
            f"- {display(p)} {p['code']}: {price} at {merchant(p)['name']}: {offer['url']}"
        )
    lines += ["", "## Pages", f"- Home: {abs_url('')}"]
    for u in PAGES:
        lines.append(f"- {u}")
    open(os.path.join(OUT, "llms.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    open(os.path.join(OUT, ".nojekyll"), "w", encoding="utf-8").write("")
    json.dump(DATA, open(os.path.join(OUT, "links.json"), "w", encoding="utf-8"), indent=2)
    os.makedirs(os.path.join(OUT, "media"), exist_ok=True)
    write_png(os.path.join(OUT, "media", "og.png"))
    fav = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#14181f"/><rect x="4" y="14" width="10" height="8" rx="2" fill="none" stroke="#e8a317" stroke-width="2"/><rect x="18" y="14" width="10" height="8" rx="2" fill="none" stroke="#e8a317" stroke-width="2"/></svg>'
    open(os.path.join(OUT, "media", "favicon.svg"), "w", encoding="utf-8").write(fav)


def assert_catalog():
    ids = [p["id"] for p in PRODUCTS]
    if len(ids) != len(set(ids)):
        die("duplicate product id")
    if not (30 <= len(PRODUCTS) <= 50):
        die(f"expected 30-50 products, found {len(PRODUCTS)}")
    for p in PRODUCTS:
        if not p["offers"]:
            die(f"{p['id']}: no offers")
        for offer in p["offers"]:
            if links.is_tracking_url(offer["url"]) or links.is_blocked_url(offer["url"]):
                die(f"{p['id']}: bad url {offer['url']}")
            if priced(offer):
                if not offer.get("price_checked"):
                    die(f"{p['id']}: priced offer missing price_checked")
                if offer.get("currency") != "USD":
                    die(f"{p['id']}: currency must be USD")
            elif offer.get("price") not in (None,):
                die(f"{p['id']}: price must be a number or null")
        click = (merchant(p).get("cj") or {}).get("click_base")
        if click:
            links.wrap_cj(click, p["offers"][0]["url"], "deal-test-cta")


def main():
    if os.path.isdir(OUT):
        import shutil
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)
    assert_catalog()
    # Homepage is written with path "" by a dedicated call after helpers exist.
    def hero_offer(product):
        rows = [o for o in prices_of(product) if "unavailable" not in (o.get("availability_note") or "").lower()]
        if not rows:
            return None
        return min(rows, key=lambda o: float(o["price"]))
    heroes = []
    for product in PRODUCTS:
        offer = hero_offer(product)
        if offer:
            heroes.append((float(offer["price"]), product, offer))
    heroes.sort(key=lambda row: row[0])
    _, first, first_offer = heroes[0]
    priced_products = sorted((p for p in PRODUCTS if prices_of(p)), key=lambda p: float(lead(p)["price"]))
    blanks = [p for p in PRODUCTS if not prices_of(p)]
    brands = []
    seen = set()
    for p in PRODUCTS:
        if p["brand"] not in seen:
            seen.add(p["brand"])
            brands.append(p["brand"])
    chips = "".join(f'<a href="{PREFIX}/brands/{brand_slug(b)}/">{e(b)}</a>' for b in brands)
    guides = "".join(f'<a href="{PREFIX}/{g["path"]}/">{e(g["title"])}</a>' for g in GUIDES)
    home = (
        f"<h1>Sunglass deals for {UPDATED.strftime('%B %-d, %Y')}</h1>"
        "<p class='sub'>Each famous model has its own page. The price and the buy button sit above the photo. "
        "A price is printed only when that colorway's merchant page showed it. Otherwise the button says check today's price.</p>"
        '<div class="lead-offer">'
        '<p class="meta">Lowest in-stock price we read on a merchant page</p>'
        f'<p class="lead-name"><b>{e(display(first))}</b> · {e(first["code"])}</p>'
        f'<p class="lead-price"><span class="price">{money(first_offer["price"])}</span></p>'
        f'<p class="meta">{e(first_offer["label"])} · {e(merchant(first)["name"])}</p>'
        f'{btn(first, first_offer, "home", "index", "cta")}'
        "</div>"
        + also_line(first, "home", "index")
        + "<h2>Prices we could read</h2><div class='grid'>"
        + "".join(card(p, "home", "index") for p in priced_products)
        + "</div><h2>Named models, price not stored</h2><div class='grid'>"
        + "".join(card(p, "home", "index") for p in blanks)
        + f"</div><section class='box'><h2>Brands</h2><div class='chips'>{chips}</div></section>"
        + f"<section class='box'><h2>Guides</h2><div class='chips'>{guides}</div></section>"
    )
    desc = (
        f"Wayfarer, Aviator, Holbrook, Frogskins, Costa, Persol 714, and other sunglass deals. "
        f"Prices from merchant pages on {UPDATED.isoformat()}, or a check-today's-price button."
    )
    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": NAME,
        "url": abs_url(""),
        "description": desc,
        "publisher": {"@type": "Organization", "name": NAME, "founder": {"@type": "Person", "name": OWNER}},
    }
    # Write homepage at site/index.html by passing a sentinel path.
    page(".", "Sunglass deals today", desc, home, [website])
    for product in PRODUCTS:
        render_deal(product)
    render_brands()
    for guide in GUIDES:
        if guide["slug"] == "polarized-sunglasses-under-200":
            render_under_200()
            continue
        if guide["type"] == "vs":
            render_vs(guide)
            continue
        rows = guide_products(guide)
        kind = "gifts" if guide["type"] == "gift" else guide["type"]
        parent = None
        if guide["type"] == "gift":
            parent = (f"{PREFIX}/gifts/", "Gifts")
        render_listing(
            guide["path"],
            guide["title"],
            guide["h1"],
            guide["intro"],
            guide["intro"],
            rows,
            [(f"{PREFIX}/", "Home")] + ([parent] if parent else []) + [(None, guide["h1"])],
            kind,
        )
    gift_rows = [g for g in GUIDES if g["type"] == "gift"]
    gift_links = "".join(
        f'<p><a href="{PREFIX}/{g["path"]}/">{e(g["title"])}</a></p>' for g in gift_rows
    )
    page(
        "gifts",
        "Sunglasses gifts",
        "Father's Day and Christmas sunglass gift pages. Prices only when a merchant page showed them.",
        f'<p class="crumbs"><a href="{PREFIX}/">Home</a> / Gifts</p><h1>Sunglasses gifts</h1>'
        f"<p class='sub'>Gift pages for named models. A missing price means we did not read one on the merchant page.</p>{gift_links}",
        [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": abs_url("")},
            {"@type": "ListItem", "position": 2, "name": "Gifts"},
        ]}],
    )
    render_static()
    write_robots_and_sitemap()
    # The "." path becomes site/index.html via the logic below? Check page().
    print(f"{len(PRODUCTS)} models, {len(PAGES)} indexable URLs -> {OUT}")


if __name__ == "__main__":
    main()
