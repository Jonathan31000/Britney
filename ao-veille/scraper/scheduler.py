"""
scraper/scheduler.py — Lancement automatique scraping + scoring multi-user
"""
import logging
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from scraper.ai_scorer import run_scorer_all_users
from scraper.database import insert_log

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")


def job_scrape():
    """Scraping piter.at — une fois, partagé pour tous les users."""
    try:
        from scraper.piter_scraper import run_scraper
        result = run_scraper()
        insert_log("piter.at", "scrape_done", str(result))
        logger.info(f"[SCRAPE] {result}")
    except Exception as e:
        insert_log("piter.at", "scrape_error", str(e))
        logger.error(f"[SCRAPE] Erreur : {e}")


def job_score():
    """Scoring pour tous les commerciaux actifs."""
    try:
        results = run_scorer_all_users()
        insert_log("scorer", "run_done", str(results))
        logger.info(f"[SCORE] {results}")
    except Exception as e:
        insert_log("scorer", "score_error", str(e))
        logger.error(f"[SCORE] Erreur : {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Europe/Paris")

    # Scraping toutes les heures en semaine, 8h-20h
    scheduler.add_job(
        job_scrape,
        CronTrigger(day_of_week="mon-fri", hour="8-20", minute=0),
        id="scrape_hourly",
        name="Scraping piter.at (toutes les heures)",
    )

    # Scraping complet le matin à 7h30
    scheduler.add_job(
        job_scrape,
        CronTrigger(day_of_week="mon-fri", hour=7, minute=30),
        id="scrape_morning",
        name="Scraping piter.at (matin)",
    )

    # Scoring pour tous les commerciaux — 30 minutes après chaque scraping
    scheduler.add_job(
        job_score,
        CronTrigger(day_of_week="mon-fri", hour="8-20", minute=30),
        id="score_hourly",
        name="Scoring IA tous les commerciaux",
    )

    # Scoring matin — 8h00
    scheduler.add_job(
        job_score,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=0),
        id="score_morning",
        name="Scoring IA matin",
    )

    logger.info("Scheduler démarré. Ctrl+C pour arrêter.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler arrêté.")