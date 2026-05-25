"""
scraper/ai_scorer.py
Scoring des appels d'offres via l'API Anthropic (Claude).
"""
import os
import json
import logging
import anthropic
from dotenv import load_dotenv

from .database import get_offres_a_scorer, insert_score, update_statut, log_event

load_dotenv()
logger = logging.getLogger(__name__)

COMPANY_CONTEXT = os.getenv(
    "COMPANY_CONTEXT",
    "Entreprise généraliste en services informatiques."
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


SYSTEM_PROMPT = """Tu es un expert en réponse aux appels d'offres publics et privés.
Tu analyses des offres de marché et évalues leur pertinence pour une entreprise donnée.
Tu réponds UNIQUEMENT en JSON valide, sans markdown, sans texte supplémentaire."""


def build_user_prompt(offre: dict, context: str) -> str:
    budget_str = ""
    if offre.get("budget_max"):
        budget_str = f"Budget estimé : {offre.get('budget_min','?')} – {offre['budget_max']} €"

    return f"""Contexte de notre entreprise :
{context}

---
Appel d'offres à analyser :
Titre : {offre.get('titre', 'N/A')}
Acheteur : {offre.get('acheteur', 'N/A')}
{budget_str}
Date limite : {offre.get('date_limite', 'N/A')}
Source : {offre.get('source', 'N/A')}

Description :
{offre.get('description', 'Pas de description disponible')[:2000]}

---
Réponds avec ce JSON (et uniquement ce JSON) :
{{
  "score": <nombre entre 0 et 10>,
  "resume": "<résumé de l'offre en 2 phrases>",
  "points_forts": ["<point 1>", "<point 2>", ...],
  "points_faibles": ["<point 1>", "<point 2>", ...],
  "recommandation": "<go | no_go | a_etudier>",
  "justification": "<explication courte de la note>"
}}

Critères de scoring :
- 8-10 : Offre idéale, forte adéquation métier, budget correct, délai raisonnable
- 5-7  : Intéressante mais avec des réserves (compétences partielles, budget incertain...)
- 0-4  : Peu pertinente (hors métier, budget trop faible, délai trop court...)
"""


def score_offre(offre: dict) -> dict:
    """Envoie une offre à Claude et retourne le score structuré."""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": build_user_prompt(offre, COMPANY_CONTEXT)}
            ]
        )

        raw = message.content[0].text
        # Nettoyage au cas où des backticks seraient présents
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(clean)

        # Validation minimale
        result.setdefault("score", 5)
        result.setdefault("resume", "")
        result.setdefault("points_forts", [])
        result.setdefault("points_faibles", [])
        result.setdefault("recommandation", "a_etudier")

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
