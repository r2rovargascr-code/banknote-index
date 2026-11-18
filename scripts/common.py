"""Shared helpers: data files, Numista API, image download."""
import io, json, os, re, time, unicodedata, urllib.parse, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
IMG = os.path.join(ROOT, "img")
UA = "BanknoteIndexBot/1.0 (https://github.com/r2rovargascr-code/banknote-index)"
OK_LICENSE = re.compile(r"^(CC|Public domain|Domaine public|PD)", re.I)

# Numista issuer codes per currency (first one that returns results is remembered in the cache).
ISSUERS = {
 "USD": ["united-states", "etats-unis"], "EUR": ["zone_euro"], "GBP": ["england"],
 "JPY": ["japon", "japan"], "CNY": ["china", "chine"], "INR": ["inde"], "CAD": ["canada"],
 "AUD": ["australie"], "NZD": ["nouvelle-zelande"], "CHF": ["suisse", "switzerland"], "SEK": ["suede"],
 "NOK": ["norvege"], "DKK": ["danemark"], "KRW": ["coree_du_sud"], "SGD": ["singapour"],
 "MXN": ["mexique", "mexico"], "BRL": ["bresil"], "ZAR": ["afrique_du_sud"], "TRY": ["turquie"],
 "THB": ["thailande"], "PHP": ["philippines"], "IDR": ["indonesie", "indonesia"],
 "VND": ["viet_nam"], "MYR": ["malaisie"], "KES": ["kenya"], "TWD": ["taiwan"], "COP": ["colombie"],
 "PRB": ["transnistrie"], "SLS": ["somaliland"],
}
EXCLUDED_WORDS = ("israel", "shekel")  # never added to the site


def load(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save(name, obj):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


class Numista:
    API = "https://api.numista.com/v3"

    def __init__(self, key, budget):
        self.key, self.budget, self.used = key, budget, 0

    def get(self, path, **params):
        if not self.key:
            raise RuntimeError("no NUMISTA_KEY")
        if self.used >= self.budget:
            raise RuntimeError("Numista request budget reached")
        self.used += 1
        url = f"{self.API}{path}?{urllib.parse.urlencode({**params, 'lang': 'en'})}"
        req = urllib.request.Request(url, headers={"Numista-API-Key": self.key, "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as f:
            time.sleep(0.4)
            return json.load(f)

    @staticmethod
    def pick_from(d, score=0):
        def side(s):
            s = d.get(s) or {}
            return {"picture": s.get("picture"), "author": s.get("picture_copyright"),
                    "license": s.get("picture_license_name"), "license_url": s.get("picture_license_url"),
                    "description": s.get("description") or ""}
        return {"id": d["id"], "title": d["title"], "years": [d.get("min_year"), d.get("max_year")],
                "issuer": (d.get("issuer") or {}).get("code"), "score": score,
                "obverse": side("obverse"), "reverse": side("reverse")}


def norm(s):
    return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()


def lead_num(title):
    m = re.match(r"^\s*(\d[\d\s,.  ']*)", title or "")
    return int(re.sub(r"\D", "", m.group(1))) if m else None


def download(url, out, referer=None, max_side=640):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; " + UA + ")"}
    if referer:
        headers["Referer"] = referer
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as f:
        data = f.read()
    im = Image.open(io.BytesIO(data)).convert("RGB")
    if im.height > im.width * 1.1:  # vertical note: show it horizontally
        im = im.rotate(90, expand=True)
    lg = os.path.join(os.path.dirname(out), "lg", os.path.basename(out))
    os.makedirs(os.path.dirname(lg), exist_ok=True)
    big = im.copy()
    big.thumbnail((1600, 1600))
    big.save(lg, "JPEG", quality=82, optimize=True, progressive=True)
    im.thumbnail((max_side, max_side))
    im.save(out, "JPEG", quality=78, optimize=True, progressive=True)
    time.sleep(0.3)


def dominant_colour(path):
    import colorsys
    im = Image.open(path).convert("RGB")
    im.thumbnail((160, 160))
    px = list(im.getdata())
    sel = [p for p in px if (lambda h, s, v: s > .18 and .25 < v < .97)(*colorsys.rgb_to_hsv(*[x / 255 for x in p]))] or px
    r, g, b = [sum(p[i] for p in sel) / len(sel) / 255 for i in range(3)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(max(l, .42), .55)
    s = max(s, .35) if s > .08 else s
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#%02x%02x%02x" % tuple(int(x * 255) for x in (r, g, b))


def short(desc, limit=90):
    d = re.split(r"(?<=[.;])\s", (desc or "").strip())[0].strip(" .;")
    return d if len(d) <= limit else d[:limit].rsplit(" ", 1)[0] + "…"
