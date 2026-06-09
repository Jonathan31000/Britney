# Journal des modifications — AO Veille

## Session du 09 juin 2026

---

### 1. Correction du chemin `cookies.json` (relatif → absolu)
**Fichiers :** `scraper/piter_scraper.py`, `scraper/auth_playwright.py`

**Problème :** Le chemin `cookies.json` était relatif au dossier de lancement du script. Selon depuis quel répertoire on lançait l'application, le fichier n'était pas trouvé.

**Correction :**
```python
# Avant
COOKIES_FILE = "cookies.json"

# Après
COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.json")
```

---

### 2. Suppression de la fonction dupliquée `load_session_from_cookies`
**Fichier :** `scraper/piter_scraper.py`

**Problème :** La fonction était définie deux fois dans le même fichier. La première version (sans Playwright) était écrasée par la seconde, rendant le code confus et source d'erreurs futures.

**Correction :** Suppression de la première définition (incomplète). Seule la version avec les 4 méthodes de connexion est conservée.

---

### 3. Correction du login — suppression du champ `login[recaptcha]`
**Fichier :** `scraper/piter_scraper.py`

**Problème :** Le payload de connexion envoyait `login[recaptcha]=""` (valeur vide). Piter.at interprète ce champ vide comme une tentative de contournement du reCAPTCHA et bloque la connexion.

**Correction :** Le champ `login[recaptcha]` est simplement absent du payload. Le serveur n'exige pas ce champ si on ne l'envoie pas.

```python
# Avant
payload = {
    "login[email]":     EMAIL,
    "login[password]":  PASSWORD,
    "login[_token]":    csrf,
    "login[recaptcha]": "",  # ← déclenchait le blocage
}

# Après
payload = {
    "login[email]":     EMAIL,
    "login[password]":  PASSWORD,
    "login[_token]":    csrf,
}
```

---

### 4. Correction de l'URL dans `.env`
**Fichier :** `.env`

**Problème :** `PITER_BASE_URL=https://app.piter.at` — ce sous-domaine n'existe pas. Le domaine correct est `https://piter.at`.

---

### 5. Installation de Playwright + Chromium
**Fichier :** `requirements.txt`

**Problème :** Playwright était utilisé dans le code comme fallback d'authentification mais n'était jamais installé.

**Correction :** Ajout de `playwright>=1.44.0` dans `requirements.txt` et installation du navigateur Chromium via `playwright install chromium`.

---

### 6. Scraping : suppression du filtre par mots-clés obligatoires
**Fichier :** `scraper/piter_scraper.py`

**Problème :** Le scraper filtrait les offres par mots-clés AVANT de les sauvegarder. Si le mot-clé était trop restrictif, presque rien n'était sauvegardé. De plus, ce filtre doublonnait le scoring.

**Décision :** Tout scraper sans filtre (sauf mots-clés exclus), puis laisser le scoring décider de la pertinence. Adapté car piter.at ne dépasse pas ~300 offres.

```python
# Avant : filtre obligatoire pendant le scraping
ok, raison = apply_rules(offre, rules)
if not ok:
    continue

# Après : seuls les mots exclus bloquent
excluded = any(kw.lower() in texte for kw in rules.get("keywords_exclude", []))
if excluded:
    continue
```

---

### 7. Scorer IA remplacé par un scorer hybride (règles + IA)
**Fichier :** `scraper/ai_scorer.py`

**Problème :** Le scorer utilisait exclusivement l'API Anthropic (Claude). Sans clé API valide, il échouait silencieusement et aucune offre n'était scorée.

**Correction :** Scorer hybride avec détection automatique :
- Si `ANTHROPIC_API_KEY` est configurée → scoring via Claude
- Sinon → scoring par règles (mots-clés)
- Si l'IA échoue → fallback automatique sur les règles

**Logique du scoring par règles :**
- Mot-clé trouvé dans le **titre** → score ≥ 8 → **GO**
- Mot-clé trouvé dans la **description** → score ≥ 6 → **À étudier**
- Aucun mot-clé → score 3 → **NO GO**

---

### 8. Endpoint API `/api/offres/count`
**Fichier :** `api/main.py`

**Ajout :** Nouvel endpoint qui retourne le nombre d'offres correspondant aux filtres actifs. Permet d'afficher "X résultats" sur la page Appels d'offres en temps réel.

---

### 9. Endpoint API `/api/trigger/score` — paramètres `mode` et `reset`
**Fichier :** `api/main.py`

**Ajout :**
- `?mode=rules` ou `?mode=ai` — choisir le moteur de scoring
- `?reset=true` — réinitialise les anciens scores avant de rescorer (utile quand on change les mots-clés)

---

### 10. Suppression de la limite de 50 dans `get_offres_a_scorer`
**Fichier :** `scraper/database.py`

**Problème :** La requête avait `LIMIT 50`, prévu pour ne pas surcharger l'API Claude. En mode règles, cette limite n'a aucune utilité et forçait à lancer le scoring plusieurs fois pour traiter toutes les offres.

---

### 11. Ajout du champ `scoring_mode` en base de données
**Fichier :** `scraper/database.py`

**Ajout :** Nouvelle clé de configuration `scoring_mode` (`"rules"` par défaut, `"ai"` si l'IA est activée). Persiste le choix de l'utilisateur entre les sessions.

---

### 12. Page Paramètres — toggle mode de scoring + bouton "Lancer le scoring"
**Fichier :** `frontend/src/pages/Parametres.jsx`

**Ajout :**
- Toggle visuel **"⧖ Règles (sans IA)"** / **"◈ IA Claude"**
- Bouton **"Lancer le scoring"** qui utilise le mode sélectionné et réinitialise les anciens scores avant de relancer

---

### 13. Page Appels d'offres — compteur de résultats + bouton Rafraîchir
**Fichier :** `frontend/src/pages/Offres.jsx`

**Ajout :**
- Affichage "X résultat(s)" qui se met à jour avec chaque filtre
- Bouton **"↻ Rafraîchir"** pour recharger les données sans quitter la page

---

### 14. Dashboard — simplification
**Fichier :** `frontend/src/pages/Dashboard.jsx`

**Modification :** Suppression des boutons de scoring du tableau de bord. Le scoring se configure et se lance depuis la page **Paramètres**. Le dashboard garde uniquement **"↻ Lancer scraping"**.

---

### 15. Script de démarrage `start.sh`
**Fichier :** `start.sh`

**Ajout :** Script qui lance backend et frontend en une seule commande, libère le port 8000 si occupé, et arrête tout proprement avec Ctrl+C.

```bash
./start.sh
```

---

## Améliorations futures recommandées

### Court terme
- **Renouvellement automatique des cookies** : les cookies piter.at expirent tous les 5-30 jours. Playwright peut les renouveler automatiquement mais nécessite que le reCAPTCHA ne soit pas déclenché.
- **Notification quand de nouvelles offres arrivent** : email ou notification système après un scraping qui trouve de nouvelles offres.

### Moyen terme
- **Intégration IA (Claude)** : ajouter une clé `ANTHROPIC_API_KEY` valide dans `.env` pour activer le scoring intelligent basé sur le contexte de l'entreprise.
- **Export Excel** : l'ancien script (`piter-scraper`) générait un fichier Excel. Cette fonctionnalité peut être ajoutée à l'API (`/api/export/xlsx`).
- **Scraping automatique** : le scheduler (`scraper/scheduler.py`) est en place mais non activé. Peut être configuré pour scraper automatiquement toutes les N heures.

### Long terme
- **Multi-sources** : ajouter d'autres plateformes d'appels d'offres (Freelance.com, Malt, etc.) en suivant le même pattern que `piter_scraper.py`.
- **Tableau de bord enrichi** : graphiques d'évolution du nombre d'offres dans le temps, taux de matching par mot-clé.
