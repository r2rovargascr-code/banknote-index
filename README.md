# Banknote Index

A Passport Index–style site of the banknotes currently in circulation, with photos, a colour browser, a world map and the IBNS Banknote of the Year.

**Live site:** https://r2rovargascr-code.github.io/banknote-index/

## How it stays up to date (no manual work)
A GitHub Actions job (`.github/workflows/update.yml`) runs on the 1st of every month:
1. `scripts/check_new_notes.py` asks Numista for newly issued notes for every currency on the site and updates `data/notes.json`.
2. `scripts/fetch_images.py` fills in missing photos: issuing bank (`data/bank_sources.json`) → Numista → Wikimedia Commons. Only openly licensed photos are used, and each is credited.
3. `scripts/build.py` builds the site and it is published to GitHub Pages.
If anything changed, the job opens an issue, so GitHub emails you a summary.

## Settings
- `NUMISTA_KEY` – your Numista API key, stored under Settings → Secrets and variables → Actions.
- Pages – Settings → Pages → Source: **GitHub Actions**.

## Editing by hand
Banknotes live in `data/notes.json` as `[denomination, colour, front subject, back subject]`. Commit a change and the site republishes within a few minutes.
