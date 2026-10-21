import json, re
from datetime import date, datetime, timezone
from urllib.request import Request, urlopen
from html import unescape

SOURCES = {
    "Carrefour": "https://www.carrefour.fr/",
    "E.Leclerc": "https://www.e.leclerc/",
    "Intermarché": "https://www.intermarche.com/",
    "Lidl": "https://www.lidl.fr/",
    "ALDI": "https://www.aldi.fr/",
    "Magasins U": "https://www.coursesu.com/",
    "Auchan": "https://www.auchan.fr/",
    "Monoprix": "https://www.monoprix.fr/",
    "Casino": "https://www.casino.fr/",
}

PRICE_RE = re.compile(r"(?<!\d)(\d{1,4}[,.]\d{2})\s*€")
DISCOUNT_RE = re.compile(r"(?:-|−)\s*(\d{1,2})\s*%")

def fetch(url):
    req = Request(url, headers={"User-Agent": "DealivoBot/1.0"})
    with urlopen(req, timeout=20) as r:
        return r.read(800000).decode("utf-8", "ignore")

def clean(text):
    text = unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()

def extract_generic(store, url):
    try:
        body = fetch(url)
    except Exception as exc:
        return {"store": store, "source": url, "reachable": False, "error": str(exc)[:180], "offers": []}

    text = clean(body)
    offers = []
    seen = set()
    for match in PRICE_RE.finditer(text):
        start = max(0, match.start() - 220)
        end = min(len(text), match.end() + 220)
        context = text[start:end]
        discount = DISCOUNT_RE.search(context)
        if not discount:
            continue
        key = (context[:140], match.group(1))
        if key in seen:
            continue
        seen.add(key)
        offers.append({
            "store": store,
            "title": context[:180],
            "price": float(match.group(1).replace(',', '.')),
            "discountPercent": int(discount.group(1)),
            "source": url,
            "verifiedBySource": True,
            "checkedAt": datetime.now(timezone.utc).isoformat(),
        })
        if len(offers) >= 25:
            break
    return {"store": store, "source": url, "reachable": True, "offers": offers}

def main():
    result = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "policy": "Only source-documented offers are eligible. Generic extraction never creates coupons or old prices.",
        "sources": [],
    }
    for store, url in SOURCES.items():
        result["sources"].append(extract_generic(store, url))
    with open("data/source-offers.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    total = sum(len(s["offers"]) for s in result["sources"])
    print(f"Extracted {total} source-documented discount candidates")

if __name__ == "__main__":
    main()
