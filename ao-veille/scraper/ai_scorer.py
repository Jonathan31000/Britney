"""
scraper/ai_scorer.py — Scoring Claude API par utilisateur
"""
import json
import os
import re

import anthropic

from scraper.database import (
    get_offres_to_score,
    get_user_config,
    insert_log,
    insert_score,
    list_users,
)


def _build_prompt(offre: dict, company_context: str, prompt_template: str) -> str:
    budget = offre.get("budget_max")
    budget_str = f"{budget:.0f}" if budget else "non renseigné"
    return prompt_template.format(
        company_context=company_context,
        titre=offre.get("titre", ""),
        acheteur=offre.get("acheteur", ""),
        budget=budget_str,
        date_limite=offre.get("date_limite", "non renseignée"),
        description=offre.get("description", ""),
    )


def _parse_score_response(text: str) -> dict:
    """Parse la réponse JSON de Claude, tolère les backticks markdown."""
    clean = re.sub(r"```json|```", "", text).strip()
    return json.loads(clean)


def _recommandation_from_score(score: float, go_threshold: float, etudier_threshold: float) -> str:
    if score >= go_threshold:
        return "go"
    if score >= etudier_threshold:
        return "a_etudier"
    return "no_go"


def run_scorer(user_id: int) -> dict:
    """
    Score toutes les offres en attente pour un utilisateur donné.
    Utilise sa propre config (company_context, prompt, seuils).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        insert_log("scorer", "score_skip", "ANTHROPIC_API_KEY manquante", user_id=user_id)
        return {"total": 0, "ok": 0, "errors": 0, "skipped": "no_api_key"}

    # Charger la config du user
    company_context   = get_user_config(user_id, "company_context") or ""
    prompt_template   = get_user_config(user_id, "prompt_template") or ""
    go_threshold      = float(get_user_config(user_id, "score_go_threshold") or 8.0)
    etudier_threshold = float(get_user_config(user_id, "score_etudier_threshold") or 5.0)

    if not company_context or not prompt_template:
        insert_log("scorer", "score_skip", "company_context ou prompt_template manquant",
                   user_id=user_id)
        return {"total": 0, "ok": 0, "errors": 0, "skipped": "config_incomplete"}

    # Offres à scorer pour ce user
    offres = get_offres_to_score(user_id)
    if not offres:
        return {"total": 0, "ok": 0, "errors": 0}

    client = anthropic.Anthropic(api_key=api_key)
    ok = 0
    errors = 0

    for offre in offres:
        try:
            user_prompt = _build_prompt(offre, company_context, prompt_template)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system=(
                    "Tu es un expert en réponse aux appels d'offres publics et privés. "
                    "Tu analyses des offres de marché et évalues leur pertinence. "
                    "Tu réponds UNIQUEMENT en JSON valide, sans markdown, sans texte supplémentaire."
                ),
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw = message.content[0].text
            data = _parse_score_response(raw)

            score_val = float(data.get("score", 0))
            reco = data.get("recommandation") or _recommandation_from_score(
                score_val, go_threshold, etudier_threshold
            )

            insert_score(
                offre_id=offre["id"],
                user_id=user_id,
                score=score_val,
                resume=data.get("resume", ""),
                points_forts=data.get("points_forts", []),
                points_faibles=data.get("points_faibles", []),
                recommandation=reco,
            )
            ok += 1

        except json.JSONDecodeError as e:
            errors += 1
            insert_log("scorer", "score_error",
                       json.dumps({"offre_id": offre["id"], "error": f"JSON invalide: {e}"}),
                       user_id=user_id)
        except Exception as e:
            errors += 1
            insert_log("scorer", "score_error",
                       json.dumps({"offre_id": offre["id"], "error": str(e)}),
                       user_id=user_id)

    result = {"total": len(offres), "ok": ok, "errors": errors}
    insert_log("scorer", "run_done", json.dumps(result), user_id=user_id)
    return result


def run_scorer_all_users() -> dict:
    """Lance le scoring pour tous les commerciaux actifs. Utilisé par le scheduler."""
    users = [u for u in list_users() if u["actif"] and u["role"] == "commercial"]
    results = {}
    for user in users:
        results[user["email"]] = run_scorer(user["id"])
    return results