#!/usr/bin/env python3
"""Add countries to data/notes.json from Numista's catalogue.

Usage: NUMISTA_KEY=... python3 scripts/add_countries.py [ISO2 ISO2 ...]
With no arguments, adds every country in COUNTRIES that is not on the site yet.
For each country it finds the standard circulation notes dated in recent years, keeps the newest
design of each denomination, and takes the subjects and material from Numista's descriptions.
Uses roughly 5-10 Numista requests per country. Israel is never added.
"""
import datetime, json, os, sys, urllib.request
from common import *

Y = datetime.date.today().year
BUDGET = int(os.environ.get("NUMISTA_BUDGET", "900"))

# iso2, Numista issuer name, display name, currency, symbol, region, map ids (ISO numeric)
COUNTRIES = [
 ("AR","Argentina","Argentina","Argentine peso","$","Americas"),("CL","Chile","Chile","Chilean peso","$","Americas"),
 ("PE","Peru","Peru","Peruvian sol","S/","Americas"),("UY","Uruguay","Uruguay","Uruguayan peso","$","Americas"),
 ("PY","Paraguay","Paraguay","Paraguayan guaraní","₲","Americas"),("BO","Bolivia","Bolivia","Boliviano","Bs","Americas"),
 ("VE","Venezuela","Venezuela","Venezuelan bolívar","Bs.","Americas"),("CR","Costa Rica","Costa Rica","Costa Rican colón","₡","Americas"),
 ("GT","Guatemala","Guatemala","Guatemalan quetzal","Q","Americas"),("HN","Honduras","Honduras","Honduran lempira","L","Americas"),
 ("NI","Nicaragua","Nicaragua","Nicaraguan córdoba","C$","Americas"),("DO","Dominican Republic","Dominican Republic","Dominican peso","RD$","Americas"),
 ("CU","Cuba","Cuba","Cuban peso","$","Americas"),("JM","Jamaica","Jamaica","Jamaican dollar","J$","Americas"),
 ("TT","Trinidad and Tobago","Trinidad and Tobago","Trinidad and Tobago dollar","TT$","Americas"),("BS","Bahamas","Bahamas","Bahamian dollar","B$","Americas"),
 ("BM","Bermuda","Bermuda","Bermudian dollar","$","Americas"),("KY","Cayman Islands","Cayman Islands","Cayman Islands dollar","CI$","Americas"),
 ("HT","Haiti","Haiti","Haitian gourde","G","Americas"),("BZ","Belize","Belize","Belize dollar","BZ$","Americas"),
 ("GY","Guyana","Guyana","Guyanese dollar","G$","Americas"),("SR","Suriname","Suriname","Surinamese dollar","$","Americas"),
 ("BB","Barbados","Barbados","Barbadian dollar","Bds$","Americas"),("AW","Aruba","Aruba","Aruban florin","ƒ","Americas"),
 ("PL","Poland","Poland","Polish złoty","zł","Europe"),("CZ","Czech Republic","Czechia","Czech koruna","Kč","Europe"),
 ("HU","Hungary","Hungary","Hungarian forint","Ft","Europe"),("RO","Romania","Romania","Romanian leu","lei","Europe"),
 ("MD","Moldova","Moldova","Moldovan leu","L","Europe"),("UA","Ukraine","Ukraine","Ukrainian hryvnia","₴","Europe"),
 ("RU","Russia","Russia","Russian ruble","₽","Europe"),("BY","Belarus","Belarus","Belarusian ruble","Br","Europe"),
 ("RS","Serbia","Serbia","Serbian dinar","din.","Europe"),("MK","North Macedonia","North Macedonia","Macedonian denar","ден","Europe"),
 ("AL","Albania","Albania","Albanian lek","L","Europe"),("BA","Bosnia and Herzegovina","Bosnia and Herzegovina","Convertible mark","KM","Europe"),
 ("IS","Iceland","Iceland","Icelandic króna","kr","Europe"),("GE","Georgia","Georgia","Georgian lari","₾","Asia"),
 ("AM","Armenia","Armenia","Armenian dram","֏","Asia"),("AZ","Azerbaijan","Azerbaijan","Azerbaijani manat","₼","Asia"),
 ("HK","Hong Kong","Hong Kong","Hong Kong dollar","HK$","Asia"),("MO","Macau","Macau","Macanese pataca","MOP$","Asia"),
 ("PK","Pakistan","Pakistan","Pakistani rupee","₨","Asia"),("BD","Bangladesh","Bangladesh","Bangladeshi taka","৳","Asia"),
 ("LK","Sri Lanka","Sri Lanka","Sri Lankan rupee","Rs","Asia"),("NP","Nepal","Nepal","Nepalese rupee","रू","Asia"),
 ("BT","Bhutan","Bhutan","Bhutanese ngultrum","Nu.","Asia"),("MM","Myanmar","Myanmar","Myanmar kyat","K","Asia"),
 ("KH","Cambodia","Cambodia","Cambodian riel","៛","Asia"),("LA","Laos","Laos","Lao kip","₭","Asia"),
 ("MN","Mongolia","Mongolia","Mongolian tögrög","₮","Asia"),("KZ","Kazakhstan","Kazakhstan","Kazakhstani tenge","₸","Asia"),
 ("UZ","Uzbekistan","Uzbekistan","Uzbekistani som","so'm","Asia"),("KG","Kyrgyzstan","Kyrgyzstan","Kyrgyzstani som","с","Asia"),
 ("TJ","Tajikistan","Tajikistan","Tajikistani somoni","SM","Asia"),("TM","Turkmenistan","Turkmenistan","Turkmenistani manat","m","Asia"),
 ("AF","Afghanistan","Afghanistan","Afghan afghani","؋","Asia"),("BN","Brunei","Brunei","Brunei dollar","B$","Asia"),
 ("MV","Maldives","Maldives","Maldivian rufiyaa","Rf","Asia"),("KP","North Korea","North Korea","North Korean won","₩","Asia"),
 ("IR","Iran","Iran","Iranian rial","﷼","Middle East"),("IQ","Iraq","Iraq","Iraqi dinar","ع.د","Middle East"),
 ("SA","Saudi Arabia","Saudi Arabia","Saudi riyal","﷼","Middle East"),("AE","United Arab Emirates","United Arab Emirates","UAE dirham","د.إ","Middle East"),
 ("QA","Qatar","Qatar","Qatari riyal","﷼","Middle East"),("KW","Kuwait","Kuwait","Kuwaiti dinar","د.ك","Middle East"),
 ("BH","Bahrain","Bahrain","Bahraini dinar","BD","Middle East"),("OM","Oman","Oman","Omani rial","﷼","Middle East"),
 ("JO","Jordan","Jordan","Jordanian dinar","JD","Middle East"),("LB","Lebanon","Lebanon","Lebanese pound","ل.ل","Middle East"),
 ("SY","Syria","Syria","Syrian pound","£S","Middle East"),("YE","Yemen","Yemen","Yemeni rial","﷼","Middle East"),
 ("EG","Egypt","Egypt","Egyptian pound","E£","Africa"),("MA","Morocco","Morocco","Moroccan dirham","DH","Africa"),
 ("DZ","Algeria","Algeria","Algerian dinar","DA","Africa"),("TN","Tunisia","Tunisia","Tunisian dinar","DT","Africa"),
 ("LY","Libya","Libya","Libyan dinar","LD","Africa"),("NG","Nigeria","Nigeria","Nigerian naira","₦","Africa"),
 ("GH","Ghana","Ghana","Ghanaian cedi","GH₵","Africa"),("ET","Ethiopia","Ethiopia","Ethiopian birr","Br","Africa"),
 ("TZ","Tanzania","Tanzania","Tanzanian shilling","TSh","Africa"),("UG","Uganda","Uganda","Ugandan shilling","USh","Africa"),
 ("RW","Rwanda","Rwanda","Rwandan franc","FRw","Africa"),("BI","Burundi","Burundi","Burundian franc","FBu","Africa"),
 ("CD","Democratic Republic of the Congo","DR Congo","Congolese franc","FC","Africa"),("AO","Angola","Angola","Angolan kwanza","Kz","Africa"),
 ("ZM","Zambia","Zambia","Zambian kwacha","K","Africa"),("ZW","Zimbabwe","Zimbabwe","Zimbabwe Gold (ZiG)","ZiG","Africa"),
 ("MZ","Mozambique","Mozambique","Mozambican metical","MT","Africa"),("MW","Malawi","Malawi","Malawian kwacha","MK","Africa"),
 ("BW","Botswana","Botswana","Botswana pula","P","Africa"),("NA","Namibia","Namibia","Namibian dollar","N$","Africa"),
 ("LS","Lesotho","Lesotho","Lesotho loti","L","Africa"),("SZ","Eswatini","Eswatini","Swazi lilangeni","E","Africa"),
 ("MG","Madagascar","Madagascar","Malagasy ariary","Ar","Africa"),("MU","Mauritius","Mauritius","Mauritian rupee","₨","Africa"),
 ("SC","Seychelles","Seychelles","Seychellois rupee","SR","Africa"),("SD","Sudan","Sudan","Sudanese pound","£SD","Africa"),
 ("SS","South Sudan","South Sudan","South Sudanese pound","SSP","Africa"),("SO","Somalia","Somalia","Somali shilling","Sh.So.","Africa"),
 ("DJ","Djibouti","Djibouti","Djiboutian franc","Fdj","Africa"),("ER","Eritrea","Eritrea","Eritrean nakfa","Nfk","Africa"),
 ("GM","Gambia","Gambia","Gambian dalasi","D","Africa"),("GN","Guinea","Guinea","Guinean franc","FG","Africa"),
 ("SL","Sierra Leone","Sierra Leone","Sierra Leonean leone","Le","Africa"),("LR","Liberia","Liberia","Liberian dollar","L$","Africa"),
 ("CV","Cape Verde","Cape Verde","Cape Verdean escudo","Esc","Africa"),("ST","Sao Tome and Principe","São Tomé and Príncipe","São Tomé dobra","Db","Africa"),
 ("MR","Mauritania","Mauritania","Mauritanian ouguiya","UM","Africa"),("KM","Comoros","Comoros","Comorian franc","CF","Africa"),
 ("JE","Jersey","Jersey","Jersey pound","£","Europe"),("GG","Guernsey","Guernsey","Guernsey pound","£","Europe"),
 ("IM","Isle of Man","Isle of Man","Manx pound","£","Europe"),("GI","Gibraltar","Gibraltar","Gibraltar pound","£","Europe"),
 ("FK","Falkland Islands","Falkland Islands","Falkland Islands pound","£","Americas"),("SH","Saint Helena","Saint Helena","Saint Helena pound","£","Africa"),
 ("FO","Faroe Islands","Faroe Islands","Faroese króna","kr","Europe"),("CK","Cook Islands","Cook Islands","Cook Islands dollar","$","Oceania"),
 ("FJ","Fiji","Fiji","Fijian dollar","FJ$","Oceania"),("PG","Papua New Guinea","Papua New Guinea","Papua New Guinean kina","K","Oceania"),
 ("WS","Samoa","Samoa","Samoan tālā","WS$","Oceania"),("TO","Tonga","Tonga","Tongan paʻanga","T$","Oceania"),
 ("VU","Vanuatu","Vanuatu","Vanuatu vatu","VT","Oceania"),("SB","Solomon Islands","Solomon Islands","Solomon Islands dollar","SI$","Oceania"),
]
# Monetary unions: (code, display, currency, symbol, region, Numista issuer name, member ISO2 list)
UNIONS = [
 ("XOF","West African CFA franc zone","West African CFA franc","CFA","Africa","West African States",["BJ","BF","CI","GW","ML","NE","SN","TG"]),
 ("XAF","Central African CFA franc zone","Central African CFA franc","FCFA","Africa","Central African States",["CM","CF","TD","CG","GQ","GA"]),
 ("XCD","Eastern Caribbean","East Caribbean dollar","EC$","Americas","Eastern Caribbean States",["AG","DM","GD","KN","LC","VC","AI","MS"]),
 ("SCT","Scotland","Pound sterling (Scottish banknotes)","£","Europe","Scotland",[]),
 ("NIR","Northern Ireland","Pound sterling (Northern Ireland banknotes)","£","Europe","Northern Ireland",[]),
 ("XPF","CFP franc zone (French Pacific)","CFP franc","₣","Oceania","French Pacific Territories",["PF","NC","WF"]),
]


def numeric(iso2):
    try:
        import pycountry
        return pycountry.countries.get(alpha_2=iso2).numeric
    except Exception:
        return None


def issuer_candidates(name):
    issuers = load("_issuers_all.json", None)
    if issuers is None:
        return []
    n = norm(name)
    exact = [i["code"] for i in issuers if norm(i["name"]) == n and not i["code"].endswith("_section")]
    loose = [i["code"] for i in issuers if norm(i["name"]).startswith(n) and i["code"] not in exact and not i["code"].endswith("_section")]
    return exact + loose[:2]


def collect(nm, code, deep=False):
    types = {}
    if not deep:
        for yr in (Y, Y - 3, Y - 6):
            res = nm.get("/types", issuer=code, category="banknote", date=yr, count=50)
            for t in res.get("types", []):
                types[t["id"]] = t
    else:
        # newest catalogue entries (results come oldest first, so read the last pages)
        res = nm.get("/types", issuer=code, category="banknote", count=50, page=1)
        pages = -(-res.get("count", 0) // 50)
        pool = res.get("types", []) if pages <= 1 else []
        for pg in sorted({pages, pages - 1} - {0}, reverse=True):
            if pg == 1 and pool:
                continue
            pool += nm.get("/types", issuer=code, category="banknote", count=50, page=pg).get("types", [])
        for t in pool:
            types[t["id"]] = t
    keep = {}
    for t in types.values():
        if (t.get("issuer") or {}).get("code") != code:
            continue
        if "standard circulation" not in ((t.get("object_type") or {}).get("name", "")).lower():
            continue
        d = lead_num(t["title"])
        if not d:
            continue
        cur = keep.get(d)
        score = ((t.get("max_year") or t.get("min_year") or 0), (t.get("min_year") or 0))
        if not cur or score > ((cur.get("max_year") or cur.get("min_year") or 0), (cur.get("min_year") or 0)):
            keep[d] = t
    if not keep:
        return {}
    newest = max((t.get("max_year") or t.get("min_year") or 0) for t in keep.values())
    floor = Y - 6 if not deep else newest - 12
    return {d: t for d, t in keep.items() if (t.get("max_year") or t.get("min_year") or 0) >= floor}


def colour_from_thumb(t):
    url = t.get("obverse_thumbnail")
    if not url:
        return "#777777"
    try:
        p = "/tmp/_thumb.jpg"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://en.numista.com/"}), timeout=20) as f:
            open(p, "wb").write(f.read())
        return dominant_colour(p)
    except Exception:
        return "#777777"


def build_entry(nm, code, iso, display, cur, sym, region, cache, map_ids, skip=()):
    found = collect(nm, code)
    if len(found) < 4:
        deep = collect(nm, code, deep=True)
        found = {**deep, **found}
    found = {d: t for d, t in found.items() if d not in skip}
    if not found:
        return None
    notes, mats, years = [], [], []
    for d in sorted(found):
        t = found[d]
        det = nm.get(f'/types/{t["id"]}')
        pick = Numista.pick_from(det, 9)
        k_code = iso if len(iso) == 3 else None
        notes.append([d, colour_from_thumb(t), short(pick["obverse"]["description"]) or "—", short(pick["reverse"]["description"]) or "—"])
        cache_key = d
        mats.append(norm((det.get("composition") or {}).get("text", "")))
        years.append(t.get("min_year") or 0)
        cache.setdefault("_pending", {})[cache_key] = pick
    mat = "Polymer" if all("polymer" in m for m in mats if m) and any(mats) else \
          "Paper & polymer" if any("polymer" in m for m in mats) else "Paper"
    entry = {"iso": iso if len(iso) == 2 else None, "country": display, "cur": cur, "sym": sym if sym not in ("",) else "",
             "issuer": "", "region": region, "series": "Current notes", "year": max(years), "mat": mat, "notes": notes, "map": map_ids}
    return entry


def main():
    nm = Numista(os.environ.get("NUMISTA_KEY"), BUDGET)
    notes = load("notes.json", [])
    cache = load("numista_cache.json", {})
    have = {c["code"] for c in notes} | {c.get("iso") for c in notes}
    only = set(sys.argv[1:])
    added = []
    jobs = [(iso, nname, disp, cur, sym, reg, None) for iso, nname, disp, cur, sym, reg in COUNTRIES] + \
           [(code, nname, disp, cur, sym, reg, members) for code, disp, cur, sym, reg, nname, members in UNIONS]
    try:
        for iso, nname, disp, cur, sym, reg, members in jobs:
            if (only and iso not in only) or iso in have or any(w in norm(disp) for w in EXCLUDED_WORDS):
                continue
            code_known = cache.get("_issuers", {}).get(iso)
            cands = [code_known] if code_known else issuer_candidates(nname)
            map_ids = [m for m in ([numeric(x) for x in members] if members else [numeric(iso)]) if m]
            entry = None
            for code in cands:
                cache.pop("_pending", None)
                entry = build_entry(nm, code, iso, disp, cur, sym, reg, cache, map_ids)
                if entry:
                    cache.setdefault("_issuers", {})[iso if len(iso) == 3 else iso] = code
                    break
            if not entry:
                print("  nothing found for", disp); continue
            cc = iso  # internal code: ISO2 for countries, 3 letters for monetary unions
            entry["code"] = cc
            entry["partial"] = len(entry["notes"]) < 4
            for d, pick in cache.pop("_pending", {}).items():
                cache[f"{cc}-{d}"] = pick
            notes.append(entry)
            added.append(disp)
            print(f"added {disp}: {[n[0] for n in entry['notes']]}")
            save("notes.json", notes); save("numista_cache.json", cache)
        # complete countries that came in partial (marked "partial": true)
        for c in notes:
            if not c.get("partial") or (only and c["code"] not in only):
                continue
            code = cache.get("_issuers", {}).get(c["code"])
            if not code:
                continue
            cache.pop("_pending", None)
            have_d = {n[0] for n in c["notes"]}
            more = build_entry(nm, code, c["code"], c["country"], c["cur"], c["sym"], c["region"], cache, c.get("map", []), skip=have_d)
            if more:
                c["notes"] = sorted(c["notes"] + more["notes"], key=lambda n: n[0])
                for d, pick in cache.pop("_pending", {}).items():
                    cache[f'{c["code"]}-{d}'] = pick
            c["partial"] = False if len(c["notes"]) >= 4 or more is not None else c["partial"]
            print(f'refreshed {c["country"]}: {[n[0] for n in c["notes"]]}')
            save("notes.json", notes); save("numista_cache.json", cache)
    except RuntimeError as e:
        print("STOP:", e)
    save("notes.json", notes); save("numista_cache.json", cache)
    print(f"added {len(added)} countries; Numista requests used: {nm.used}")


if __name__ == "__main__":
    main()
