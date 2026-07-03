"""
parser.py — Extraction des données depuis les pages HTML Piter

C'est ici que tu adaptes les sélecteurs CSS/HTML selon la structure réelle du site.
Ouvre l'inspecteur de ton navigateur (F12) pour identifier les bons sélecteurs.
"""

from datetime import datetime
from bs4 import BeautifulSoup, Tag
from loguru import logger


# ─────────────────────────────────────────────
# Structure d'un appel d'offres
# ─────────────────────────────────────────────
def _empty_ao() -> dict:
    return {
        "titre": None,
        "reference": None,
        "acheteur": None,
        "localisation": None,
        "type_marche": None,
        "categorie": None,
        "etat": None,
        "lien": None,
        "date_scraping": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ─────────────────────────────────────────────
# Parser d'une carte / ligne AO (page liste)
# ─────────────────────────────────────────────
def parse_ao_card(card: Tag, base_url: str = "") -> dict:
    """
    Extrait les données d'une ligne <tr class="js-consultation-list"> de la page liste Piter.
    Colonnes : favori | référence | client | entité | mission | niveau | lieu | prix | état | canal
    """
    data = _empty_ao()

    try:
        tds = card.find_all("td", recursive=False)
        if len(tds) < 9:
            return data

        # ── Référence (AO number) ─────────────────────
        ref_td = tds[1]
        data["reference"] = ref_td.get_text(strip=True)
        data["titre"] = ref_td.get("data-modal-title", data["reference"])

        # ── Client ────────────────────────────────────
        # Le nom complet est dans le tooltip .js-tooltip-content du div clientTT*
        client_tooltip = tds[2].select_one(".js-tooltip-content")
        if client_tooltip:
            data["acheteur"] = client_tooltip.get_text(strip=True)

        # ── Entité ────────────────────────────────────
        entity_tooltip = tds[3].select_one(".js-tooltip-content")
        if entity_tooltip:
            data["categorie"] = entity_tooltip.get_text(strip=True)
        else:
            entity_span = tds[3].select_one("span.min-w-32")
            if entity_span:
                data["categorie"] = entity_span.get_text(strip=True)

        # ── Mission ───────────────────────────────────
        mission_span = tds[4].select_one("span.min-w-32")
        if mission_span:
            data["type_marche"] = mission_span.get_text(strip=True)

        # ── Lieu ──────────────────────────────────────
        lieu_td = tds[6]
        data["localisation"] = lieu_td.get_text(strip=True)

        # ── État ──────────────────────────────────────
        etat_span = tds[8].select_one(".badge")
        if etat_span:
            data["etat"] = etat_span.get_text(strip=True)

        # ── Lien vers le détail ───────────────────────
        # data-url sur le <tr> lui-même
        href = card.get("data-url", "")
        if href:
            data["lien"] = href if href.startswith("http") else base_url + href

    except Exception as e:
        logger.warning(f"Erreur parsing carte AO : {e}")

    return data


# ─────────────────────────────────────────────
# Parser de la page détail (optionnel)
# ─────────────────────────────────────────────
def parse_ao_detail(soup: BeautifulSoup) -> dict:
    """
    Extrait les données supplémentaires depuis la page détail d'un AO.
    Appelé uniquement si tu veux aller chercher plus d'info que la liste.

    ⚠️ À ADAPTER selon la structure de la page détail.
    """
    data = {}

    try:
        # Exemple : description complète
        desc_el = soup.select_one(".ao-description, .description, article p")
        if desc_el:
            data["description"] = desc_el.get_text(strip=True)

        # Exemple : valeur estimée du marché
        valeur_el = soup.select_one(".ao-valeur, .montant, .valeur-estimee")
        if valeur_el:
            data["valeur_estimee"] = valeur_el.get_text(strip=True)

        # Exemple : code CPV
        cpv_el = soup.select_one(".cpv, .code-cpv")
        if cpv_el:
            data["code_cpv"] = cpv_el.get_text(strip=True)

    except Exception as e:
        logger.warning(f"Erreur parsing détail AO : {e}")

    return data


# ─────────────────────────────────────────────
# Parsing des pages de liste complètes
# ─────────────────────────────────────────────
def parse_ao_list_page(soup: BeautifulSoup, base_url: str = "") -> list[dict]:
    """
    Extrait tous les AO d'une page de liste.

    ⚠️ Remplace le sélecteur ".ao-card" par celui qui correspond
    au container de chaque appel d'offres dans la liste.
    """
    # Chaque AO est une ligne <tr class="js-consultation-list"> dans le tableau
    cards = soup.select("tr.js-consultation-list")

    if not cards:
        all_trs = soup.find_all("tr")
        logger.warning(
            f"Aucune carte AO trouvée — {len(all_trs)} <tr> dans la page, "
            f"titre HTML: {soup.title.string if soup.title else 'N/A'}"
        )
        return []

    results = []
    for card in cards:
        ao_data = parse_ao_card(card, base_url=base_url)
        if ao_data["titre"]:  # on filtre les cartes vides
            results.append(ao_data)

    logger.debug(f"{len(results)} AO extraits de cette page")
    return results

