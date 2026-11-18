#!/usr/bin/env python3
"""Fill in missing banknote photos. Order per note: issuing bank -> Numista -> Wikimedia Commons.

- Bank: direct image URLs listed in data/bank_sources.json, e.g.
  {"USD-1": {"f": "https://...", "b": "https://...", "bank": "U.S. Currency Education Program",
             "url": "https://...", "license": "Official image"}}
- Numista: needs NUMISTA_KEY. Picks are cached in data/numista_cache.json, so a note is only
  searched once; only openly licensed (Creative Commons / public domain) photos are used.
- Wikimedia Commons: free, no key; only files whose name matches the denomination, side and a
  recent year, with an open licence.
Photos are saved as img/<CODE>-<denomination>-<f|b>.jpg and credited in data/credits.json.
"""
import json, os, re, sys, urllib.parse, urllib.request
from common import *

BUDGET = int(os.environ.get("NUMISTA_BUDGET", "400"))
CUR_YEAR = int(os.environ.get("CUR_YEAR", __import__("datetime").date.today().year))


def have(k):
    return all(os.path.exists(os.path.join(IMG, f"{k}-{s}.jpg")) for s in "fb")


def from_bank(k, src, credits):
    ok = False
    for s in "fb":
        if src.get(s):
            try:
                download(src[s], os.path.join(IMG, f"{k}-{s}.jpg"), referer=src.get("url"))
                ok = True
            except Exception as e:
                print("  bank failed", k, s, e)
    if ok:
        cr = {"author": src.get("bank"), "license": src.get("license", "Official image"), "license_url": src.get("url")}
        credits[k] = {"source": "bank", "bank": src.get("bank"), "url": src.get("url") or src.get("f"), "f": cr, "b": cr}
    return ok


def numista_find(nm, c, denom, front, back, cache):
    known = cache.setdefault("_issuers", {})
    codes = [known[c["code"]]] if c["code"] in known else ISSUERS.get(c["code"], [])
    cands = []
    for code in codes:
        res = nm.get("/types", issuer=code, category="banknote", q=str(denom), count=50, page=1)
        pool = res.get("types", [])
        pages = -(-res.get("count", 0) // 50)
        for pg in sorted({pages, pages - 1} - {0, 1}, reverse=True):
            pool += nm.get("/types", issuer=code, category="banknote", q=str(denom), count=50, page=pg).get("types", [])
        t = [x for x in pool if lead_num(x["title"]) == denom
             and (x.get("issuer") or {}).get("code") == code
             and "circulat" in ((x.get("object_type") or {}).get("name", "")).lower()
             and (x.get("min_year") or 0) <= CUR_YEAR and (x.get("max_year") or x.get("min_year") or 0) >= 1990]
        if t:
            known[c["code"]] = code
            cands = t
            break
    if not cands:
        return None
    cands.sort(key=lambda x: (x.get("max_year") or 0, x.get("min_year") or 0), reverse=True)
    kw = {w for s in (front, back) for w in re.split(r"[^\w]+", norm(s)) if len(w) > 3}
    best, best_score = None, -1
    for x in cands[:2]:
        d = nm.get(f'/types/{x["id"]}')
        text = norm(" ".join([d.get("title", ""), (d.get("obverse") or {}).get("description", ""),
                              (d.get("reverse") or {}).get("description", "")]))
        score = sum(1 for w in kw if w in text)
        if score > best_score:
            best, best_score = d, score
        if score >= 2:
            break
    return Numista.pick_from(best, best_score)


def from_numista(pick, k, credits):
    if not pick or pick.get("none"):
        return False
    ref = f'https://en.numista.com/{pick["id"]}'
    ok = False
    for s, side in (("f", "obverse"), ("b", "reverse")):
        p = pick.get(side) or {}
        if p.get("picture") and OK_LICENSE.match(p.get("license") or ""):
            try:
                download(p["picture"], os.path.join(IMG, f"{k}-{s}.jpg"), referer=ref)
                ok = True
            except Exception as e:
                print("  numista download failed", k, s, e)
    if ok:
        credits[k] = {"source": "numista", "id": pick["id"], "title": pick["title"], "url": ref,
                      "f": {x: pick["obverse"].get(x) for x in ("author", "license", "license_url")},
                      "b": {x: pick["reverse"].get(x) for x in ("author", "license", "license_url")}}
    return ok


def commons(query):
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": query,
              "gsrnamespace": 6, "gsrlimit": 30, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 900}
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as f:
        return (json.load(f).get("query") or {}).get("pages", {}).values()


def from_wikimedia(c, denom, k, credits):
    pages = list(commons(f'{c["country"]} {denom} {c["cur"]} banknote'))
    min_year = c.get("year", CUR_YEAR) - 10
    found = {}
    for p in pages:
        title = norm(p.get("title", ""))
        flat = title.replace(",", "").replace(".", "").replace(" ", "_")
        if not re.search(rf"(^|[^\d]){denom}([^\d]|$)", flat):
            continue
        years = [int(y) for y in re.findall(r"(?:19|20)\d\d", title)]
        if not years or max(years) < min_year:
            continue
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        if not OK_LICENSE.match(lic):
            continue
        side = "f" if re.search(r"obverse|front|anverso|recto", title) else "b" if re.search(r"reverse|back|reverso|verso", title) else None
        if side and side not in found:
            artist = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip()
            found[side] = {"img": info.get("thumburl") or info.get("url"), "page": info.get("descriptionurl"),
                           "author": artist[:80] or "Wikimedia Commons contributor", "license": lic,
                           "license_url": (meta.get("LicenseUrl") or {}).get("value")}
    if not found:
        return False
    for s, v in found.items():
        download(v["img"], os.path.join(IMG, f"{k}-{s}.jpg"))
    first = found.get("f") or found.get("b")
    credits[k] = {"source": "wikimedia", "url": first["page"],
                  "f": {x: found["f"][x] for x in ("author", "license", "license_url")} if "f" in found else None,
                  "b": {x: found["b"][x] for x in ("author", "license", "license_url")} if "b" in found else None}
    return True


def main():
    os.makedirs(IMG, exist_ok=True)
    notes = load("notes.json", [])
    cache = load("numista_cache.json", {})
    credits = load("credits.json", {})
    banks = load("bank_sources.json", {})
    nm = Numista(os.environ.get("NUMISTA_KEY"), BUDGET)
    added = []
    for c in notes:
        for n in c["notes"]:
            k = f'{c["code"]}-{n[0]}'
            if have(k) and k in credits:
                continue
            try:
                if k in banks and from_bank(k, banks[k], credits):
                    added.append(f"{k} (bank)"); continue
                if nm.key:
                    if k not in cache:
                        cache[k] = numista_find(nm, c, n[0], n[2], n[3], cache) or {"none": True}
                    if from_numista(cache[k], k, credits):
                        added.append(f"{k} (Numista)"); continue
                if from_wikimedia(c, n[0], k, credits):
                    added.append(f"{k} (Wikimedia)"); continue
            except RuntimeError as e:
                print("STOP:", e); break
            except Exception as e:
                print("  error", k, e)
    save("numista_cache.json", cache)
    save("credits.json", credits)
    print(f"photos added: {len(added)}; Numista requests used: {nm.used}")
    with open(os.path.join(DATA, "last_photos.txt"), "w") as f:
        f.write("\n".join(added))


if __name__ == "__main__":
    main()
