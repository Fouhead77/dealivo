import json, re
from datetime import datetime, timezone
from html import unescape
from urllib.request import Request, urlopen

SOURCES = [
    ("Carrefour", "https://www.carrefour.fr/catalogue"),
    ("E.Leclerc", "https://www.e.leclerc/prospectus"),
    ("Intermarché", "https://www.intermarche.com/enseigne/edito/operations-et-conditions"),
    ("Lidl", "https://www.lidl.fr/c/catalogues-en-ligne/s10017753"),
    ("ALDI", "https://www.aldi.fr/"),
    ("Magasins U", "https://www.coursesu.com/conditions-generales-offres.html"),
    ("Auchan", "https://www.auchan.fr/reductions/ep-reductions"),
]

PRICE = re.compile(r"(?<!\d)(\d{1,4}[,.]\d{2})\s*€")
OLD_PRICE = re.compile(r"(?:au lieu de|avant|ancien prix|prix habituel)\s*:?\s*(\d{1,4}[,.]\d{2})\s*€", re.I)
PERCENT = re.compile(r"(?:-|−)\s*(\d{1,2})\s*%")


def fetch(url):
    req = Request(url, headers={"User-Agent": "DealivoBot/1.0 (+https://dealivo.netlify.app)"})
    with urlopen(req, timeout=25) as r:
        return r.read(1200000).decode("utf-8", "ignore")


def clean(value):
    value = unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def candidate_from_context(store, source, context):
    current = PRICE.search(context)
    if not current:
        return None
    old = OLD_PRICE.search(context)
    pct = PERCENT.search(context)
    if not old and not pct:
        return None
    current_price = float(current.group(1).replace(',', '.'))
    old_price = float(old.group(1).replace(',', '.')) if old else None
    discount_pct = int(pct.group(1)) if pct else None
    if old_price and old_price > current_price:
        computed = round((1 - current_price / old_price) * 100)
        if discount_pct is None or abs(computed - discount_pct) <= 2:
            discount_pct = computed
        else:
            return None
    if discount_pct is None:
        return None
    title = context[:180]
    return {
        "store": store,
        "title": title,
        "price": current_price,
        "oldPrice": old_price,
        "discountPercent": discount_pct,
        "source": source,
        "verifiedBySource": True,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }


def extract(store, source):
    try:
        body = fetch(source)
    except Exception as exc:
        return {"store": store, "source": source, "reachable": False, "error": str(exc)[:180], "products": []}
    text = clean(body)
    products, seen = [], set()
    for match in PRICE.finditer(text):
        context = text[max(0, match.start()-350):min(len(text), match.end()+350)]
        item = candidate_from_context(store, source, context)
        if not item:
            continue
        key = (item["title"], item["price"], item["discountPercent"])
        if key in seen:
            continue
        seen.add(key)
        products.append(item)
        if len(products) >= 40:
            break
    return {"store": store, "source": source, "reachable": True, "products": products}


def main():
    payload = {"updatedAt": datetime.now(timezone.utc).isoformat(), "policy": "Product deals require an explicit current price plus a source-documented discount. No inferred old prices.", "sources": []}
    for store, source in SOURCES:
        payload["sources"].append(extract(store, source))
    with open("data/product-deals.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("Product deal extraction complete")


if __name__ == "__main__":
    main()
