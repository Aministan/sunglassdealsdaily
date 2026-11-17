#!/usr/bin/env python3
"""Save each colorway's official photo as media/products/{id}.jpg.

Product page URLs come from data/links.json. The script requests that merchant
page and uses its og:image (or the Product JSON-LD image). It does not request
affiliate click hosts, and it does not open /go/, /out/, /redirect/, or /r/.

When the merchant HTML is blocked, a photo already stored on the offer is used
only if it is an https image on that merchant's own host and the file name
contains the model code. A shared or mismatched image is skipped. Prices,
URLs, and every other field stay as they are.

Pillow is imported inside the resize function. The site build does not run
this script and does not import Pillow.
"""
import io
import json
import os
import re
import ssl
import urllib.parse
import urllib.request

import links

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS = os.path.join(ROOT, "data", "links.json")
MEDIA_DIR = os.path.join(ROOT, "media", "products")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
SKIP_NAME = ("logo", "icon", "favicon", "sprite", "badge", "payment", "placeholder", "pixel")
# og:image URLs read from the merchant product page when that page did not
# already have an image in data/links.json. The live page wins when it loads.
FOUND = {
    ("ray-ban-new-wayfarer-rb2132", 0): "https://images2.ray-ban.com//prod-onecp-record-files/pieyewear/e21b2a98-b405-4c33-93ec-b35d00dd09c5/0RB2132__902L__STD__shad__qt.png?impolicy=RB_RB_FBShare",
    ("ray-ban-aviator-rb3025", 0): "https://images2.ray-ban.com//prod-onecp-record-files/pieyewear/6ad42b4b-f1af-45cc-a6c6-b35d00db1f85/0RB3025__L0205__STD__shad__qt.png?impolicy=RB_RB_FBShare",
    ("ray-ban-aviator-rb3025", 1): "https://images2.ray-ban.com//prod-onecp-record-files/pieyewear/067a1851-db2a-469a-a9cc-b35d00dad68a/0RB3025__004_58__STD__shad__qt.png?impolicy=RB_RB_FBShare",
    ("ray-ban-clubmaster-rb3016", 0): "https://images2.ray-ban.com//prod-onecp-record-files/pieyewear/0db3121e-4066-4643-b758-b35d00d06419/0RB3016__W0365__STD__shad__qt.png?impolicy=RB_RB_FBShare",
    ("ray-ban-round-metal-rb3447", 0): "https://images2.ray-ban.com//prod-onecp-record-files/pieyewear/0e2aa848-036f-4b52-b5cf-b36001626b2a/0RB3447__919648__STD__shad__qt.png?impolicy=RB_RB_FBShare",
    ("ray-ban-erika-rb4171", 0): "https://images2.ray-ban.com//prod-onecp-record-files/pieyewear/75cb6ac1-760f-4e23-b595-b35d00dd61e9/0RB4171__865_13__STD__shad__qt.png?impolicy=RB_RB_FBShare",
    ("ray-ban-justin-rb4165", 0): "https://images2.ray-ban.com//prod-onecp-record-files/pieyewear/bb1e17a9-7a18-48a0-8b1a-b35d018347b6/0RB4165__622_55__STD__shad__qt.png?impolicy=RB_RB_FBShare",
    ("ray-ban-hexagonal-rb3548", 0): "https://images2.ray-ban.com//prod-onecp-record-files/pieyewear/e3fc9840-27e3-45eb-8019-b36000cd3d7a/0RB3548__919631__STD__shad__qt.png?impolicy=RB_RB_FBShare",
    ("oakley-sutro-lite-s", 0): "https://assets2.oakley.com/prod-onecp-record-files/pieyewear/34316dbd-d840-4653-96d9-b3a1003f7fc2/0OO9496__949601__P21__shad__qt.png",
    ("prada-pr-19zs", 0): "https://assets2.sunglasshut.com/prod-onecp-record-files/pieyewear/449ef23d-126d-4c39-94a4-b3620031221e/0PR_19ZS__1AB5S0__P21__shad__qt.png",
    ("prada-pr-06ys", 0): "https://assets2.sunglasshut.com/prod-onecp-record-files/pieyewear/4a8f36ef-c49a-415c-b286-b36100c8dfd3/0PR_06YS__09Q5S0__STD__shad__qt.png",
    ("prada-pr-65zs", 0): "https://assets2.sunglasshut.com/prod-onecp-record-files/pieyewear/f1bca610-6b3a-4414-a809-b37000fe3952/0PR_65ZS__ZVN09T__P21__shad__qt.png",
}
CTX = ssl.create_default_context()


def blocked(url):
    if not isinstance(url, str) or not url:
        return True
    if links.is_tracking_url(url) or links.is_blocked_url(url):
        return True
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return True
    return links.is_redirect_path(parts.path)


class GuardRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if blocked(newurl):
            raise RuntimeError(f"refusing redirect to {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(GuardRedirect, urllib.request.HTTPSHandler(context=CTX))


def request_url(url):
    parts = urllib.parse.urlsplit(url.strip())
    path = urllib.parse.quote(urllib.parse.unquote(parts.path), safe="/%")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def fetch(url, accept, limit, user_agent=UA):
    if blocked(url):
        raise RuntimeError(f"refusing {url}")
    # Oakley's image host rejects a browser user agent from this network and
    # serves the file to a plain client. The URL is still the merchant's own.
    req = urllib.request.Request(request_url(url), headers={"User-Agent": user_agent, "Accept": accept})
    with OPENER.open(req, timeout=20) as resp:
        final = resp.geturl()
        if blocked(final):
            raise RuntimeError(f"refusing final {final}")
        data = resp.read(limit)
        ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        return final, ctype, data


def registrable(host):
    parts = (host or "").lower().split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host or ""


def codes(product, offer):
    blob = " ".join(
        [
            product.get("code") or "",
            product.get("id") or "",
            offer.get("sku") or "",
            urllib.parse.urlparse(offer.get("url") or "").path,
        ]
    )
    compact = re.sub(r"[^A-Za-z0-9]+", "", product.get("code") or "")
    found = re.findall(r"[A-Za-z0-9]{4,}", blob)
    if len(compact) >= 4:
        found.append(compact)
    return [item.lower() for item in found]


def image_matches(url, product, offer):
    name = urllib.parse.unquote(urllib.parse.urlsplit(url).path).lower().replace("_", "")
    return any(token.replace("_", "") in name for token in codes(product, offer))


def acceptable(url, product, offer):
    if not isinstance(url, str) or not url.startswith("https://") or blocked(url):
        return False
    if registrable(links.host_of(url)) != registrable(links.host_of(offer.get("url") or "")):
        return False
    if not image_matches(url, product, offer):
        return False
    name = urllib.parse.unquote(urllib.parse.urlsplit(url).path).lower()
    if any(token in name for token in SKIP_NAME):
        return False
    return re.search(r"\.(jpe?g|png|webp)(?:$|\?)", url, flags=re.I) is not None


def attr(tag, name):
    match = re.search(rf"""\b{name}\s*=\s*(['"])(.*?)\1""", tag, flags=re.I | re.S)
    return html_unescape(match.group(2)).strip() if match else ""


def html_unescape(value):
    return (
        value.replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


def meta_images(page):
    found = []
    for tag in re.findall(r"<meta\b[^>]*>", page, flags=re.I):
        prop = (attr(tag, "property") or attr(tag, "name")).lower()
        if prop in ("og:image", "og:image:secure_url", "twitter:image"):
            content = attr(tag, "content")
            if content:
                found.append(content)
    return found


def flatten_image(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(flatten_image(item))
        return out
    if isinstance(value, dict):
        url = value.get("url") or value.get("contentUrl")
        return [url] if isinstance(url, str) else []
    return []


def jsonld_images(page):
    images = []
    for raw in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        page,
        flags=re.I | re.S,
    ):
        try:
            data = json.loads(html_unescape(raw.strip()))
        except json.JSONDecodeError:
            continue
        images.extend(product_images(data))
    return images


def product_images(node):
    found = []
    if isinstance(node, list):
        for item in node:
            found.extend(product_images(item))
        return found
    if not isinstance(node, dict):
        return found
    kind = node.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    if "Product" in kinds and node.get("image"):
        found.extend(flatten_image(node["image"]))
    for value in node.values():
        if isinstance(value, (dict, list)):
            found.extend(product_images(value))
    return found


def page_images(page, page_url):
    ordered = []
    for candidate in meta_images(page) + jsonld_images(page):
        url = urllib.parse.urljoin(page_url, candidate.strip())
        parts = urllib.parse.urlsplit(url)
        if parts.scheme == "http":
            url = urllib.parse.urlunsplit(("https",) + parts[1:])
        if url not in ordered:
            ordered.append(url)
    return ordered


def save_jpeg(data, dest):
    # Lazy import: a top-level Pillow import has broken a deploy before.
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    image.load()
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        plate = Image.new("RGB", rgba.size, (255, 255, 255))
        plate.paste(rgba, mask=rgba.split()[-1])
        image = plate
    else:
        image = image.convert("RGB")
    width, height = image.size
    if width < 200 or height < 200:
        raise RuntimeError(f"image is only {width}x{height}")
    ratio = width / height
    if ratio > 2.6 or ratio < 0.35:
        raise RuntimeError(f"image ratio {width}x{height} does not look like a product photo")
    if width > 600:
        height = max(1, round(height * 600 / width))
        width = 600
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    image.save(dest, "JPEG", quality=78, optimize=True, progressive=True)
    return width, height


def filename_for(product, index):
    if index == 0:
        return product["id"] + ".jpg"
    return f"{product['id']}-{index + 1}.jpg"


def try_download(url, dest):
    final, ctype, data = fetch(
        url,
        "image/avif,image/webp,image/png,image/*,*/*;q=0.8",
        20_000_000,
        user_agent="curl/8.5.0",
    )
    if blocked(final):
        raise RuntimeError(f"rejected host {final}")
    if ctype and not ctype.startswith("image/"):
        raise RuntimeError(f"content-type {ctype}")
    return save_jpeg(data, dest)


def candidates(product, offer, index):
    ordered = []
    page_url = offer.get("url")
    if isinstance(page_url, str) and page_url.startswith("https://") and not blocked(page_url):
        try:
            final, ctype, body = fetch(page_url, "text/html,application/xhtml+xml", 1_500_000)
            if "html" in ctype or "xml" in ctype:
                ordered.extend(page_images(body.decode("utf-8", "replace"), final))
        except Exception as exc:
            print(f"page {product['id']}#{index}: {exc}")
    found = FOUND.get((product["id"], index))
    if found:
        ordered.append(found)
    current = offer.get("image")
    if isinstance(current, str) and current.startswith("https://"):
        ordered.append(current)
    unique = []
    for url in ordered:
        if url not in unique:
            unique.append(url)
    return unique


def priced(offer):
    price = offer.get("price")
    return isinstance(price, (int, float)) and not isinstance(price, bool) and price > 0


def patch_image(text, offer_url, image, width, height):
    marker = json.dumps(offer_url)
    pos = text.find(marker)
    if pos < 0:
        raise SystemExit(f"url not found in links.json: {offer_url}")
    img_key = text.find('"image"', pos)
    if img_key < 0 or img_key - pos > 900:
        raise SystemExit(f"image field not found for {offer_url}")
    line_start = text.rfind("\n", 0, img_key) + 1
    line_end = text.find("\n", img_key)
    indent = "          "
    block = (
        f'{indent}"image": {json.dumps(image)},\n'
        f'{indent}"image_width": {int(width)},\n'
        f'{indent}"image_height": {int(height)},'
    )
    # Drop a previous width/height pair so a re-run does not stack them.
    rest = text[line_end + 1:]
    for key in ("image_width", "image_height"):
        if rest.startswith(f'{indent}"{key}"'):
            rest = rest.split("\n", 1)[1]
    return text[:line_start] + block + "\n" + rest


def main():
    original = open(LINKS, encoding="utf-8").read()
    data = json.loads(original)
    before = [
        (p["id"], o.get("url"), o.get("price"), o.get("currency"), o.get("price_checked"), o.get("label"))
        for p in data["products"]
        for o in p["offers"]
    ]
    saved = {}
    skipped = []
    for product in data["products"]:
        for index, offer in enumerate(product["offers"]):
            dest_name = filename_for(product, index)
            dest = os.path.join(MEDIA_DIR, dest_name)
            errors = []
            done = None
            for url in candidates(product, offer, index):
                if not acceptable(url, product, offer):
                    errors.append(f"rejected {url}")
                    continue
                try:
                    width, height = try_download(url, dest)
                except Exception as exc:
                    errors.append(f"{url} ({exc})")
                    if os.path.exists(dest) and not str(offer.get("image") or "").endswith(dest_name):
                        os.remove(dest)
                    continue
                done = (f"/media/products/{dest_name}", width, height, url)
                break
            if done:
                saved[(product["id"], index)] = done
                print(f"ok   {product['id']}#{index} {done[1]}x{done[2]} {done[3]}")
            else:
                if os.path.exists(dest) and str(offer.get("image") or "") == f"/media/products/{dest_name}":
                    print(f"keep {product['id']}#{index}")
                else:
                    if os.path.exists(dest) and not str(offer.get("image") or "").endswith(dest_name):
                        os.remove(dest)
                    skipped.append((product["id"], index, "; ".join(errors) or "no matching product image"))
                    print(f"skip {product['id']}#{index}: {skipped[-1][2][:240]}")
    missing_deals = []
    for product in data["products"]:
        for index, offer in enumerate(product["offers"]):
            if not priced(offer):
                continue
            if "unavailable" in (offer.get("availability_note") or "").lower():
                continue
            if (product["id"], index) not in saved and not str(offer.get("image") or "").startswith("/media/products/"):
                missing_deals.append(product["id"])
    if missing_deals:
        raise SystemExit("priced deals still without a photo: " + ", ".join(missing_deals))
    text = original
    for product in data["products"]:
        for index, offer in enumerate(product["offers"]):
            done = saved.get((product["id"], index))
            if not done:
                continue
            text = patch_image(text, offer["url"], done[0], done[1], done[2])
    after_data = json.loads(text)
    after = [
        (p["id"], o.get("url"), o.get("price"), o.get("currency"), o.get("price_checked"), o.get("label"))
        for p in after_data["products"]
        for o in p["offers"]
    ]
    if before != after:
        raise SystemExit("refusing to write links.json: a price or URL changed")
    open(LINKS, "w", encoding="utf-8").write(text)
    print(f"saved {len(saved)} images, skipped {len(skipped)}")


if __name__ == "__main__":
    main()
