# SunglassDealsDaily

Static sunglass deal pages for famous models (Ray-Ban Wayfarer, Aviator, Oakley Holbrook, Costa fishing frames, Persol 714, and others). One product page per model: the price and the buy button sit above the photo. Built by Amin Peracha.

A price is stored only when that colorway's public merchant page showed the number. Otherwise the button says **Check today's price**. There are no star ratings and no invented reviews.

## Where links live

Every outbound URL is in `data/links.json`, on the product. Merchants, with CJ applications pending:

| Store | CJ advertiser |
| --- | --- |
| Ray-Ban US | 3175074 |
| Oakley US | 1463156 |
| Sunglass Hut US | 4025749 |
| Costa Del Mar | 5626771 |

`cj.click_base` is null, so the site links to the merchant's own product page with no tracking parameters. After a program is approved, set `click_base` to that advertiser's CJ click URL. The build wraps the plain product URL and adds a sid:

`{pagetype}-{slug}-{placement}`

Placements are `cta`, `table`, `grid`, and `also`. The sid uses only `a-z`, `0-9`, `_`, and `-`, and it is at most 64 characters. Scripts never request a tracking URL.

## Prices from a CJ feed later

`scripts/apply_feed.py` reads a local JSON file. It does not call the network. A row matches `merchants[].cj.advertiser_id` plus `offers[].sku`. A row with no price leaves the stored price alone.

```json
[{"advertiser_id": "1463156", "sku": "OO9102", "price": 174.00, "currency": "USD"}]
```

```bash
python3 scripts/apply_feed.py data/cj-feed.json
```

## Build

The default build is the custom domain, with no path prefix:

```bash
python3 scripts/build.py
python3 scripts/validate.py
```

`SITE_URL` defaults to `https://sunglassdealsdaily.com` and `PATH_PREFIX` defaults to empty. Canonicals, the sitemap, robots, Open Graph URLs, and internal links use that host.

Local preview:

```bash
python3 scripts/build.py
python3 -m http.server -d site 8765
```

Then open `http://127.0.0.1:8765/`.

## Deploy

`.github/workflows/pages.yml` builds `site/` with `SITE_URL=https://sunglassdealsdaily.com` and an empty `PATH_PREFIX`, then deploys with GitHub Actions. The custom domain is set in the repository's Pages settings. The workflow does not write a CNAME file.
