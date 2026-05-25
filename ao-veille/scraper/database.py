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


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
            statut      TEXT DEFAULT 'nouveau',  -- nouveau | filtre_ok | filtre_ko | scored
            raw_json    TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS scores (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            offre_id    INTEGER NOT NULL REFERENCES offres(id),
            score       REAL,
            resume      TEXT,
            points_forts TEXT,
            points_faibles TEXT,
            recommandation TEXT,  -- go | no_go | a_etudier
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT,
            event       TEXT,
            detail      TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_offres_statut ON offres(statut);
        CREATE INDEX IF NOT EXISTS idx_offres_source ON offres(source);
        CREATE INDEX IF NOT EXISTS idx_offres_date ON offres(date_limite);
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Base initialisée : {DB_PATH}")


def compute_hash(offre: dict) -> str:
    """Hash unique basé sur titre + acheteur + date_limite pour déduplication."""
    key = f"{offre.get('titre','')}{offre.get('acheteur','')}{offre.get('date_limite','')}".lower().strip()
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def insert_offre(offre: dict) -> Optional[int]:
    """
    Insère une offre si elle n'existe pas déjà.
    Retourne l'id inséré, ou None si doublon.
    """
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
        return None  # doublon
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
    """Retourne les offres avec statut filtre_ok sans score encore."""
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
