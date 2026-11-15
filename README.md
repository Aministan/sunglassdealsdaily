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

GitHub Pages project URL (the default):

```bash
python3 scripts/build.py
python3 scripts/validate.py
```

Custom domain later, still without a CNAME file in the repo until you add one on purpose:

```bash
SITE_URL=https://sunglassdealsdaily.com PATH_PREFIX= python3 scripts/build.py
```

Local preview of the project-page paths:

```bash
python3 scripts/build.py
rm -rf /tmp/www && mkdir -p /tmp/www
cp -a site /tmp/www/sunglassdealsdaily
python3 -m http.server -d /tmp/www 8765
```

Then open `http://127.0.0.1:8765/sunglassdealsdaily/`.

## Deploy

`.github/workflows/pages.yml` builds `site/` and deploys with GitHub Actions. `actions/configure-pages` runs with `enablement: true`, and the build uses that action's `origin` and `base_path`, so a custom domain set in the Pages settings is picked up without a code change. The workflow does not write a CNAME file.
