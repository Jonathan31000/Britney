"""
scraper/rules.py — Filtrage des offres par règles métier (par utilisateur)
"""
from datetime import date, datetime
import re
from typing import Optional


def _extract_tjm(text: str) -> Optional[float]:
    """Détecte un TJM dans un texte. Retourne None si non trouvé."""
    matches = re.findall(r'(\d{3,4})\s*€', text)
    values = [float(m) for m in matches if 100 <= float(m) <= 5000]
    return max(values) if values else None


def apply_rules(offre: dict, rules: dict) -> tuple[bool, str]:
    """
    Applique les règles métier d'un utilisateur à une offre.

    Args:
        offre: dict avec titre, description, budget_max, date_limite
        rules: dict chargé depuis user_config (keywords_include, etc.)

    Returns:
        (passed: bool, reason: str)
    """
    text = f"{offre.get('titre', '')} {offre.get('description', '')}".lower()

    # 1. Mots-clés exclus (prioritaire)
    for kw in rules.get("keywords_exclude", []):
        if kw.lower() in text:
            return False, f"mot_exclu:{kw}"

    # 2. Mots-clés obligatoires
    includes = rules.get("keywords_include", [])
    if includes:
        if not any(kw.lower() in text for kw in includes):
            return False, "aucun_mot_cle_obligatoire"

    # 3. Budget
    budget_min = rules.get("budget_min")
    budget_max = rules.get("budget_max")
    if budget_min is not None or budget_max is not None:
        tjm = offre.get("budget_max") or _extract_tjm(offre.get("description", ""))
        if tjm is not None:
            if budget_min and tjm < budget_min:
                return False, f"tjm_trop_bas:{tjm}"
            if budget_max and tjm > budget_max:
                return False, f"tjm_trop_eleve:{tjm}"

    # 4. Délai minimum
    min_days = rules.get("min_days_remaining", 0)
    if min_days and min_days > 0:
        date_limite = offre.get("date_limite")
        if date_limite:
            try:
                dl = datetime.strptime(date_limite, "%Y-%m-%d").date()
                remaining = (dl - date.today()).days
                if remaining < min_days:
                    return False, f"delai_trop_court:{remaining}j"
            except ValueError:
                pass

    return True, "ok"


def load_rules_for_user(user_id: int) -> dict:
    """Charge les règles depuis la config de l'utilisateur."""
    from scraper.database import get_user_config
    return {
        "keywords_include":   get_user_config(user_id, "keywords_include") or [],
        "keywords_exclude":   get_user_config(user_id, "keywords_exclude") or [],
        "budget_min":         get_user_config(user_id, "budget_min"),
        "budget_max":         get_user_config(user_id, "budget_max"),
        "min_days_remaining": get_user_config(user_id, "min_days_remaining") or 0,
        "ai_score_threshold": get_user_config(user_id, "ai_score_threshold") or 4.0,
    }