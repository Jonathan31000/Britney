"""
Analyse automatique d'une URL pour générer la config de scraping.
Flow : Playwright fetch → nettoyage HTML → Claude analyse → config JSON
"""

import json
import re
import os
import anthropic
from bs4 import BeautifulSoup


ANALYSIS_PROMPT = """Tu es un expert en scraping web. On te donne le HTML d'une page listant des appels d'offres ou des missions de conseil IT.

Ton rôle : identifier les sélecteurs CSS permettant d'extraire les données de chaque offre.

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown, sans texte supplémentaire.

Structure attendue :
{
  "source_name": "nom_court_sans_espaces",
  "display_name": "Nom Affiché",
  "confidence": 0.85,
  "notes": "Observations importantes sur la structure",
  "pagination": {
    "type": "query_param | path | none",
    "param": "page",
    "start": 1,
    "selector_next": "a.next-page"
  },
  "selectors": {
    "offer_row": "sélecteur CSS du bloc contenant une offre",
    "titre": "sélecteur CSS relatif au titre",
    "acheteur": "sélecteur CSS relatif à l'acheteur/client",
    "description": "sélecteur CSS relatif à la description",
    "date_limite": "sélecteur CSS relatif à la date limite",
    "budget": "sélecteur CSS relatif au budget/TJM",
    "url": "sélecteur CSS relatif au lien (attribut href)"
  },
  "field_patterns": {
    "date": "format détecté ex: DD/MM/YYYY",
    "budget": "pattern regex pour extraire le montant ex: (\\\\d+)\\\\s*€"
  },
  "auth_hint": "none | login_required | cookies_needed"
}

Si un champ n'est pas trouvé dans le HTML, mets null comme valeur du sélecteur.
Si la page semble nécessiter une authentification (page de login, contenu vide), indique auth_hint = "login_required".

HTML à analyser :
"""


def _clean_html(html: str, max_chars=15000) -> str:
    """Nettoie le HTML pour ne garder que le contenu utile."""
    soup = BeautifulSoup(html, "lxml")

    # Supprimer scripts, styles, meta, etc.
    for tag in soup(["script", "style", "meta", "link", "noscript",
                     "header", "footer", "nav"]):
        tag.decompose()

    # Garder seulement le body
    body = soup.find("body")
    if body:
        text = body.get_text(separator="\n", strip=True)
        clean = str(body)
    else:
        clean = str(soup)

    # Tronquer si trop long
    return clean[:max_chars]


async def fetch_with_playwright(url: str, cookies: list = None) -> dict:
    """Fetch une page avec Playwright (rendu JS complet)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"success": False, "error": "Playwright non installé. Lancer: playwright install chromium"}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        if cookies:
            await context.add_cookies(cookies)

        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)  # Attendre le JS
            html = await page.content()
            title = await page.title()
            final_url = page.url
        except Exception as e:
            await browser.close()
            return {"success": False, "error": str(e)}

        await browser.close()
        return {
            "success": True,
            "html": html,
            "title": title,
            "final_url": final_url,
            "redirected": final_url != url
        }


def analyze_with_claude(html: str, url: str) -> dict:
    """Envoie le HTML à Claude pour analyse et retourne la config JSON."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    clean = _clean_html(html)
    prompt = ANALYSIS_PROMPT + f"\nURL source : {url}\n\n{clean}"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system="Tu es un expert en scraping web. Tu réponds UNIQUEMENT en JSON valide.",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # Nettoyer éventuels backticks
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


def preview_offers(html: str, config: dict) -> list:
    """
    Extrait les 3 premières offres depuis le HTML en utilisant la config générée.
    Retourne une liste de dicts pour l'aperçu dashboard.
    """
    soup = BeautifulSoup(html, "lxml")
    selectors = config.get("selectors", {})

    row_sel = selectors.get("offer_row")
    if not row_sel:
        return []

    rows = soup.select(row_sel)[:3]
    previews = []

    for row in rows:
        offer = {}
        for field in ["titre", "acheteur", "description", "date_limite", "budget", "url"]:
            sel = selectors.get(field)
            if not sel:
                offer[field] = None
                continue
            el = row.select_one(sel)
            if not el:
                offer[field] = None
            elif field == "url":
                offer[field] = el.get("href") or el.get_text(strip=True)
            else:
                offer[field] = el.get_text(strip=True)
        previews.append(offer)

    return previews


# Point d'entrée synchrone pour FastAPI (qui tourne avec asyncio)
def analyze_url_sync(url: str, cookies: list = None) -> dict:
    import asyncio
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(fetch_with_playwright(url, cookies))
    loop.close()

    if not result["success"]:
        return {"success": False, "error": result["error"]}

    if result.get("redirected"):
        # Probablement redirigé vers login
        pass

    html = result["html"]

    try:
        config = analyze_with_claude(html, url)
    except Exception as e:
        return {"success": False, "error": f"Erreur analyse Claude: {e}"}

    previews = preview_offers(html, config)

    return {
        "success": True,
        "config": config,
        "preview": previews,
        "html_title": result.get("title"),
        "final_url": result.get("final_url")
    }