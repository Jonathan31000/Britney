"""
auth.py — Gestion de la session et de l'authentification Piter
"""

import os
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_fixed
from loguru import logger


class PiterAuth:
    """
    Gère la connexion à Piter et maintient la session HTTP.
    Utilise requests.Session pour conserver les cookies entre les requêtes.
    """

    def __init__(self):
        self.base_url = os.getenv("PITER_BASE_URL", "https://www.piter.fr")
        self.login_url = os.getenv("PITER_LOGIN_URL", "https://www.piter.fr/login")
        self.email = os.getenv("PITER_EMAIL")
        self.password = os.getenv("PITER_PASSWORD")

        if not self.email or not self.password:
            raise ValueError(
                "❌ PITER_EMAIL et PITER_PASSWORD doivent être définis dans le fichier .env"
            )

        self.session = requests.Session()
        ua = UserAgent()
        self.session.headers.update({
            "User-Agent": ua.random,
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.base_url,
        })

    def _parse_login_form(self, soup: BeautifulSoup) -> dict:
        """
        Inspecte le formulaire de login et retourne :
          - email_field   : nom du champ email/login
          - password_field: nom du champ password
          - csrf_field    : nom du champ CSRF token (None si absent)
          - csrf_value    : valeur du token CSRF (None si absent)
        """
        all_inputs = soup.find_all("input")
        logger.debug(
            f"Inputs trouvés sur la page login : "
            f"{[(i.get('name'), i.get('type')) for i in all_inputs]}"
        )

        email_field = "email"
        password_field = "password"
        csrf_field = None
        csrf_value = None

        for inp in all_inputs:
            itype = inp.get("type", "").lower()
            name = inp.get("name") or ""

            if itype == "email" or "email" in name.lower() or "mail" in name.lower() or "username" in name.lower():
                email_field = name
            elif itype == "password":
                password_field = name
            elif itype == "hidden" or "token" in name.lower() or "csrf" in name.lower():
                csrf_field = name
                csrf_value = inp.get("value") or ""

        logger.debug(
            f"Formulaire détecté : email='{email_field}', password='{password_field}', "
            f"csrf_field='{csrf_field}', csrf_value='{(csrf_value or '')[:12]}...'"
        )
        return {
            "email_field": email_field,
            "password_field": password_field,
            "csrf_field": csrf_field,
            "csrf_value": csrf_value,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def login(self) -> requests.Session:
        """
        Effectue le POST de login et retourne la session authentifiée.
        Détecte automatiquement les noms des champs du formulaire.
        """
        logger.info(f"Connexion à Piter avec {self.email}...")

        login_page = self.session.get(self.login_url, timeout=15)
        login_page.raise_for_status()
        soup = BeautifulSoup(login_page.text, "lxml")

        form = self._parse_login_form(soup)

        payload = {
            form["email_field"]: self.email,
            form["password_field"]: self.password,
        }
        if form["csrf_field"] and form["csrf_value"] is not None:
            payload[form["csrf_field"]] = form["csrf_value"]

        response = self.session.post(
            self.login_url,
            data=payload,
            timeout=20,
            allow_redirects=True,
        )
        response.raise_for_status()

        if self._is_logged_in(response):
            logger.success("✅ Connecté avec succès !")
            return self.session
        else:
            raise ConnectionError(
                "❌ Échec de la connexion — vérifie tes credentials ou les noms des champs du formulaire"
            )

    def _is_logged_in(self, response: requests.Response) -> bool:
        """
        Piter redirige vers /connexion en cas d'échec de login.
        Si l'URL finale est hors de la page connexion → succès.
        """
        logger.debug(f"URL après login : {response.url}")

        login_indicators = ["connexion", "login"]
        on_login_page = any(ind in response.url.lower() for ind in login_indicators)

        if on_login_page:
            logger.error(f"Toujours sur la page de connexion ({response.url}) — credentials incorrects ?")
            return False

        return True
