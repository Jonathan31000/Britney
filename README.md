# AO Veille — Guide de setup complet

Outil de veille automatique des appels d'offres avec scraping, filtrage par règles et scoring IA (Claude).

---

## Prérequis

- Windows 10/11, macOS, ou Linux
- Connexion internet

---

## ÉTAPE 1 — Installer Python 3.11+

### Windows
1. Télécharger Python sur https://www.python.org/downloads/
2. **IMPORTANT** : cocher "Add Python to PATH" pendant l'installation
3. Vérifier dans un terminal :
   ```
   python --version
   ```
   → doit afficher `Python 3.11.x` ou supérieur

### macOS
```bash
brew install python@3.11
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip
```

---

## ÉTAPE 2 — Installer Node.js 20+

Télécharger sur https://nodejs.org (version LTS recommandée)

Vérifier :
```
node --version   # v20.x.x
npm --version    # 10.x.x
```

---

## ÉTAPE 3 — Installer VSCode

1. Télécharger sur https://code.visualstudio.com
2. Installer les extensions recommandées (voir section VSCode ci-dessous)

---

## ÉTAPE 4 — Cloner / copier le projet

Copier le dossier `ao-veille` dans le répertoire de votre choix, par exemple :
- Windows : `C:\projets\ao-veille`
- macOS/Linux : `~/projets/ao-veille`

---

## ÉTAPE 5 — Ouvrir dans VSCode

```bash
code ao-veille
```

Ou : File → Open Folder → sélectionner le dossier `ao-veille`

---

## ÉTAPE 6 — Créer l'environnement virtuel Python

Dans le terminal VSCode (Ctrl+` pour l'ouvrir) :

```bash
# Se placer à la racine du projet
cd ao-veille

# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Windows :
venv\Scripts\activate
# macOS/Linux :
source venv/bin/activate

# Installer les dépendances Python
pip install -r requirements.txt
```

> VSCode devrait détecter automatiquement le venv. Si pas :
> Ctrl+Shift+P → "Python: Select Interpreter" → choisir `./venv/...`

---

## ÉTAPE 7 — Configurer les variables d'environnement

```bash
# Copier le fichier exemple
cp .env.example .env
```

Éditer le fichier `.env` avec vos vraies valeurs :

```env
PITER_EMAIL=votre@email.com
PITER_PASSWORD=votremotdepasse
PITER_BASE_URL=https://app.piter.at

ANTHROPIC_API_KEY=sk-ant-api03-...

COMPANY_CONTEXT=Décrivez votre entreprise ici pour que l'IA score correctement.
Exemple : ESN spécialisée en développement web et conseil, 20 personnes,
ciblons des marchés publics IT entre 50k et 300k euros.
```

> **Obtenir une clé API Anthropic** : https://console.anthropic.com → API Keys

---

## ÉTAPE 8 — Adapter les règles métier

Éditer `config/rules.yaml` selon votre activité :

```yaml
keywords_include:
  - développement
  - informatique
  - conseil
  # Ajoutez vos mots-clés métier

budget_min: 10000   # Ajustez selon votre cible
```

---

## ÉTAPE 9 — Installer les dépendances frontend

```bash
cd frontend
npm install
cd ..
```

---

## ÉTAPE 10 — Lancer le projet

Ouvrir **deux terminaux** dans VSCode (icône `+` dans le panel terminal) :

### Terminal 1 — Backend Python (API + Scheduler)

```bash
# Activer le venv si pas déjà fait
source venv/bin/activate   # ou venv\Scripts\activate sur Windows

# Initialiser la base de données
python -c "from scraper.database import init_db; init_db()"

# Lancer l'API FastAPI
python -m uvicorn api.main:app --reload --port 8000
```

L'API est disponible sur : http://localhost:8000
Documentation auto : http://localhost:8000/docs

### Terminal 2 — Frontend React

```bash
cd frontend
npm run dev
```

Le dashboard est disponible sur : **http://localhost:5173**

---

## ÉTAPE 11 — Premier scraping

Deux options :

### Option A — Depuis le dashboard
Aller sur http://localhost:5173 → cliquer **"↻ Lancer scraping"**

### Option B — En ligne de commande
```bash
python -c "from scraper.piter_scraper import run_scraper; run_scraper()"
```

### Lancer le scoring IA
```bash
python -c "from scraper.ai_scorer import run_scorer; run_scorer()"
```

### Lancer le scheduler automatique
```bash
python -m scraper.scheduler
```
Cela lancera un premier passage immédiatement, puis toutes les heures du lundi au vendredi.

---

## Configuration VSCode — Extensions recommandées

Installer depuis le menu Extensions (Ctrl+Shift+X) :

| Extension | ID | Utilité |
|-----------|-----|---------|
| Python | `ms-python.python` | Coloration, IntelliSense, debug Python |
| Pylance | `ms-python.vscode-pylance` | Autocomplétion Python avancée |
| ESLint | `dbaeumer.vscode-eslint` | Linting JavaScript/React |
| Prettier | `esbenp.prettier-vscode` | Formatage automatique |
| SQLite Viewer | `qwtel.sqlite-viewer` | Voir la base de données directement dans VSCode |
| REST Client | `humao.rest-client` | Tester l'API sans Postman |
| GitLens | `eamodio.gitlens` | Git avancé |
| Thunder Client | `rangav.vscode-thunder-client` | Client HTTP intégré |

---

## Configuration VSCode — settings.json recommandés

Ctrl+Shift+P → "Open User Settings (JSON)" et ajouter :

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[python]": {
    "editor.defaultFormatter": "ms-python.python"
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/node_modules": true,
    "**/.env": false
  }
}
```

---

## Debug — Adapter les sélecteurs CSS du scraper

Si les offres ne sont pas détectées, c'est normal : les sélecteurs dans `piter_scraper.py`
sont des hypothèses. Pour les ajuster :

1. **Inspecter piter.at dans Chrome/Firefox** :
   - Se connecter manuellement sur piter.at
   - Aller sur la page liste des consultations
   - Clic droit sur une carte d'offre → "Inspecter"
   - Chercher la classe CSS de la carte, du titre, de la date, etc.

2. **Tester manuellement** dans un fichier `debug_scraper.py` :
   ```python
   from scraper.piter_scraper import create_session, login
   from bs4 import BeautifulSoup

   session = create_session()
   if login(session):
       resp = session.get("https://app.piter.at/fr/consultations")
       soup = BeautifulSoup(resp.text, "lxml")
       print(soup.prettify()[:5000])  # Voir le HTML
   ```

3. **Mettre à jour les sélecteurs** dans `piter_scraper.py` dans la fonction
   `parse_offre_from_card()` selon ce que vous voyez dans l'inspecteur.

---

## Structure du projet

```
ao-veille/
├── scraper/
│   ├── piter_scraper.py    # Scraper piter.at (authentification + extraction)
│   ├── ai_scorer.py        # Scoring IA via Claude API
│   ├── rules.py            # Moteur de règles métier
│   ├── database.py         # SQLite (CRUD)
│   └── scheduler.py        # Planification automatique (APScheduler)
├── api/
│   └── main.py             # API REST FastAPI
├── frontend/
│   └── src/
│       ├── pages/          # Dashboard, Offres, OffreDetail, Logs
│       ├── components/     # ScoreBadge, Sidebar
│       └── hooks/          # useApi.js
├── config/
│   └── rules.yaml          # Règles de filtrage métier
├── data/
│   └── offres.db           # Base SQLite (créée automatiquement)
├── .env                    # Variables d'environnement (à créer)
└── requirements.txt        # Dépendances Python
```

---

## FAQ

**Q: L'API renvoie "Login échoué"**
→ Vérifier `PITER_EMAIL` et `PITER_PASSWORD` dans `.env`
→ Vérifier que `PITER_BASE_URL` est correct (avec ou sans `/fr`)
→ Lancer le debug scraper (voir section Debug)

**Q: "No module named scraper"**
→ S'assurer d'être à la racine du projet `ao-veille/` et que le venv est activé

**Q: Le frontend affiche "Failed to fetch"**
→ Vérifier que l'API Python tourne bien sur le port 8000
→ Vérifier le proxy dans `frontend/vite.config.js`

**Q: Le scoring IA coûte cher**
→ Ajuster les règles dans `config/rules.yaml` pour être plus sélectif avant le scoring
→ Réduire `max_tokens` dans `ai_scorer.py` si les résumés sont trop longs
