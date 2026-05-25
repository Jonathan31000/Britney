"""
scraper/scheduler.py
Lance le scraping + scoring automatiquement selon une planification.
"""
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .piter_scraper import run_scraper
from .ai_scorer import run_scorer
from .database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def pipeline():
    """Pipeline complet : scrape → score."""
    logger.info("=== Démarrage du pipeline ===")
    try:
        result = run_scraper()
        logger.info(f"Scraping terminé : {result}")
    except Exception as e:
        logger.error(f"Erreur scraping : {e}")

    try:
        result = run_scorer()
        logger.info(f"Scoring terminé : {result}")
    except Exception as e:
        logger.error(f"Erreur scoring : {e}")
    logger.info("=== Pipeline terminé ===")


def start_scheduler():
    """Démarre le scheduler en arrière-plan."""
    init_db()

    scheduler = BackgroundScheduler()

    # Scraping toutes les heures de 8h à 20h, du lundi au vendredi
    scheduler.add_job(
        pipeline,
        CronTrigger(day_of_week="mon-fri", hour="8-20", minute=0),
        id="pipeline_horaire",
        name="Pipeline scraping + scoring",
        replace_existing=True,
    )

    # Un passage complet le matin à 7h30
    scheduler.add_job(
        pipeline,
        CronTrigger(day_of_week="mon-fri", hour=7, minute=30),
        id="pipeline_matin",
        name="Pipeline matin",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler démarré — pipeline toutes les heures (lun-ven 8h-20h)")
    return scheduler


if __name__ == "__main__":
    # Lancement manuel : python -m scraper.scheduler
    scheduler = start_scheduler()

    # Premier passage immédiat
    logger.info("Premier passage immédiat...")
    pipeline()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("Scheduler arrêté.")
