"""
scraper/auth_playwright.py
Renouvellement automatique des cookies piter.at via Playwright.
Utilisé en fallback quand cookies.json est expiré.
"""
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

EMAIL        = os.getenv("PITER_EMAIL", "")
PASSWORD     = os.getenv("PITER_PASSWORD", "")
BASE_URL     = os.getenv("PITER_BASE_URL", "https://piter.at")
COOKIES_FILE = "cookies.json"


def refresh_cookies(headless: bool = True) -> bool:
    """
    Ouvre Chrome via Playwright, se connecte sur piter.at,
    récupère les cookies et les sauvegarde dans cookies.json.
    Retourne True si succès, False sinon.
    """
    if not EMAIL or not PASSWORD:
        logger.error("[playwright] PITER_EMAIL ou PITER_PASSWORD manquant dans .env")
        return False

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        logger.error("[playwright] Playwright non installé — pip install playwright")
        return False

    logger.info(f"[playwright] Lancement Chrome headless={headless}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
            locale="fr-FR",
        )
        page = context.new_page()

        try:
            # 1. Charger la page de connexion
            logger.info("[playwright] Chargement page connexion...")
            page.goto(f"{BASE_URL}/connexion", wait_until="networkidle", timeout=30000)

            # 2. Remplir le formulaire
            page.fill("input[name='login[email]']", EMAIL)
            page.fill("input[name='login[password]']", PASSWORD)

            # Cocher "Rester connecté" si présent (cookie REMEMBERME 30j)
            remember = page.query_selector("input[name='login[remember_me]']")
            if remember:
                remember.check()

            logger.info("[playwright] Soumission du formulaire...")
            page.click("button[type='submit']")

            # 3. Attendre la redirection post-login
            try:
                page.wait_for_url(f"{BASE_URL}/prestataire/**", timeout=15000)
            except PlaywrightTimeout:
                # Certains reCAPTCHA déclenchent une page intermédiaire
                page.wait_for_load_state("networkidle", timeout=15000)

            current_url = page.url
            if "connexion" in current_url:
                logger.error(f"[playwright] Login échoué — toujours sur {current_url}")
                browser.close()
                return False

            logger.info(f"[playwright] Connecté → {current_url}")

            # 4. Récupérer les cookies
            cookies = context.cookies()
            if not cookies:
                logger.error("[playwright] Aucun cookie récupéré")
                browser.close()
                return False

            # 5. Sauvegarder dans cookies.json (format Cookie-Editor compatible)
            with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            logger.info(f"[playwright] {len(cookies)} cookie(s) sauvegardé(s) dans {COOKIES_FILE}")
            browser.close()
            return True

        except Exception as e:
            logger.error(f"[playwright] Erreur : {e}")
            try:
                browser.close()
            except Exception:
                pass
            return False


def ensure_cookies(max_attempts: int = 2) -> bool:
    """
    Vérifie si cookies.json est valide, sinon tente un refresh.
    Retourne True si les cookies sont utilisables.
    """
    for attempt in range(1, max_attempts + 1):
        logger.info(f"[playwright] Tentative {attempt}/{max_attempts}...")
        if refresh_cookies(headless=attempt == 1):
            return True
        if attempt == 1:
            # 2ème tentative en mode visible pour debug
            logger.warning("[playwright] Retry en mode visible (headless=False)...")
    return False