#!/usr/bin/env python3
"""Build the site into _site/: index.html (template + data), world.json and img/."""
import datetime, json, os, re, shutil
from common import ROOT, DATA, IMG, load, dominant_colour

OUT = os.path.join(ROOT, "_site")


def main():
    notes = load("notes.json", [])
    credits = load("credits.json", {})
    img, changed = {}, False
    for c in notes:
        for n in c["notes"]:
            k = f'{c["code"]}-{n[0]}'
            sides = {s: f"img/{k}-{s}.jpg" for s in "fb" if os.path.exists(os.path.join(IMG, f"{k}-{s}.jpg"))}
            sides.update({s + "l": f"img/lg/{k}-{s}.jpg" for s in "fb" if os.path.exists(os.path.join(IMG, "lg", f"{k}-{s}.jpg"))})
            if sides:
                img[k] = sides
                if n[1] in ("#777777", "#000000") and "f" in sides:  # colour for newly added notes
                    n[1] = dominant_colour(os.path.join(IMG, f"{k}-f.jpg")); changed = True
    if changed:
        json.dump(notes, open(os.path.join(DATA, "notes.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    verified = load("meta.json", {}).get("verified") or datetime.date.today().strftime("%-d %B %Y")
    t = open(os.path.join(ROOT, "template.html"), encoding="utf-8").read()
    t = re.sub(r'const VERIFIED = "[^"]*";', f'const VERIFIED = "{verified}";', t)
    t = t.replace("/*DATA*/", "const D = " + json.dumps(notes, ensure_ascii=False) + ";")
    t = t.replace("/*IMG*/{}", json.dumps(img))
    t = t.replace("/*CREDITS*/{}", json.dumps({k: v for k, v in credits.items() if k in img}, ensure_ascii=False))
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(t)
    shutil.copy(os.path.join(DATA, "world.json"), OUT)
    shutil.copytree(IMG, os.path.join(OUT, "img"))
    print(f"built _site: {len(img)} notes with photos")


if __name__ == "__main__":
    main()
