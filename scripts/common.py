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
    """Main ink colour of a note: the most common saturated hue (a plain average of all
    hues turns most paper notes into the same beige)."""
    import colorsys
    im = Image.open(path).convert("RGB")
    im.thumbnail((160, 160))
    bins = [[0.0, 0.0, 0.0, 0.0] for _ in range(24)]  # weight, sum sin/cos replaced by r,g,b sums
    for p in im.getdata():
        h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in p])
        if s < .22 or not (.2 < v < .97):
            continue
        if .06 < h < .14 and s < .45:   # skip cream / beige paper tone
            continue
        w = s * v
        bn = bins[int(h * 24) % 24]
        bn[0] += w; bn[1] += p[0] * w; bn[2] += p[1] * w; bn[3] += p[2] * w
    # merge neighbouring bins so a hue split across a boundary still wins
    score = [bins[i][0] + .5 * (bins[i - 1][0] + bins[(i + 1) % 24][0]) for i in range(24)]
    i = max(range(24), key=lambda i: score[i])
    if score[i] < 1:
        return "#8b8f93"
    tot = sum(bins[j][0] for j in (i - 1, i, (i + 1) % 24)) or 1
    r, g, b = [sum(bins[j][k] for j in (i - 1, i, (i + 1) % 24)) / tot / 255 for k in (1, 2, 3)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(max(l, .42), .55); s = max(s, .4)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#%02x%02x%02x" % tuple(int(x * 255) for x in (r, g, b))


COLOUR_ONLY = re.compile(r"underprint|multicolou?r printing|^(deep|dark|light|pale|bright)\b|on multishade", re.I)


def short(desc, limit=90):
    d = (desc or "").replace("\r", " ").replace("\n", ", ").strip()
    if COLOUR_ONLY.search(d.split(".")[0]):
        parts = [p for p in re.split(r"\.\s*", d) if p and not COLOUR_ONLY.search(p)]
        d = parts[0] if parts else ""
    d = re.sub(r"^(it has the image of|image of|portrait of)\s+", "", d, flags=re.I)
    d = re.split(r"\s+(?:to|at|on) (?:the )?(?:right|left|center|centre)\b|, issuer name|, face value", d)[0]
    d = re.sub(r"\s*\([^)]*\)", "", d)
    d = re.sub(r"\s+,", ",", re.sub(r",\s*,", ",", d))
    d = re.split(r"(?<=[.;])\s", d.strip())[0].strip(" .;,")
    d = d[:1].upper() + d[1:]
    return d if len(d) <= limit else d[:limit].rsplit(" ", 1)[0] + "…"


SPECIMEN_REQUIRED = ("GBP",)  # Bank of England: images showing >50% of a side must carry SPECIMEN


def stamp_specimen(path):
    """Bold grey SPECIMEN at 45 degrees through the centre, >=1/3 of the length and >=1/10 of the height."""
    from PIL import ImageDraw, ImageFont
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    size = max(12, int(h * 0.2))
    font = None
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(f, size); break
        except Exception:
            pass
    font = font or ImageFont.load_default()
    layer = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    text = "SPECIMEN"
    tw = d.textlength(text, font=font)
    d.text(((w * 2 - tw) / 2, (h * 2 - size) / 2), text, font=font, fill=(110, 110, 110, 210))
    layer = layer.rotate(45, resample=Image.BICUBIC)
    layer = layer.crop((w // 2, h // 2, w // 2 + w, h // 2 + h))
    Image.alpha_composite(im, layer).convert("RGB").save(path, "JPEG", quality=82)
