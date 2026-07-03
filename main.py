"""
main.py — Point d'entrée du scraper Piter

Usage :
    python main.py                        → scrape tout
    python main.py --max-pages 3          → limite à 3 pages (test)
    python main.py --detail               → va chercher les pages détail aussi
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Charge les variables d'environnement depuis .env
load_dotenv()

# Configure les logs
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add("logs/scraper_{time:YYYY-MM-DD}.log", level="DEBUG", rotation="1 day")

# Import après load_dotenv
from src import PiterAuth, PiterScraper, parse_ao_list_page, parse_ao_detail, AOExporter


def parse_args():
    parser = argparse.ArgumentParser(description="Scraper Appels d'offres Piter")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="Nombre max de pages à scraper (None = tout)")
    parser.add_argument("--detail", action="store_true",
                        help="Aller chercher la page détail de chaque AO")
    return parser.parse_args()


def main():
    args = parse_args()
    base_url = __import__("os").getenv("PITER_BASE_URL", "https://www.piter.fr")

    # ── 1. Authentification ───────────────────────────────────
    auth = PiterAuth()
    try:
        session = auth.login()
    except Exception as e:
        logger.error(f"Impossible de se connecter : {e}")
        sys.exit(1)

    # ── 2. Scraping des pages de liste ────────────────────────
    scraper = PiterScraper(session)
    list_soups = scraper.scrape_all_pages(max_pages=args.max_pages)

    # ── 3. Parsing ────────────────────────────────────────────
    all_records = []
    for soup in list_soups:
        records = parse_ao_list_page(soup, base_url=base_url)
        all_records.extend(records)

    logger.info(f"📦 {len(all_records)} appels d'offres extraits au total")

    # ── 4. Enrichissement via pages détail (optionnel) ────────
    if args.detail and all_records:
        logger.info("🔍 Récupération des pages détail...")
        for i, record in enumerate(all_records, 1):
            if record.get("lien"):
                try:
                    logger.info(f"Détail {i}/{len(all_records)} — {record['titre'][:60]}...")
                    detail_soup = scraper.get_ao_detail(record["lien"])
                    extra = parse_ao_detail(detail_soup)
                    record.update(extra)
                except Exception as e:
                    logger.warning(f"Détail ignoré ({record['lien']}) : {e}")

    # ── 5. Export ─────────────────────────────────────────────
    if not all_records:
        logger.warning("⚠️  Aucun AO trouvé — vérifie les sélecteurs dans parser.py")
        sys.exit(0)

    exporter = AOExporter()
    output_path = exporter.export(all_records)

    logger.success(f"\n🎉 Terminé ! Fichier : {output_path}")


if __name__ == "__main__":
    main()
