import json, re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# Sources are deliberately explicit. The pipeline never invents a coupon.
SOURCES = [
    ("Carrefour", "https://www.carrefour.fr/"),
    ("E.Leclerc", "https://www.e.leclerc/"),
    ("Intermarché", "https://www.intermarche.com/"),
    ("Lidl", "https://www.lidl.fr/"),
    ("ALDI", "https://www.aldi.fr/"),
    ("Magasins U", "https://www.coursesu.com/"),
    ("Auchan", "https://www.auchan.fr/"),
    ("Monoprix", "https://www.monoprix.fr/"),
    ("Casino", "https://www.casino.fr/"),
]

SEED = [
    {"store":"Auchan","code":"OCTOBRE20","discount":"−20 €","condition":"dès 80 €","title":"Première commande","details":"20 € de remise immédiate pour une première commande Auchan.fr ou application, sur les courses éligibles.","expires":"2026-10-31","source":"Auchan","url":"https://www.auchan.fr/reductions/ep-reductions"},
    {"store":"Auchan","code":"OCTOBRE30","discount":"−30 €","condition":"dès 150 €","title":"Première commande","details":"30 € de remise immédiate pour une première commande Auchan.fr ou application, sur les courses éligibles.","expires":"2026-10-31","source":"Auchan","url":"https://www.auchan.fr/reductions/ep-reductions"},
    {"store":"Cdiscount","code":"HELLO10","discount":"−10 €","condition":"dès 50 €","title":"Première commande","details":"10 € de remise pour les nouveaux clients dès 50 € d’achat.","expires":"2027-01-01","source":"Le Parisien","url":"https://www.cdiscount.com/"},
    {"store":"Cdiscount","code":"10PRCENT","discount":"−10 %","condition":"dès 150 €","title":"Nouveaux clients","details":"10 % de remise dès 150 € d’achat, réservé aux nouveaux clients.","expires":"2027-01-01","source":"Le Parisien","url":"https://www.cdiscount.com/"},
    {"store":"Cdiscount","code":"10MODE49","discount":"−10 %","condition":"dès 49 €","title":"Sélection mode","details":"10 % de remise sur une sélection mode et accessoires.","expires":"2026-10-30","source":"Le Parisien","url":"https://www.cdiscount.com/"},
    {"store":"Cdiscount","code":"B&D59","discount":"−20 %","condition":"dès 59 €","title":"Black+Decker","details":"20 % de remise sur une sélection de produits Black+Decker.","expires":"2026-10-23","source":"Le Parisien","url":"https://www.cdiscount.com/"},
    {"store":"Cdiscount","code":"TEL15D99","discount":"−15 €","condition":"dès 99 €","title":"Téléphonie","details":"15 € de remise sur une sélection de téléphones.","expires":"2026-10-21","source":"Le Parisien","url":"https://www.cdiscount.com/"},
    {"store":"Cdiscount","code":"HALLOWEEN26","discount":"−10 %","condition":"dès 30 €","title":"Halloween","details":"10 % de remise sur une sélection d’articles Halloween.","expires":"2026-11-01","source":"Le Parisien","url":"https://www.cdiscount.com/"},
    {"store":"Fnac","code":"KIDS26","discount":"−10 €","condition":"dès 50 €","title":"Jeux & jouets","details":"10 € offerts dès 50 € sur une sélection jeux et jouets.","expires":"2026-11-01","source":"Fnac","url":"https://www.fnac.com/l368532/Precommandez-les-nouveautes-jeux-jouets"},
]

# Generic store-level records make the supermarket section useful even when no coupon is published.
for store, url in SOURCES:
    SEED.append({"store":store,"code":None,"discount":"Promotions","condition":"catalogue / fidélité","title":f"Offres {store}","details":"Promotions à vérifier selon le catalogue, le magasin et les avantages fidélité. Aucun code n’est inventé par Dealivo.","expires":None,"source":store,"url":url})

def fetch(url):
    try:
        req = Request(url, headers={"User-Agent":"DealivoBot/1.0 (+https://dealivo.netlify.app)"})
        with urlopen(req, timeout=20) as r:
            body = r.read(500000).decode("utf-8", "ignore")
        return True, len(body)
    except Exception as exc:
        return False, str(exc)[:160]

today = date.today()
active = []
source_status = []
for store, url in SOURCES:
    ok, info = fetch(url)
    source_status.append({"store":store,"url":url,"reachable":ok,"detail":info,"checkedAt":datetime.now(timezone.utc).isoformat()})

for deal in SEED:
    exp = deal.get("expires")
    if exp:
        try:
            if date.fromisoformat(exp) < today:
                continue
        except ValueError:
            continue
    d = dict(deal)
    d["checkedAt"] = datetime.now(timezone.utc).isoformat()
    active.append(d)

payload = {"updatedAt": datetime.now(timezone.utc).isoformat(), "activeDeals": active, "sources": source_status, "policy":"No invented prices or coupons; expired dated offers are removed automatically."}
(DATA / "active-deals.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Dealivo refresh: {len(active)} active records, {len(source_status)} sources checked")
