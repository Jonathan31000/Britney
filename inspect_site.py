"""
inspect_site.py — Script d'aide pour inspecter la structure HTML de Piter

Lance ce script EN PREMIER pour identifier les bons sélecteurs CSS
avant d'adapter parser.py.

Usage : python inspect_site.py
"""

import os
import sys
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

logger.remove()
logger.add(sys.stdout, level="DEBUG", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | {message}")

from src.auth import PiterAuth


def main():
    ao_url = os.getenv("PITER_AO_URL", "https://www.piter.fr/appels-offres")

    logger.info("Connexion...")
    auth = PiterAuth()
    session = auth.login()

    logger.info(f"Récupération de {ao_url}")
    response = session.get(ao_url, timeout=20)
    response.raise_for_status()

    # Sauvegarde le HTML brut pour inspection
    output_file = "data/output/debug_page.html"
    os.makedirs("data/output", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(response.text)

    logger.success(f"✅ HTML sauvegardé dans {output_file}")
    logger.info("Ouvre ce fichier dans VS Code ou ton navigateur pour identifier les sélecteurs CSS")
    logger.info("Cherche le container qui contient chaque appel d'offres dans la liste")


if __name__ == "__main__":
    main()
