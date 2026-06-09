"""
scraper/ai_scorer.py
Scoring des appels d'offres.
- Si ANTHROPIC_API_KEY est configurée → scoring via Claude (IA)
- Sinon → scoring basé sur les mots-clés configurés (règles)
"""
import os
import json
import logging
from dotenv import load_dotenv

from .database import get_offres_a_scorer, get_config, insert_score, update_statut, log_event

load_dotenv()
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_AI_ENABLED = bool(ANTHROPIC_API_KEY and not ANTHROPIC_API_KEY.startswith("sk-ant-..."))

SYSTEM_PROMPT = """Tu es un expert en réponse aux appels d'offres publics et privés.
Tu analyses des offres de marché et évalues leur pertinence pour une entreprise donnée.
Tu réponds UNIQUEMENT en JSON valide, sans markdown, sans texte supplémentaire."""


# ---------------------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return text.lower() if text else ""


def _recommandation_from_score(score: float) -> str:
    go_threshold      = get_config("score_go_threshold") or 8
    etudier_threshold = get_config("score_etudier_threshold") or 5
    if score >= go_threshold:
        return "go"
    if score >= etudier_threshold:
        return "a_etudier"
    return "no_go"


# ---------------------------------------------------------------------------
# Scoring par règles (sans IA)
# ---------------------------------------------------------------------------

def _score_par_regles(offre: dict) -> dict:
    keywords_include = get_config("keywords_include") or []
    keywords_exclude = get_config("keywords_exclude") or []

    titre         = _normalize(offre.get("titre", ""))
    description   = _normalize(offre.get("description", ""))
    texte_complet = f"{titre} {description}"

    for kw in keywords_exclude:
        if kw.lower() in texte_complet:
            return {
                "score": 1,
                "resume": f"Offre rejetée — mot-clé exclu : « {kw} »",
                "points_forts": [],
                "points_faibles": [f"Contient le mot-clé exclu : {kw}"],
                "recommandation": "no_go",
            }

    if not keywords_include:
        return {
            "score": 5,
            "resume": "Aucun critère configuré — offre à étudier manuellement.",
            "points_forts": [],
            "points_faibles": [],
            "recommandation": "a_etudier",
        }

    title_matches = [kw for kw in keywords_include if kw.lower() in titre]
    desc_matches  = [kw for kw in keywords_include if kw.lower() in description and kw not in title_matches]

    # Trouvé dans le titre → GO, dans la description → À étudier, nulle part → NO GO
    score = 3 + min(6, len(title_matches) * 5) + min(4, len(desc_matches) * 3)
    score = round(min(10.0, score), 1)

    if not title_matches and not desc_matches:
        resume = "Aucun mot-clé recherché trouvé dans cette offre."
    else:
        mots = ", ".join(f"« {k} »" for k in title_matches + desc_matches)
        resume = f"{len(title_matches) + len(desc_matches)} mot(s)-clé(s) trouvé(s) : {mots}."

    return {
        "score": score,
        "resume": resume,
        "points_forts": [f"Contient : {k}" for k in title_matches + desc_matches],
        "points_faibles": [] if title_matches or desc_matches else ["Aucun mot-clé correspondant"],
        "recommandation": _recommandation_from_score(score),
    }


# ---------------------------------------------------------------------------
# Scoring par IA (Claude)
# ---------------------------------------------------------------------------

def _build_prompt(offre: dict) -> str:
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


def _score_par_ia(offre: dict) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(offre)}]
    )

    raw   = message.content[0].text
    clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    result = json.loads(clean)

    result.setdefault("score", 5)
    result.setdefault("resume", "")
    result.setdefault("points_forts", [])
    result.setdefault("points_faibles", [])

    score = float(result["score"])
    result["recommandation"] = _recommandation_from_score(score)
    return result


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def score_offre(offre: dict, force_mode: str = "auto") -> dict:
    use_ai = (force_mode == "ai") or (force_mode == "auto" and _AI_ENABLED)
    if use_ai:
        try:
            return _score_par_ia(offre)
        except Exception as e:
            logger.warning(f"[scorer] IA indisponible ({e}) — fallback règles")
    return _score_par_regles(offre)


def run_scorer(force_mode: str = "auto"):
    use_ai = (force_mode == "ai") or (force_mode == "auto" and _AI_ENABLED)
    mode_label = "IA (Claude)" if use_ai else "règles (sans IA)"
    offres = get_offres_a_scorer()
    logger.info(f"[scorer] mode demandé : {force_mode} → {mode_label}")
    logger.info(f"[scorer] {len(offres)} offre(s) à scorer — mode : {mode_label}")

    stats = {"total": len(offres), "ok": 0, "errors": 0, "mode": mode_label}

    for offre in offres:
        try:
            score_data = score_offre(offre, force_mode=force_mode)
            insert_score(offre["id"], score_data)
            update_statut(offre["id"], "scored")
            stats["ok"] += 1
            logger.info(f"[scorer] #{offre['id']} score={score_data['score']} reco={score_data['recommandation']}")
        except Exception as e:
            logger.error(f"[scorer] Erreur offre #{offre['id']} : {e}")
            stats["errors"] += 1

    log_event("scorer", "run_done", json.dumps(stats))
    logger.info(f"[scorer] Terminé : {stats}")
    return stats
