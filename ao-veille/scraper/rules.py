"""
scraper/rules.py
Filtrage par règles métier AVANT le scoring IA.
"""
import yaml
import re
from datetime import datetime, date
from typing import Tuple


def load_rules(path: str = "config/rules.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize(text: str) -> str:
    return text.lower().strip() if text else ""


def apply_rules(offre: dict, rules: dict) -> Tuple[bool, str]:
    """
    Applique les règles sur une offre.
    Retourne (True, "") si OK, (False, "raison") si rejetée.
    """
    texte = _normalize(f"{offre.get('titre','')} {offre.get('description','')}")

    # 1. Mots-clés exclus
    for kw in rules.get("keywords_exclude", []):
        if kw.lower() in texte:
            return False, f"mot-clé exclu : '{kw}'"

    # 2. Mots-clés obligatoires (au moins un)
    includes = rules.get("keywords_include", [])
    if includes:
        found = any(kw.lower() in texte for kw in includes)
        if not found:
            return False, "aucun mot-clé obligatoire trouvé"

    # 3. Budget
    budget_min_rule = rules.get("budget_min")
    budget_max_rule = rules.get("budget_max")
    offre_budget_max = offre.get("budget_max")
    offre_budget_min = offre.get("budget_min")

    if budget_min_rule and offre_budget_max is not None:
        if offre_budget_max < budget_min_rule:
            return False, f"budget trop faible ({offre_budget_max} < {budget_min_rule})"

    if budget_max_rule and offre_budget_min is not None:
        if offre_budget_min > budget_max_rule:
            return False, f"budget trop élevé ({offre_budget_min} > {budget_max_rule})"

    # 4. Délai restant
    min_days = rules.get("min_days_remaining", 0)
    date_limite_str = offre.get("date_limite")
    if date_limite_str and min_days > 0:
        try:
            # Accepte plusieurs formats
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    dl = datetime.strptime(date_limite_str, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                dl = None

            if dl:
                remaining = (dl - date.today()).days
                if remaining < min_days:
                    return False, f"délai trop court ({remaining} jours restants)"
        except Exception:
            pass  # date non parseable → on laisse passer

    return True, ""
