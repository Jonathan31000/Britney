"""
scraper/piter_scraper.py
Scraper pour piter.at — authentification par cookies de session (contournement reCAPTCHA).

COMMENT OBTENIR VOS COOKIES :
1. Connectez-vous manuellement sur https://piter.at dans Chrome
2. F12 → Application → Cookies → https://piter.at
3. Copiez la valeur du cookie "PHPSESSID" (ou similaire)
4. Collez-la dans le fichier .env : PITER_SESSION_COOKIE=valeur
   Ou exportez tous les cookies via l'extension "Cookie-Editor" (format JSON)
   et sauvegardez dans cookies.json à la racine du projet.
"""
import os
import re
import json
import time
import logging
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from .database import insert_offre, update_statut, log_event
from .rules import load_rules, apply_rules

load_dotenv()
logger = logging.getLogger(__name__)

BASE_URL     = os.getenv("PITER_BASE_URL", "https://piter.at")
EMAIL        = os.getenv("PITER_EMAIL", "")
PASSWORD     = os.getenv("PITER_PASSWORD", "")
SESSION_COOKIE = os.getenv("PITER_SESSION_COOKIE", "")
COOKIES_FILE = "cookies.json"
RULES_PATH   = "config/rules.yaml"

LIST_URL = f"{BASE_URL}/prestataire/consultation"


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": BASE_URL,
    })
    return session


def load_session_from_cookies(session: requests.Session) -> bool:
    """
    Méthode 1 : charge les cookies depuis cookies.json (export Cookie-Editor).
    Méthode 2 : utilise PITER_SESSION_COOKIE depuis .env.
    Méthode 3 : tente le login classique (peut échouer si reCAPTCHA actif).
    """

    # --- Méthode 1 : fichier cookies.json ---
    if os.path.exists(COOKIES_FILE):
        try:
            with open(COOKIES_FILE, "r") as f:
                cookies = json.load(f)
            for c in cookies:
                session.cookies.set(
                    c.get("name", ""),
                    c.get("value", ""),
                    domain=c.get("domain", "piter.at").lstrip(".")
                )
            # Vérification
            resp = session.get(LIST_URL, timeout=15, allow_redirects=True)
            if "connexion" not in resp.url and resp.status_code == 200:
                logger.info(f"[piter] Connecté via cookies.json → {resp.url}")
                log_event("piter.at", "login_ok", "cookies.json")
                return True
            logger.warning("[piter] cookies.json présent mais session invalide (expirée ?)")
        except Exception as e:
            logger.warning(f"[piter] Erreur lecture cookies.json : {e}")

    # --- Méthode 2 : cookie manuel dans .env ---
    if SESSION_COOKIE:
        # Format attendu : "nom=valeur; nom2=valeur2"
        for pair in SESSION_COOKIE.split(";"):
            pair = pair.strip()
            if "=" in pair:
                name, value = pair.split("=", 1)
                session.cookies.set(name.strip(), value.strip(), domain="piter.at")
        resp = session.get(LIST_URL, timeout=15, allow_redirects=True)
        if "connexion" not in resp.url and resp.status_code == 200:
            logger.info(f"[piter] Connecté via PITER_SESSION_COOKIE → {resp.url}")
            log_event("piter.at", "login_ok", "session_cookie")
            return True
        logger.warning("[piter] PITER_SESSION_COOKIE invalide ou expiré")

    # --- Méthode 3 : login classique (fonctionne si reCAPTCHA désactivé) ---
    logger.info("[piter] Tentative login classique...")
    return login_classic(session)


def login_classic(session: requests.Session) -> bool:
    """Login email/password — bloqué si reCAPTCHA actif."""
    login_url = f"{BASE_URL}/connexion"
    try:
        resp = session.get(login_url, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        # Token CSRF Symfony : login[_token]
        csrf = ""
        field = soup.find("input", {"name": "login[_token]"})
        if field:
            csrf = field.get("value", "")
            logger.info("[piter] Token CSRF trouvé")

        # Token reCAPTCHA (champ login[recaptcha]) — on tente avec valeur vide
        recaptcha_val = ""
        recap_field = soup.find("input", {"name": "login[recaptcha]"})
        if recap_field:
            recaptcha_val = recap_field.get("value", "")

        payload = {
            "login[email]":      EMAIL,
            "login[password]":   PASSWORD,
            "login[remember_me]": "1",
            "login[_token]":     csrf,
            "login[recaptcha]":  recaptcha_val,
        }

        resp2 = session.post(login_url, data=payload, timeout=15, allow_redirects=True)

        if "connexion" not in resp2.url and resp2.status_code == 200:
            logger.info(f"[piter] Login classique OK → {resp2.url}")
            log_event("piter.at", "login_ok", resp2.url)
            return True
        else:
            logger.error(f"[piter] Login classique échoué (reCAPTCHA probable) → {resp2.url}")
            log_event("piter.at", "login_fail", "recaptcha_bloque")
            return False

    except Exception as e:
        logger.error(f"[piter] Erreur login : {e}")
        log_event("piter.at", "login_error", str(e))
        return False


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def get_page_urls(session: requests.Session) -> List[str]:
    urls = [LIST_URL]
    try:
        resp = session.get(LIST_URL, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        pagination = soup.find("nav", class_="pagination-nav")
        if pagination:
            for a in pagination.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/"):
                    href = BASE_URL + href
                if href not in urls and "page=" in href:
                    urls.append(href)
    except Exception as e:
        logger.warning(f"[piter] Erreur pagination : {e}")
    logger.info(f"[piter] {len(urls)} page(s)")
    return urls


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_row(row: BeautifulSoup) -> Optional[dict]:
    try:
        tds = row.find_all("td")
        if len(tds) < 7:
            return None

        ao_td = tds[1]
        ao_num = ao_td.get_text(strip=True)
        modal_title = ao_td.get("data-modal-title", "")
        titre = modal_title.replace("Consultation", "").strip() if modal_title else ao_num

        data_url = row.get("data-url", "")
        url = BASE_URL + data_url if data_url.startswith("/") else data_url

        # Client via tooltip
        client = ""
        img = tds[2].find("img", {"data-tooltip-target": True})
        if img:
            tip = row.find("div", {"id": img.get("data-tooltip-target", "")})
            if tip:
                c = tip.find(class_="js-tooltip-content")
                client = c.get_text(strip=True) if c else ""

        # Entité
        entite_span = tds[3].find("span", class_="min-w-32")
        entite = entite_span.get_text(strip=True) if entite_span else ""
        if entite_span and entite_span.get("data-tooltip-target"):
            tip = row.find("div", {"id": entite_span["data-tooltip-target"]})
            if tip:
                c = tip.find(class_="js-tooltip-content")
                if c: entite = c.get_text(strip=True)

        # Mission
        mission_span = tds[4].find("span", class_="min-w-32") if len(tds) > 4 else None
        mission = mission_span.get_text(strip=True) if mission_span else ""
        if mission_span and mission_span.get("data-tooltip-target"):
            tip = row.find("div", {"id": mission_span["data-tooltip-target"]})
            if tip:
                c = tip.find(class_="js-tooltip-content")
                if c: mission = c.get_text(strip=True)

        # Niveau / Lieu
        niveau = tds[5].find("span").get_text(strip=True) if len(tds) > 5 and tds[5].find("span") else ""
        lieu_span = tds[6].find("span") if len(tds) > 6 else None
        lieu = lieu_span.get_text(strip=True) if lieu_span else ""
        if lieu_span and lieu_span.get("data-tooltip-target"):
            tip = row.find("div", {"id": lieu_span["data-tooltip-target"]})
            if tip:
                c = tip.find(class_="js-tooltip-content")
                if c: lieu = c.get_text(strip=True)

        acheteur = f"{client} / {entite}" if client and entite else (client or entite)
        titre_complet = f"{titre} — {mission}" if mission else titre

        return {
            "source":      "piter.at",
            "titre":       titre_complet,
            "description": f"Mission : {mission}\nNiveau : {niveau}\nLieu : {lieu}",
            "acheteur":    acheteur,
            "budget_min":  None,
            "budget_max":  None,
            "date_limite": "",
            "date_pub":    datetime.now().strftime("%Y-%m-%d"),
            "url":         url,
            "_token":      row.get("data-token", ""),
        }
    except Exception as e:
        logger.debug(f"[piter] Erreur parse row : {e}")
        return None


def enrich_from_panel(soup: BeautifulSoup, offre: dict) -> dict:
    """Enrichit avec le panneau détail déjà présent dans la page liste."""
    token = offre.get("_token", "")
    panel = soup.find("div", {"id": token, "class": re.compile("js-consultation-info")})
    if not panel:
        return offre

    fields = {}
    for bold in panel.find_all("span", class_="font-bold"):
        key = bold.get_text(strip=True).lower()
        val = bold.find_next_sibling("div")
        if val:
            fields[key] = val.get_text(separator="\n", strip=True)

    parts = []
    for k in ["contexte", "description", "compétences", "livrables"]:
        if fields.get(k):
            parts.append(f"=== {k.upper()} ===\n{fields[k]}")
    if parts:
        offre["description"] = "\n\n".join(parts)[:4000]

    if fields.get("date de fin souhaitée"):
        offre["date_limite"] = _norm_date(fields["date de fin souhaitée"])
    if fields.get("publiée"):
        offre["date_pub"] = _norm_date(fields["publiée"])

    bmin, bmax = _parse_tjm("\n".join(parts))
    if bmax:
        offre["budget_min"] = bmin
        offre["budget_max"] = bmax

    return offre


def _parse_tjm(text: str):
    vals = []
    for m in re.findall(r'(\d[\d\s]*)\s*€', text.replace("\u00a0", " ")):
        try:
            v = float(m.replace(" ", ""))
            if 100 <= v <= 5000:
                vals.append(v)
        except ValueError:
            pass
    if not vals: return None, None
    if len(vals) == 1: return None, vals[0]
    return min(vals), max(vals)


def _norm_date(text: str) -> str:
    for p, r in [(r"(\d{2})/(\d{2})/(\d{4})", r"\3-\2-\1"),
                 (r"(\d{4})-(\d{2})-(\d{2})", r"\1-\2-\3")]:
        m = re.search(p, text)
        if m: return re.sub(p, r, m.group())
    return text.strip()[:10]


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def run_scraper():
    logger.info("[piter] Démarrage scraping...")
    rules = load_rules(RULES_PATH)

    session = create_session()
    if not load_session_from_cookies(session):
        log_event("piter.at", "scrape_abort", "authentification échouée")
        return {"status": "error", "message": "Authentification échouée — voir README pour cookies"}

    stats = {"trouvees": 0, "nouvelles": 0, "filtre_ok": 0, "filtre_ko": 0}

    for page_url in get_page_urls(session):
        try:
            resp = session.get(page_url, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")
            rows = soup.find_all("tr", class_=re.compile(r"js-consultation-list"))
            logger.info(f"[piter] {len(rows)} offre(s) sur {page_url}")

            for row in rows:
                offre = parse_row(row)
                if not offre:
                    continue
                stats["trouvees"] += 1

                ok, raison = apply_rules(offre, rules)
                if not ok:
                    stats["filtre_ko"] += 1
                    continue

                offre = enrich_from_panel(soup, offre)
                ok, raison = apply_rules(offre, rules)
                statut = "filtre_ok" if ok else "filtre_ko"
                stats["filtre_ok" if ok else "filtre_ko"] += 1

                offre.pop("_token", None)
                offre_id = insert_offre(offre)
                if offre_id:
                    update_statut(offre_id, statut)
                    stats["nouvelles"] += 1
                    logger.info(f"[piter] #{offre_id} : {offre['titre'][:60]}")

                time.sleep(0.3)

        except Exception as e:
            logger.error(f"[piter] Erreur page {page_url} : {e}")

    log_event("piter.at", "scrape_done", json.dumps(stats))
    logger.info(f"[piter] Terminé : {stats}")
    return {"status": "ok", **stats}