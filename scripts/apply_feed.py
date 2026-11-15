#!/usr/bin/env python3
"""Fill offers[].price from a local CJ product-feed file.

Usage: python3 scripts/apply_feed.py data/cj-feed.json

Each row is an object with advertiser_id, sku, price, and optional currency and url.
A row matches an offer when the merchant's cj.advertiser_id equals advertiser_id
and offers[].sku equals sku. A null or missing price does not change the stored
price. This script does not request any URL. A feed url is copied only when it
is a plain https URL on the same host as the offer already stored.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import links

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS = os.path.join(ROOT, "data", "links.json")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 scripts/apply_feed.py data/cj-feed.json")
    feed_path = sys.argv[1]
    data = json.load(open(LINKS, encoding="utf-8"))
    rows = json.load(open(feed_path, encoding="utf-8"))
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("products") or []
    by_key = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = (str(row.get("advertiser_id") or ""), str(row.get("sku") or ""))
        if key[0] and key[1]:
            by_key[key] = row
    changed = 0
    for product in data["products"]:
        merchant = data["merchants"][product["merchant"]]
        advertiser = str((merchant.get("cj") or {}).get("advertiser_id") or "")
        for offer in product["offers"]:
            row = by_key.get((advertiser, str(offer.get("sku") or "")))
            if not row:
                continue
            price = row.get("price")
            if price is None or price == "":
                print(f"skip {product['id']} {offer.get('sku')}: feed has no price")
                continue
            try:
                price = float(price)
            except (TypeError, ValueError):
                print(f"skip {product['id']} {offer.get('sku')}: price is not a number")
                continue
            if price <= 0:
                print(f"skip {product['id']} {offer.get('sku')}: price is not positive")
                continue
            offer["price"] = round(price, 2)
            offer["currency"] = row.get("currency") or "USD"
            offer["price_source"] = "cj-feed"
            url = row.get("url")
            if isinstance(url, str) and url.startswith("https://") and not links.is_tracking_url(url) and not links.is_blocked_url(url):
                if links.host_of(url) == links.host_of(offer["url"]):
                    offer["url"] = url
            changed += 1
            print(f"price {product['id']} {offer.get('sku')} {offer['price']}")
    json.dump(data, open(LINKS, "w", encoding="utf-8"), indent=2)
    open(LINKS, "a", encoding="utf-8").write("\n")
    print(f"updated {changed} offers")


if __name__ == "__main__":
    main()
