#!/usr/bin/env python3
"""Look for newly issued banknotes on Numista and update data/notes.json.

For every currency already on the site, asks Numista for standard circulation notes dated this
year and last year (about 2 requests per currency). Then:
- a new design for a denomination already listed replaces the old one (subjects taken from
  Numista's descriptions, old photo removed so fetch_images.py downloads the new one);
- a brand-new denomination is added;
- a continuing design we had no photo for is linked so its photo can be downloaded.
Commemorative notes are ignored. No new countries are ever added. Withdrawn notes are not
detected automatically. A summary is written to data/last_changes.md.
"""
import datetime, os
from common import *

Y = datetime.date.today().year
BUDGET = int(os.environ.get("NUMISTA_BUDGET", "400"))


def main():
    nm = Numista(os.environ.get("NUMISTA_KEY"), BUDGET)
    if not nm.key:
        print("No NUMISTA_KEY; skipping new-note check"); return
    notes = load("notes.json", [])
    cache = load("numista_cache.json", {})
    ignored = set(load("ignored_types.json", []))
    known_ids = {v.get("id") for k, v in cache.items() if not k.startswith("_") and isinstance(v, dict)} | ignored
    issuers = cache.setdefault("_issuers", {})
    changes = []
    try:
        for c in notes:
            code = issuers.get(c["code"]) or (ISSUERS.get(c["code"]) or [None])[0]
            if not code:
                continue
            seen = {}
            for yr in (Y, Y - 1):
                for t in nm.get("/types", issuer=code, category="banknote", date=yr, count=50).get("types", []):
                    seen[t["id"]] = t
            for t in seen.values():
                if t["id"] in known_ids:
                    continue
                if (t.get("issuer") or {}).get("code") != code:
                    continue
                if "standard circulation" not in ((t.get("object_type") or {}).get("name", "")).lower():
                    continue
                denom = lead_num(t["title"])
                if not denom or any(w in norm(t["title"]) for w in EXCLUDED_WORDS):
                    continue
                k = f'{c["code"]}-{denom}'
                existing = next((n for n in c["notes"] if n[0] == denom), None)
                old = cache.get(k) or {}
                old_years = old.get("years") or [0, 0]
                is_new_design = (t.get("min_year") or 0) >= Y - 1 and (t.get("min_year") or 0) > (old_years[0] or 0)
                if existing and not is_new_design and old.get("id") and not old.get("none"):
                    continue  # just another dated printing of a design we already have
                d = nm.get(f'/types/{t["id"]}')
                pick = Numista.pick_from(d, 9)
                cache[k] = pick
                known_ids.add(t["id"])
                front = short(pick["obverse"]["description"]) or (existing[2] if existing else "See Numista")
                back = short(pick["reverse"]["description"]) or (existing[3] if existing else "See Numista")
                for s in "fb":
                    p = os.path.join(IMG, f"{k}-{s}.jpg")
                    if os.path.exists(p) and (is_new_design or not existing):
                        os.remove(p)
                if existing and is_new_design:
                    existing[2], existing[3] = front, back
                    c["year"] = max(c.get("year", 0), t.get("min_year") or 0)
                    changes.append(f'- **{c["country"]} {denom}**: new design ({t["title"]}, {t.get("min_year")}) - <https://en.numista.com/{t["id"]}>')
                elif not existing:
                    c["notes"].append([denom, "#777777", front, back])
                    c["notes"].sort(key=lambda n: n[0])
                    c["year"] = max(c.get("year", 0), t.get("min_year") or 0)
                    changes.append(f'- **{c["country"]} {denom}**: new denomination added ({t["title"]}) - <https://en.numista.com/{t["id"]}>')
                else:
                    changes.append(f'- {c["country"]} {denom}: linked to Numista entry {t["id"]} for its photo')
    except RuntimeError as e:
        print("STOP:", e)
    save("notes.json", notes)
    save("numista_cache.json", cache)
    save("meta.json", {"verified": datetime.date.today().strftime("%-d %B %Y")})
    with open(os.path.join(DATA, "last_changes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(changes))
    print(f"{len(changes)} change(s); Numista requests used: {nm.used}")


if __name__ == "__main__":
    main()
