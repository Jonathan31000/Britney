"""
scraper/ai_scorer.py
Scoring des appels d'offres via l'API Anthropic (Claude).
Le contexte entreprise et le template de prompt sont lus depuis la table `config` (V2).
"""
import os
import json
import logging
import anthropic
from dotenv import load_dotenv

from .database import get_offres_a_scorer, get_config, insert_score, update_statut, log_event

load_dotenv()
logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Tu es un expert en réponse aux appels d'offres publics et privés.
Tu analyses des offres de marché et évalues leur pertinence pour une entreprise donnée.
Tu réponds UNIQUEMENT en JSON valide, sans markdown, sans texte supplémentaire."""


def build_user_prompt(offre: dict) -> str:
    """Construit le prompt en injectant les données de l'offre dans le template stocké en base."""
    company_context = get_config("company_context")
    prompt_template = get_config("prompt_template")

    budget_str = "non renseigné"
    if offre.get("budget_max"):
        if offre.get("budget_min"):
            budget_str = f"{offre['budget_min']} – {offre['budget_max']}"
        else:
            budget_str = str(offre["budget_max"])

    return prompt_template.format(
        company_context=company_context,
        titre=offre.get("titre", "N/A"),
        acheteur=offre.get("acheteur", "N/A"),
        budget=budget_str,
        date_limite=offre.get("date_limite", "N/A"),
        source=offre.get("source", "N/A"),
        description=offre.get("description", "Pas de description disponible")[:2000],
    )


def _recommandation_from_score(score: float) -> str:
    """Calcule la recommandation selon les seuils paramétrables."""
    go_threshold     = get_config("score_go_threshold")
    etudier_threshold = get_config("score_etudier_threshold")
    if score >= go_threshold:
        return "go"
    if score >= etudier_threshold:
        return "a_etudier"
    return "no_go"


def score_offre(offre: dict) -> dict:
    """Envoie une offre à Claude et retourne le score structuré."""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": build_user_prompt(offre)}
            ]
        )

        raw = message.content[0].text
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(clean)

        # Validation minimale
        result.setdefault("score", 5)
        result.setdefault("resume", "")
        result.setdefault("points_forts", [])
        result.setdefault("points_faibles", [])
        result.setdefault("justification", "")

        # Recalcule la recommandation selon les seuils paramétrés
        # (au cas où Claude retourne une valeur hors-seuil)
        score = float(result["score"])
        result["recommandation"] = _recommandation_from_score(score)

        return result

    except json.JSONDecodeError as e:
        logger.error(f"[scorer] JSON invalide pour offre {offre.get('id')} : {e}")
        return {"score": 0, "resume": "Erreur parsing", "recommandation": "a_etudier",
                "points_forts": [], "points_faibles": []}
    except Exception as e:
        logger.error(f"[scorer] Erreur API pour offre {offre.get('id')} : {e}")
        return {"score": 0, "resume": f"Erreur API : {str(e)}", "recommandation": "a_etudier",
                "points_forts": [], "points_faibles": []}


def run_scorer():
    """Traite toutes les offres en attente de scoring."""
    offres = get_offres_a_scorer()
    logger.info(f"[scorer] {len(offres)} offre(s) à scorer")

    stats = {"total": len(offres), "ok": 0, "errors": 0}

    for offre in offres:
        logger.info(f"[scorer] Scoring offre #{offre['id']} : {offre['titre'][:60]}...")
        score_data = score_offre(offre)

        if score_data.get("score", 0) > 0 or score_data.get("resume"):
            insert_score(offre["id"], score_data)
            update_statut(offre["id"], "scored")
            stats["ok"] += 1
        else:
            stats["errors"] += 1

    log_event("scorer", "run_done", json.dumps(stats))
    logger.info(f"[scorer] Terminé : {stats}")
    return stats