"""
scraper/database.py
Gestion de la base SQLite : création, insertion, lecture des offres.
"""
import sqlite3
import hashlib
import json
import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./data/offres.db")

# ---------------------------------------------------------------------------
# Valeurs par défaut de la config (V2)
# ---------------------------------------------------------------------------

DEFAULT_PROMPT_TEMPLATE = """Contexte de notre entreprise :
{company_context}

---
Appel d'offres à analyser :
Titre : {titre}
Acheteur : {acheteur}
Budget estimé : {budget} €
Date limite : {date_limite}
Source : {source}

Description :
{description}

---
Réponds avec ce JSON (et uniquement ce JSON) :
{{
  "score": <nombre entre 0 et 10>,
  "resume": "<résumé de l'offre en 2 phrases>",
  "points_forts": ["<point 1>", "<point 2>"],
  "points_faibles": ["<point 1>", "<point 2>"],
  "recommandation": "<go | no_go | a_etudier>",
  "justification": "<explication courte de la note>"
}}

Critères de scoring :
- 8-10 : Offre idéale, forte adéquation métier, budget correct, délai raisonnable
- 5-7  : Intéressante mais avec des réserves (compétences partielles, budget incertain...)
- 0-4  : Peu pertinente (hors métier, budget trop faible, délai trop court...)"""

CONFIG_DEFAULTS = [
    # (key, value_as_json, label, section)
    ("keywords_include",       json.dumps(["développement", "java", "python", "data"]),
     "Mots-clés obligatoires", "filtrage"),
    ("keywords_exclude",       json.dumps([]),
     "Mots-clés exclus",       "filtrage"),
    ("budget_min",             json.dumps(None),
     "TJM minimum (€)",        "filtrage"),
    ("budget_max",             json.dumps(None),
     "TJM maximum (€)",        "filtrage"),
    ("min_days_remaining",     json.dumps(0),
     "Délai minimum (jours)",  "filtrage"),
    ("ai_score_threshold",     json.dumps(4.0),
     "Score minimum affiché",  "filtrage"),
    ("company_context",        json.dumps("Entreprise généraliste en services informatiques."),
     "Contexte entreprise",    "scoring"),
    ("prompt_template",        json.dumps(DEFAULT_PROMPT_TEMPLATE),
     "Template du prompt IA",  "scoring"),
    ("score_go_threshold",     json.dumps(8.0),
     "Seuil score GO",         "scoring"),
    ("score_etudier_threshold", json.dumps(5.0),
     "Seuil score À étudier",  "scoring"),
]


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS offres (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            hash        TEXT UNIQUE NOT NULL,
            source      TEXT NOT NULL,
            titre       TEXT NOT NULL,
            description TEXT,
            acheteur    TEXT,
            budget_min  REAL,
            budget_max  REAL,
            date_limite TEXT,
            date_pub    TEXT,
            url         TEXT,
            statut      TEXT DEFAULT 'nouveau',
            raw_json    TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS scores (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            offre_id       INTEGER NOT NULL REFERENCES offres(id),
            score          REAL,
            resume         TEXT,
            points_forts   TEXT,
            points_faibles TEXT,
            recommandation TEXT,
            created_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            source     TEXT,
            event      TEXT,
            detail     TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS config (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            label      TEXT,
            section    TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_offres_statut ON offres(statut);
        CREATE INDEX IF NOT EXISTS idx_offres_source ON offres(source);
        CREATE INDEX IF NOT EXISTS idx_offres_date   ON offres(date_limite);
    """)

    conn.commit()
    _init_config_defaults(conn)
    conn.commit()
    _migrate_v1_config(conn)
    conn.commit()
    conn.close()
    print(f"[DB] Base initialisée : {DB_PATH}")


def _init_config_defaults(conn: sqlite3.Connection):
    """Insère les valeurs par défaut uniquement si elles n'existent pas encore."""
    conn.executemany(
        """INSERT OR IGNORE INTO config (key, value, label, section, updated_at)
           VALUES (?, ?, ?, ?, datetime('now'))""",
        CONFIG_DEFAULTS,
    )


def _migrate_v1_config(conn: sqlite3.Connection):
    """
    Migration V1→V2 : importe rules.yaml et COMPANY_CONTEXT depuis .env
    dans la table config, uniquement si les valeurs sont encore celles par défaut.
    """
    # Contexte entreprise depuis .env
    ctx = os.getenv("COMPANY_CONTEXT", "").strip()
    if ctx:
        row = conn.execute("SELECT value FROM config WHERE key='company_context'").fetchone()
        current = json.loads(row["value"]) if row else ""
        if current == "Entreprise généraliste en services informatiques.":
            conn.execute(
                "UPDATE config SET value=?, updated_at=datetime('now') WHERE key='company_context'",
                (json.dumps(ctx),)
            )

    # rules.yaml
    rules_path = "config/rules.yaml"
    if os.path.exists(rules_path):
        try:
            import yaml
            with open(rules_path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f) or {}

            mapping = {
                "keywords_include":   ("keywords_include",   []),
                "keywords_exclude":   ("keywords_exclude",   []),
                "budget_min":         ("budget_min",         None),
                "budget_max":         ("budget_max",         None),
                "min_days_remaining": ("min_days_remaining", 0),
                "ai_score_threshold": ("ai_score_threshold", 4.0),
            }
            for yaml_key, (db_key, default_val) in mapping.items():
                if yaml_key in rules:
                    row = conn.execute(
                        "SELECT value FROM config WHERE key=?", (db_key,)
                    ).fetchone()
                    current = json.loads(row["value"]) if row else None
                    if current == default_val:
                        conn.execute(
                            "UPDATE config SET value=?, updated_at=datetime('now') WHERE key=?",
                            (json.dumps(rules[yaml_key]), db_key)
                        )
        except Exception as e:
            print(f"[DB] Avertissement migration rules.yaml : {e}")


# ---------------------------------------------------------------------------
# Config get / set
# ---------------------------------------------------------------------------

def get_config(key: str):
    """Retourne la valeur désérialisée d'un paramètre de config."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        if row is None:
            raise KeyError(f"Clé de config inconnue : '{key}'")
        return json.loads(row["value"])
    finally:
        conn.close()


def set_config(key: str, value):
    """Met à jour un paramètre de config (valeur Python → JSON en base)."""
    conn = get_connection()
    try:
        result = conn.execute(
            "UPDATE config SET value=?, updated_at=datetime('now') WHERE key=?",
            (json.dumps(value, ensure_ascii=False), key)
        )
        if result.rowcount == 0:
            raise KeyError(f"Clé de config inconnue : '{key}'")
        conn.commit()
    finally:
        conn.close()


def get_all_config() -> dict:
    """Retourne toute la config regroupée par section."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT key, value, label, section, updated_at FROM config ORDER BY section, key"
        ).fetchall()
        result = {}
        for row in rows:
            section = row["section"] or "autre"
            if section not in result:
                result[section] = {}
            result[section][row["key"]] = {
                "value":      json.loads(row["value"]),
                "label":      row["label"],
                "updated_at": row["updated_at"],
            }
        return result
    finally:
        conn.close()


def reset_config():
    """Remet tous les paramètres à leurs valeurs par défaut."""
    conn = get_connection()
    try:
        conn.executemany(
            "UPDATE config SET value=?, updated_at=datetime('now') WHERE key=?",
            [(val, key) for key, val, *_ in CONFIG_DEFAULTS]
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Offres
# ---------------------------------------------------------------------------

def compute_hash(offre: dict) -> str:
    key = f"{offre.get('titre','')}{offre.get('acheteur','')}{offre.get('date_limite','')}".lower().strip()
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def insert_offre(offre: dict) -> Optional[int]:
    offre["hash"] = compute_hash(offre)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO offres (hash, source, titre, description, acheteur,
                                budget_min, budget_max, date_limite, date_pub, url, raw_json)
            VALUES (:hash, :source, :titre, :description, :acheteur,
                    :budget_min, :budget_max, :date_limite, :date_pub, :url, :raw_json)
        """, {
            "hash":        offre["hash"],
            "source":      offre.get("source", "inconnu"),
            "titre":       offre.get("titre", ""),
            "description": offre.get("description", ""),
            "acheteur":    offre.get("acheteur", ""),
            "budget_min":  offre.get("budget_min"),
            "budget_max":  offre.get("budget_max"),
            "date_limite": offre.get("date_limite"),
            "date_pub":    offre.get("date_pub"),
            "url":         offre.get("url", ""),
            "raw_json":    json.dumps(offre, ensure_ascii=False),
        })
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def update_statut(offre_id: int, statut: str):
    conn = get_connection()
    conn.execute(
        "UPDATE offres SET statut=?, updated_at=datetime('now') WHERE id=?",
        (statut, offre_id)
    )
    conn.commit()
    conn.close()


def insert_score(offre_id: int, score_data: dict):
    conn = get_connection()
    conn.execute("""
        INSERT INTO scores (offre_id, score, resume, points_forts, points_faibles, recommandation)
        VALUES (:offre_id, :score, :resume, :points_forts, :points_faibles, :recommandation)
    """, {
        "offre_id":       offre_id,
        "score":          score_data.get("score"),
        "resume":         score_data.get("resume"),
        "points_forts":   json.dumps(score_data.get("points_forts", []), ensure_ascii=False),
        "points_faibles": json.dumps(score_data.get("points_faibles", []), ensure_ascii=False),
        "recommandation": score_data.get("recommandation"),
    })
    conn.commit()
    conn.close()


def get_offres_a_scorer():
    conn = get_connection()
    rows = conn.execute("""
        SELECT o.* FROM offres o
        LEFT JOIN scores s ON s.offre_id = o.id
        WHERE o.statut = 'filtre_ok' AND s.id IS NULL
        ORDER BY o.created_at DESC
        LIMIT 50
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_event(source: str, event: str, detail: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO logs (source, event, detail) VALUES (?, ?, ?)",
        (source, event, detail)
    )
    conn.commit()
    conn.close()