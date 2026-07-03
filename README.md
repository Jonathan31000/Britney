# 🔍 Piter AO Scraper

Scraper Python pour les appels d'offres du site Piter.

## Structure du projet

```
piter-scraper/
├── main.py               # Point d'entrée
├── inspect_site.py       # Outil d'inspection HTML (à lancer en premier)
├── requirements.txt
├── .env                  # Tes credentials (ne pas committer)
├── .env.example          # Template .env
├── .gitignore
├── src/
│   ├── auth.py           # Connexion et gestion de session
│   ├── scraper.py        # Navigation / récupération des pages
│   ├── parser.py         # Extraction des données (sélecteurs CSS)
│   └── exporter.py       # Export Excel / CSV
├── data/output/          # Fichiers générés
└── logs/                 # Logs de run
```

## Installation

```bash
# 1. Crée et active un venv
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows

# 2. Installe les dépendances
pip install -r requirements.txt

# 3. Configure tes credentials
cp .env.example .env
# Édite .env avec ton email et mot de passe Piter
```

## Usage

### Étape 1 — Inspecter le HTML (une seule fois)
```bash
python inspect_site.py
```
→ Ouvre `data/output/debug_page.html` pour identifier les sélecteurs CSS.  
→ Adapte les sélecteurs dans `src/parser.py`.

### Étape 2 — Lancer le scraper

```bash
# Scrape tout
python main.py

# Test sur 3 pages seulement
python main.py --max-pages 3

# Avec les pages détail (plus lent)
python main.py --detail

# Combiné
python main.py --max-pages 5 --detail
```

## Où adapter le code

| Quoi | Où |
|---|---|
| Noms des champs du formulaire de login | `src/auth.py` → `payload` |
| Détection de connexion réussie | `src/auth.py` → `_is_logged_in()` |
| Paramètre de pagination dans l'URL | `src/scraper.py` → `get_ao_list_page()` |
| Sélecteur du container d'un AO | `src/parser.py` → `parse_ao_list_page()` |
| Sélecteurs des champs d'un AO | `src/parser.py` → `parse_ao_card()` |
| Champs supplémentaires (page détail) | `src/parser.py` → `parse_ao_detail()` |

## Config `.env`

```env
PITER_EMAIL=ton.email@exemple.com
PITER_PASSWORD=ton_mot_de_passe
PITER_BASE_URL=https://www.piter.fr
PITER_LOGIN_URL=https://www.piter.fr/login
PITER_AO_URL=https://www.piter.fr/appels-offres
OUTPUT_FORMAT=excel    # ou csv
OUTPUT_DIR=data/output
```
