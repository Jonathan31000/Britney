"""
scraper.py — Navigation sur le site Piter et récupération des pages d'appels d'offres
"""

import os
import time
import random
import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class PiterScraper:
    """
    Navigue sur les pages d'appels d'offres Piter et retourne le HTML brut.
    Le parsing est délégué à parser.py (séparation des responsabilités).
    """

    def __init__(self, session: requests.Session):
        self.session = session
        self.ao_url = os.getenv("PITER_AO_URL", "https://www.piter.fr/appels-offres")
        self.base_url = os.getenv("PITER_BASE_URL", "https://www.piter.fr")

    def _polite_delay(self, min_s: float = 1.5, max_s: float = 4.0):
        """Pause aléatoire entre les requêtes pour ne pas surcharger le serveur."""
        delay = random.uniform(min_s, max_s)
        logger.debug(f"Pause {delay:.1f}s...")
        time.sleep(delay)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _get_page(self, url: str) -> BeautifulSoup:
        """Récupère une page et retourne un objet BeautifulSoup."""
        logger.debug(f"GET {url}")
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def get_total_pages(self) -> int:
        """
        Récupère le nombre total de pages de résultats.
        ⚠️ À adapter selon la pagination du site Piter.
        """
        soup = self._get_page(self.ao_url)

        # Exemple — cherche le dernier numéro de page dans la pagination
        # Adapter le sélecteur CSS selon l'HTML réel du site
        pagination = soup.select("ul.pagination li a")
        if not pagination:
            logger.warning("Pas de pagination trouvée, on suppose 1 page.")
            return 1

        page_numbers = []
        for link in pagination:
            try:
                page_numbers.append(int(link.text.strip()))
            except ValueError:
                pass  # ignore les liens "Suivant", ">>", etc.

        return max(page_numbers) if page_numbers else 1

    def get_ao_list_page(self, page: int = 1) -> BeautifulSoup:
        """
        Récupère une page de liste d'appels d'offres.
        ⚠️ Adapter le paramètre de pagination selon l'URL du site (page=, p=, offset=...).
        """
        url = f"{self.ao_url}?page={page}"  # ⚠️ À adapter
        self._polite_delay()
        return self._get_page(url)

    def get_ao_detail(self, detail_url: str) -> BeautifulSoup:
        """
        Récupère la page détail d'un appel d'offres.
        Si detail_url est relatif, on préfixe avec base_url.
        """
        if detail_url.startswith("/"):
            detail_url = self.base_url + detail_url

        self._polite_delay()
        return self._get_page(detail_url)

    def scrape_all_pages(self, max_pages: int | None = None) -> list[BeautifulSoup]:
        """
        Scrape toutes les pages de liste et retourne une liste de BeautifulSoup.
        max_pages : limite optionnelle (utile pour les tests).
        """
        total = self.get_total_pages()
        pages_to_scrape = min(total, max_pages) if max_pages else total
        logger.info(f"📄 {total} pages trouvées — scraping de {pages_to_scrape} pages")

        soups = []
        for page_num in range(1, pages_to_scrape + 1):
            logger.info(f"Page {page_num}/{pages_to_scrape}...")
            soup = self.get_ao_list_page(page=page_num)
            soups.append(soup)

        return soups
