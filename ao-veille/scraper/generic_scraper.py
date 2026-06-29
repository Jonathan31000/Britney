"""
Scraper générique piloté par la config JSON d'une source.
"""

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from scraper.database import insert_offre, insert_log, update_source, get_source


def _extract_text(el, default=None):
    if el is None:
        return default
    return el.get_text(strip=True) or default


def _extract_budget(text: str, pattern: str = None) -> float | None:
    if not text:
        return None
    pat = pattern or r"(\d[\d\s]{2,6})\s*€"
    matches = re.findall(pat, text)
    for m in matches:
        val = float(re.sub(r"\s", "", m))
        if 100 <= val <= 5000:
            return val
    return None


def _parse_date(text: str, fmt: str = None) -> str | None:
    if not text:
        return None
    formats = [fmt] if fmt else ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"]
    for f in formats:
        try:
            return datetime.strptime(text.strip(), f).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _build_session(source: dict) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9",
    })
    cookies_json = source.get("cookies_json")
    if cookies_json:
        cookies = json.loads(cookies_json)
        for c in cookies:
            session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))
    return session


def _scrape_page(session, url, selectors, field_patterns, base_url) -> list:
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    row_sel = selectors.get("offer_row")
    if not row_sel:
        return []

    rows = soup.select(row_sel)
    offers = []

    for row in rows:
        def get(field):
            sel = selectors.get(field)
            if not sel:
                return None
            el = row.select_one(sel)
            if field == "url" and el:
                href = el.get("href", "")
                if href and not href.startswith("http"):
                    href = base_url.rstrip("/") + "/" + href.lstrip("/")
                return href
            return _extract_text(el)

        titre = get("titre") or "Sans titre"
        acheteur = get("acheteur") or ""
        description = get("description") or ""
        date_limite_raw = get("date_limite")
        budget_raw = get("budget")

        date_fmt = field_patterns.get("date") if field_patterns else None
        budget_pat = field_patterns.get("budget") if field_patterns else None

        offers.append({
            "titre": titre,
            "acheteur": acheteur,
            "description": description,
            "date_limite": _parse_date(date_limite_raw, date_fmt),
            "date_pub": datetime.now().strftime("%Y-%m-%d"),
            "budget_min": None,
            "budget_max": _extract_budget(budget_raw or description, budget_pat),
            "url": get("url") or url,
        })

    return offers


def run_generic_scraper(source_id: int) -> dict:
    source = get_source(source_id)
    if not source:
        return {"status": "error", "message": f"Source {source_id} introuvable"}

    config = json.loads(source.get("config_json") or "{}")
    if not config:
        return {"status": "error", "message": "Source sans configuration — relancer l'analyse"}

    selectors = config.get("selectors", {})
    field_patterns = config.get("field_patterns", {})
    pagination = config.get("pagination", {})
    base_url = source["base_url"]
    list_url = source["list_url"]

    session = _build_session(source)

    all_offers = []
    page = pagination.get("start", 1)
    max_pages = 20  # Sécurité

    while page <= max_pages:
        # Construire l'URL paginée
        if pagination.get("type") == "query_param":
            param = pagination.get("param", "page")
            sep = "&" if "?" in list_url else "?"
            url = f"{list_url}{sep}{param}={page}"
        elif pagination.get("type") == "path":
            url = f"{list_url}/{page}"
        else:
            url = list_url

        offers = _scrape_page(session, url, selectors, field_patterns, base_url)
        if not offers:
            break

        all_offers.extend(offers)

        if pagination.get("type") == "none":
            break
        page += 1

    # Insertion en base
    nouvelles = 0
    for o in all_offers:
        o["source"] = source["name"]
        result = insert_offre(o)  # Supposant que insert_offre retourne True si nouvelle
        if result:
            nouvelles += 1

    update_source(source_id, {"last_scraped": datetime.now().isoformat()})

    insert_log(source["name"], "scrape_done", json.dumps({
        "trouvees": len(all_offers),
        "nouvelles": nouvelles
    }))

    return {
        "status": "ok",
        "source": source["name"],
        "trouvees": len(all_offers),
        "nouvelles": nouvelles
    }