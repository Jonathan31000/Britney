"""
scraper/database.py — SQLite CRUD + schéma multi-utilisateurs
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional

DB_PATH = os.getenv("DB_PATH", "./data/offres.db")

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)

    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS offres (
            id          INTEGER PRIMARY KEY,
            hash        TEXT UNIQUE,
            source      TEXT,
            titre       TEXT,
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
        )""")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY,
            email         TEXT UNIQUE NOT NULL,
            nom           TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL CHECK(role IN ('admin', 'commercial')),
            actif         INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now')),
            updated_at    TEXT DEFAULT (datetime('now')),
            last_login    TEXT
        )""")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_config (
            id         INTEGER PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key        TEXT NOT NULL,
            value      TEXT,
            label      TEXT,
            section    TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, key)
        )""")

        if _table_exists(conn, "scores"):
            if not _column_exists(conn, "scores", "user_id"):
                print("[DB] Migration : ajout colonne user_id dans scores")
                conn.execute("ALTER TABLE scores ADD COLUMN user_id INTEGER REFERENCES users(id)")
        else:
            conn.execute("""
            CREATE TABLE scores (
                id             INTEGER PRIMARY KEY,
                offre_id       INTEGER NOT NULL REFERENCES offres(id) ON DELETE CASCADE,
                user_id        INTEGER REFERENCES users(id) ON DELETE CASCADE,
                score          REAL,
                resume         TEXT,
                points_forts   TEXT,
                points_faibles TEXT,
                recommandation TEXT,
                created_at     TEXT DEFAULT (datetime('now')),
                UNIQUE(offre_id, user_id)
            )""")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id         INTEGER PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )""")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS offre_actions (
            id         INTEGER PRIMARY KEY,
            offre_id   INTEGER NOT NULL REFERENCES offres(id) ON DELETE CASCADE,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            action     TEXT CHECK(action IN ('ignore', 'repondu', 'gagne', 'perdu')),
            note       TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(offre_id, user_id)
        )""")

        if _table_exists(conn, "logs"):
            if not _column_exists(conn, "logs", "user_id"):
                print("[DB] Migration : ajout colonne user_id dans logs")
                conn.execute("ALTER TABLE logs ADD COLUMN user_id INTEGER REFERENCES users(id)")
        else:
            conn.execute("""
            CREATE TABLE logs (
                id         INTEGER PRIMARY KEY,
                source     TEXT,
                event      TEXT,
                detail     TEXT,
                user_id    INTEGER REFERENCES users(id),
                created_at TEXT DEFAULT (datetime('now'))
            )""")

        if not _table_exists(conn, "sources"):
            conn.execute("""
            CREATE TABLE sources (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                base_url     TEXT NOT NULL,
                list_url     TEXT NOT NULL,
                auth_type    TEXT DEFAULT 'none',
                cookies_json TEXT,
                config_json  TEXT,
                active       INTEGER DEFAULT 1,
                confidence   REAL DEFAULT 0.0,
                last_scraped TEXT,
                created_at   TEXT DEFAULT (datetime('now'))
            )""")
            conn.execute("""
                INSERT OR IGNORE INTO sources
                    (name, display_name, base_url, list_url, auth_type, active)
                VALUES
                    ('piter.at', 'Piter.at', 'https://piter.at',
                     'https://piter.at/prestataire/consultation', 'cookies', 1)
            """)

        if not _table_exists(conn, "tags"):
            conn.execute("""
            CREATE TABLE tags (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                offre_id   INTEGER NOT NULL REFERENCES offres(id) ON DELETE CASCADE,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                label      TEXT NOT NULL,
                color      TEXT DEFAULT '#4f8ef7',
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(offre_id, user_id, label)
            )""")

        if not _table_exists(conn, "saved_searches"):
            conn.execute("""
            CREATE TABLE saved_searches (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name       TEXT NOT NULL,
                filters    TEXT NOT NULL,
                notify     INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )""")

        if not _column_exists(conn, "offres", "vue_par"):
            conn.execute("ALTER TABLE offres ADD COLUMN vue_par TEXT DEFAULT '[]'")
        if not _column_exists(conn, "offres", "score_perso"):
            conn.execute("ALTER TABLE offres ADD COLUMN score_perso TEXT DEFAULT '{}'")
        if not _column_exists(conn, "offres", "actions"):
            conn.execute("ALTER TABLE offres ADD COLUMN actions TEXT DEFAULT '{}'")

        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_offres_statut    ON offres(statut)",
            "CREATE INDEX IF NOT EXISTS idx_offres_source    ON offres(source)",
            "CREATE INDEX IF NOT EXISTS idx_scores_user      ON scores(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_scores_offre     ON scores(offre_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_config_user ON user_config(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user    ON sessions(user_id)",
        ]:
            try:
                conn.execute(sql)
            except Exception:
                pass

        _create_default_admin(conn)
        _init_config_defaults_all_users(conn)

    print(f"[DB] Base initialisée : {DB_PATH}")


def migrate_v3():
    with get_conn() as conn:
        if not _table_exists(conn, "sources"):
            conn.execute("""
            CREATE TABLE sources (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                base_url     TEXT NOT NULL,
                list_url     TEXT NOT NULL,
                auth_type    TEXT DEFAULT 'none',
                cookies_json TEXT,
                config_json  TEXT,
                active       INTEGER DEFAULT 1,
                confidence   REAL DEFAULT 0.0,
                last_scraped TEXT,
                created_at   TEXT DEFAULT (datetime('now'))
            )""")
            conn.execute("""
                INSERT OR IGNORE INTO sources
                    (name, display_name, base_url, list_url, auth_type, active)
                VALUES
                    ('piter.at', 'Piter.at', 'https://piter.at',
                     'https://piter.at/prestataire/consultation', 'cookies', 1)
            """)

        if not _table_exists(conn, "tags"):
            conn.execute("""
            CREATE TABLE tags (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                offre_id   INTEGER NOT NULL REFERENCES offres(id) ON DELETE CASCADE,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                label      TEXT NOT NULL,
                color      TEXT DEFAULT '#4f8ef7',
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(offre_id, user_id, label)
            )""")

        if not _table_exists(conn, "saved_searches"):
            conn.execute("""
            CREATE TABLE saved_searches (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name       TEXT NOT NULL,
                filters    TEXT NOT NULL,
                notify     INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )""")

        if not _column_exists(conn, "offres", "vue_par"):
            conn.execute("ALTER TABLE offres ADD COLUMN vue_par TEXT DEFAULT '[]'")
        if not _column_exists(conn, "offres", "score_perso"):
            conn.execute("ALTER TABLE offres ADD COLUMN score_perso TEXT DEFAULT '{}'")
        if not _column_exists(conn, "offres", "actions"):
            conn.execute("ALTER TABLE offres ADD COLUMN actions TEXT DEFAULT '{}'")

    print("[DB] Migration V3 OK")


CONFIG_DEFAULTS = [
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
    ("company_context",        json.dumps("ESN spécialisée en développement IT."),
     "Contexte entreprise",    "scoring"),
    ("prompt_template",        json.dumps(
        "Contexte de notre entreprise :\n{company_context}\n\n---\n"
        "Appel d'offres à analyser :\nTitre : {titre}\nAcheteur : {acheteur}\n"
        "Budget estimé : {budget} €\nDate limite : {date_limite}\n\n"
        "Description :\n{description}\n\n---\n"
        "Réponds UNIQUEMENT avec un objet JSON valide :\n"
        '{{\n  "score": <0-10>,\n  "resume": "<2 phrases>",\n'
        '  "points_forts": ["..."],\n  "points_faibles": ["..."],\n'
        '  "recommandation": "<go|no_go|a_etudier>",\n  "justification": "<1 phrase>"\n}}'
    ), "Template du prompt IA", "scoring"),
    ("score_go_threshold",     json.dumps(8.0),
     "Seuil score GO",         "scoring"),
    ("score_etudier_threshold", json.dumps(5.0),
     "Seuil score À étudier",  "scoring"),
]


def _init_user_config_defaults(conn, user_id: int):
    conn.executemany("""
        INSERT OR IGNORE INTO user_config (user_id, key, value, label, section, updated_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, [(user_id, key, value, label, section)
          for key, value, label, section in CONFIG_DEFAULTS])


def _init_config_defaults_all_users(conn):
    users = conn.execute("SELECT id FROM users").fetchall()
    for u in users:
        _init_user_config_defaults(conn, u["id"])


def _create_default_admin(conn):
    existing = conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()
    if existing:
        return
    from api.auth import hash_password
    pw_hash = hash_password("admin")
    conn.execute("""
        INSERT INTO users (email, nom, password_hash, role, created_at, updated_at)
        VALUES ('admin@localhost', 'Admin', ?, 'admin', datetime('now'), datetime('now'))
    """, (pw_hash,))
    print("[AUTH] Compte admin créé : admin@localhost / admin")
    print("[AUTH] ⚠  Changez le mot de passe au premier login !")


# ---------------------------------------------------------------------------
# CRUD — Users
# ---------------------------------------------------------------------------
def get_user_by_email(email: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def list_users() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, email, nom, role, actif, created_at, last_login FROM users ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def create_user(email: str, nom: str, role: str, password: str) -> dict:
    from api.auth import hash_password
    pw_hash = hash_password(password)
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO users (email, nom, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (email, nom, pw_hash, role))
        user_id = cur.lastrowid
        _init_user_config_defaults(conn, user_id)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row)


def update_user(user_id: int, **fields) -> bool:
    allowed = {"email", "nom", "role", "actif", "password_hash", "last_login"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    return True


def deactivate_user(user_id: int):
    update_user(user_id, actif=0)


def update_last_login(user_id: int):
    update_user(user_id, last_login=datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# CRUD — user_config
# ---------------------------------------------------------------------------
def get_user_config(user_id: int, key: str) -> Any:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM user_config WHERE user_id = ? AND key = ?",
            (user_id, key)
        ).fetchone()
        if row is None:
            defaults = {k: json.loads(v) for k, v, _, _ in CONFIG_DEFAULTS}
            return defaults.get(key)
        return json.loads(row["value"])


def set_user_config(user_id: int, key: str, value: Any):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_config (user_id, key, value, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (user_id, key, json.dumps(value)))


def get_all_user_config(user_id: int) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT key, value, label, section, updated_at FROM user_config WHERE user_id = ?",
            (user_id,)
        ).fetchall()

    result = {}
    for row in rows:
        section = row["section"] or "autres"
        if section not in result:
            result[section] = {}
        result[section][row["key"]] = {
            "value": json.loads(row["value"]),
            "label": row["label"],
            "updated_at": row["updated_at"],
        }
    return result


def reset_user_config(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM user_config WHERE user_id = ?", (user_id,))
        _init_user_config_defaults(conn, user_id)


# ---------------------------------------------------------------------------
# CRUD — Offres
# ---------------------------------------------------------------------------
def insert_offre(offre: dict) -> Optional[int]:
    with get_conn() as conn:
        try:
            cur = conn.execute("""
                INSERT INTO offres
                    (hash, source, titre, description, acheteur,
                     budget_min, budget_max, date_limite, date_pub, url,
                     statut, raw_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'nouveau', ?, datetime('now'), datetime('now'))
            """, (
                offre.get("hash"), offre.get("source"), offre.get("titre"),
                offre.get("description"), offre.get("acheteur"),
                offre.get("budget_min"), offre.get("budget_max"),
                offre.get("date_limite"), offre.get("date_pub"),
                offre.get("url"), json.dumps(offre.get("raw_json", {})),
            ))
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def update_statut(offre_id: int, statut: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE offres SET statut=?, updated_at=datetime('now') WHERE id=?",
            (statut, offre_id)
        )


def get_offres(
    user_id: int,
    source: str = None,
    recommandation: str = None,
    search: str = None,
    score_min: float = None,
    limit: int = 50,
    offset: int = 0,
    is_admin: bool = False,
    filter_user_id: int = None,
) -> list:
    score_user = filter_user_id if (is_admin and filter_user_id) else user_id

    if not is_admin or filter_user_id:
        uid = filter_user_id if filter_user_id else user_id
        keywords = get_user_config(uid, "keywords_include") or []
    else:
        keywords = []

    with get_conn() as conn:
        params = []
        where_clauses = []

        if keywords and (not is_admin or filter_user_id):
            kw_conditions = " OR ".join(
                ["(LOWER(o.titre) LIKE ? OR LOWER(o.description) LIKE ?)"] * len(keywords)
            )
            where_clauses.append(f"({kw_conditions})")
            for kw in keywords:
                params.extend([f"%{kw.lower()}%", f"%{kw.lower()}%"])

        if source:
            where_clauses.append("o.source = ?")
            params.append(source)

        if search:
            where_clauses.append(
                "(LOWER(o.titre) LIKE ? OR LOWER(o.acheteur) LIKE ? OR LOWER(o.description) LIKE ?)"
            )
            params.extend([f"%{search.lower()}%"] * 3)

        if recommandation:
            where_clauses.append("s.recommandation = ?")
            params.append(recommandation)

        if score_min is not None:
            where_clauses.append("s.score >= ?")
            params.append(score_min)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        query = f"""
            SELECT
                o.*,
                s.score, s.resume, s.points_forts, s.points_faibles,
                s.recommandation, s.created_at AS scored_at,
                a.action, a.note
            FROM offres o
            LEFT JOIN scores s ON s.offre_id = o.id AND s.user_id = {score_user}
            LEFT JOIN offre_actions a ON a.offre_id = o.id AND a.user_id = {score_user}
            {where_sql}
            ORDER BY s.score DESC NULLS LAST, o.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()

    result = []
    for row in rows:
        d = dict(row)
        for field in ("points_forts", "points_faibles"):
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        result.append(d)
    return result


def get_offre_by_id(offre_id: int, user_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                o.*,
                s.score, s.resume, s.points_forts, s.points_faibles,
                s.recommandation, s.created_at AS scored_at,
                a.action, a.note
            FROM offres o
            LEFT JOIN scores s ON s.offre_id = o.id AND s.user_id = ?
            LEFT JOIN offre_actions a ON a.offre_id = o.id AND a.user_id = ?
            WHERE o.id = ?
        """, (user_id, user_id, offre_id)).fetchone()
        if not row:
            return None
        d = dict(row)
        for field in ("points_forts", "points_faibles"):
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        return d


def get_offres_to_score(user_id: int) -> list:
    keywords = get_user_config(user_id, "keywords_include") or []
    with get_conn() as conn:
        if keywords:
            kw_conditions = " OR ".join(
                ["(LOWER(titre) LIKE ? OR LOWER(description) LIKE ?)"] * len(keywords)
            )
            params = []
            for kw in keywords:
                params.extend([f"%{kw.lower()}%", f"%{kw.lower()}%"])
            params.append(user_id)
            rows = conn.execute(f"""
                SELECT o.* FROM offres o
                WHERE ({kw_conditions})
                AND o.id NOT IN (
                    SELECT offre_id FROM scores WHERE user_id = ?
                )
                ORDER BY o.created_at DESC
            """, params).fetchall()
        else:
            rows = conn.execute("""
                SELECT o.* FROM offres o
                WHERE o.id NOT IN (
                    SELECT offre_id FROM scores WHERE user_id = ?
                )
                ORDER BY o.created_at DESC
            """, (user_id,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# CRUD — Scores
# ---------------------------------------------------------------------------
def insert_score(offre_id: int, user_id: int, score: float, resume: str,
                 points_forts: list, points_faibles: list,
                 recommandation: str, **kwargs):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO scores
                (offre_id, user_id, score, resume, points_forts, points_faibles,
                 recommandation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(offre_id, user_id) DO UPDATE SET
                score = excluded.score,
                resume = excluded.resume,
                points_forts = excluded.points_forts,
                points_faibles = excluded.points_faibles,
                recommandation = excluded.recommandation,
                created_at = excluded.created_at
        """, (
            offre_id, user_id, score, resume,
            json.dumps(points_forts), json.dumps(points_faibles),
            recommandation,
        ))


# ---------------------------------------------------------------------------
# CRUD — Offre actions
# ---------------------------------------------------------------------------
def set_offre_action(offre_id: int, user_id: int, action: str, note: str = None):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO offre_actions (offre_id, user_id, action, note, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(offre_id, user_id) DO UPDATE SET
                action = excluded.action,
                note = excluded.note,
                updated_at = excluded.updated_at
        """, (offre_id, user_id, action, note))


# ---------------------------------------------------------------------------
# CRUD — Logs
# ---------------------------------------------------------------------------
def insert_log(source: str, event: str, detail: str = "", user_id: int = None):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO logs (source, event, detail, user_id, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (source, event, detail, user_id))


# Alias pour compatibilité piter_scraper
log_event = insert_log


def get_logs(limit: int = 50, user_id: int = None) -> list:
    with get_conn() as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM logs WHERE user_id = ? OR user_id IS NULL "
                "ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
def get_stats(user_id: int, is_admin: bool = False) -> dict:
    with get_conn() as conn:
        if is_admin:
            total = conn.execute("SELECT COUNT(*) FROM offres").fetchone()[0]
            sources = dict(conn.execute(
                "SELECT source, COUNT(*) FROM offres GROUP BY source"
            ).fetchall())
            go = conn.execute(
                "SELECT COUNT(DISTINCT offre_id) FROM scores WHERE recommandation='go'"
            ).fetchone()[0]
            no_go = conn.execute(
                "SELECT COUNT(DISTINCT offre_id) FROM scores WHERE recommandation='no_go'"
            ).fetchone()[0]
            a_etudier = conn.execute(
                "SELECT COUNT(DISTINCT offre_id) FROM scores WHERE recommandation='a_etudier'"
            ).fetchone()[0]
            scored = conn.execute(
                "SELECT COUNT(DISTINCT offre_id) FROM scores"
            ).fetchone()[0]
        else:
            keywords = get_user_config(user_id, "keywords_include") or []
            if keywords:
                kw_conditions = " OR ".join(
                    ["(LOWER(titre) LIKE ? OR LOWER(description) LIKE ?)"] * len(keywords)
                )
                params = []
                for kw in keywords:
                    params.extend([f"%{kw.lower()}%", f"%{kw.lower()}%"])
                total = conn.execute(
                    f"SELECT COUNT(*) FROM offres WHERE {kw_conditions}", params
                ).fetchone()[0]
            else:
                total = conn.execute("SELECT COUNT(*) FROM offres").fetchone()[0]

            sources = dict(conn.execute(
                "SELECT source, COUNT(*) FROM offres GROUP BY source"
            ).fetchall())
            go = conn.execute(
                "SELECT COUNT(*) FROM scores WHERE user_id=? AND recommandation='go'",
                (user_id,)
            ).fetchone()[0]
            no_go = conn.execute(
                "SELECT COUNT(*) FROM scores WHERE user_id=? AND recommandation='no_go'",
                (user_id,)
            ).fetchone()[0]
            a_etudier = conn.execute(
                "SELECT COUNT(*) FROM scores WHERE user_id=? AND recommandation='a_etudier'",
                (user_id,)
            ).fetchone()[0]
            scored = conn.execute(
                "SELECT COUNT(*) FROM scores WHERE user_id=?", (user_id,)
            ).fetchone()[0]

    return {
        "total": total,
        "scored": scored,
        "go": go,
        "no_go": no_go,
        "a_etudier": a_etudier,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Migration V1 → multi-user
# ---------------------------------------------------------------------------
def migrate_v1_to_multiuser():
    with get_conn() as conn:
        legacy = conn.execute(
            "SELECT id FROM users WHERE email='legacy@localhost'"
        ).fetchone()
        if legacy:
            print("[MIGRATION] Déjà effectuée.")
            return

        from api.auth import hash_password
        pw_hash = hash_password("changeme")
        cur = conn.execute("""
            INSERT INTO users (email, nom, password_hash, role, created_at, updated_at)
            VALUES ('legacy@localhost', 'Commercial (migré V1)', ?, 'commercial',
                    datetime('now'), datetime('now'))
        """, (pw_hash,))
        user_id = cur.lastrowid

        try:
            conn.execute(
                "UPDATE scores SET user_id = ? WHERE user_id IS NULL", (user_id,)
            )
        except Exception:
            pass

        try:
            old_config = conn.execute("SELECT key, value, label, section FROM config").fetchall()
            for row in old_config:
                conn.execute("""
                    INSERT OR IGNORE INTO user_config (user_id, key, value, label, section, updated_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (user_id, row["key"], row["value"], row["label"], row["section"]))
        except Exception:
            _init_user_config_defaults(conn, user_id)

        ctx = os.getenv("COMPANY_CONTEXT", "")
        if ctx:
            conn.execute("""
                INSERT OR REPLACE INTO user_config (user_id, key, value, label, section, updated_at)
                VALUES (?, 'company_context', ?, 'Contexte entreprise', 'scoring', datetime('now'))
            """, (user_id, json.dumps(ctx)))

        print(f"[MIGRATION] Données V1 migrées vers user_id={user_id} (legacy@localhost / changeme)")


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
def get_sources(active_only=False) -> list:
    with get_conn() as conn:
        q = "SELECT * FROM sources"
        if active_only:
            q += " WHERE active = 1"
        q += " ORDER BY created_at ASC"
        rows = conn.execute(q).fetchall()
        return [dict(r) for r in rows]


def get_source(source_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sources WHERE id=?", (source_id,)
        ).fetchone()
        return dict(row) if row else None


def upsert_source(data: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO sources (name, display_name, base_url, list_url, auth_type,
                                 cookies_json, config_json, active, confidence)
            VALUES (:name, :display_name, :base_url, :list_url, :auth_type,
                    :cookies_json, :config_json, :active, :confidence)
            ON CONFLICT(name) DO UPDATE SET
                display_name  = excluded.display_name,
                base_url      = excluded.base_url,
                list_url      = excluded.list_url,
                auth_type     = excluded.auth_type,
                cookies_json  = COALESCE(excluded.cookies_json, cookies_json),
                config_json   = excluded.config_json,
                active        = excluded.active,
                confidence    = excluded.confidence
        """, data)


def update_source(source_id: int, fields: dict):
    allowed = {"display_name", "list_url", "auth_type", "cookies_json",
               "config_json", "active", "confidence", "last_scraped"}
    sets = ", ".join(f"{k}=?" for k in fields if k in allowed)
    vals = [v for k, v in fields.items() if k in allowed]
    if not sets:
        return
    with get_conn() as conn:
        conn.execute(f"UPDATE sources SET {sets} WHERE id=?", vals + [source_id])


def delete_source(source_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM sources WHERE id=?", (source_id,))


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------
def get_tags_for_user(user_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT label, color, COUNT(*) as count
            FROM tags WHERE user_id=?
            GROUP BY label, color
            ORDER BY count DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def get_tags_for_offre(offre_id: int, user_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT label, color FROM tags WHERE offre_id=? AND user_id=?",
            (offre_id, user_id)
        ).fetchall()
        return [dict(r) for r in rows]


def add_tag(offre_id: int, user_id: int, label: str, color: str = "#4f8ef7"):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO tags (offre_id, user_id, label, color)
            VALUES (?, ?, ?, ?)
        """, (offre_id, user_id, label.strip().lower(), color))


def remove_tag(offre_id: int, user_id: int, label: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM tags WHERE offre_id=? AND user_id=? AND label=?",
            (offre_id, user_id, label)
        )


# ---------------------------------------------------------------------------
# Saved searches
# ---------------------------------------------------------------------------
def get_saved_searches(user_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, filters, notify, created_at FROM saved_searches "
            "WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return [
            {"id": r["id"], "name": r["name"], "filters": json.loads(r["filters"]),
             "notify": bool(r["notify"]), "created_at": r["created_at"]}
            for r in rows
        ]


def save_search(user_id: int, name: str, filters: dict, notify: bool = False):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO saved_searches (user_id, name, filters, notify)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, json.dumps(filters), int(notify)))


def delete_saved_search(search_id: int, user_id: int):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM saved_searches WHERE id=? AND user_id=?",
            (search_id, user_id)
        )


# ---------------------------------------------------------------------------
# Vue / Action / Score perso
# ---------------------------------------------------------------------------
def mark_vue(offre_id: int, user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT vue_par FROM offres WHERE id=?", (offre_id,)
        ).fetchone()
        if not row:
            return
        vues = json.loads(row["vue_par"] or "[]")
        if user_id not in vues:
            vues.append(user_id)
            conn.execute(
                "UPDATE offres SET vue_par=? WHERE id=?",
                (json.dumps(vues), offre_id)
            )


def set_action(offre_id: int, user_id: int, action: Optional[str]):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT actions FROM offres WHERE id=?", (offre_id,)
        ).fetchone()
        actions = json.loads(row["actions"] or "{}") if row else {}
        if action is None:
            actions.pop(str(user_id), None)
        else:
            actions[str(user_id)] = action
        conn.execute(
            "UPDATE offres SET actions=? WHERE id=?",
            (json.dumps(actions), offre_id)
        )


def set_score_perso(offre_id: int, user_id: int, score: Optional[float]):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT score_perso FROM offres WHERE id=?", (offre_id,)
        ).fetchone()
        scores = json.loads(row["score_perso"] or "{}") if row else {}
        if score is None:
            scores.pop(str(user_id), None)
        else:
            scores[str(user_id)] = score
        conn.execute(
            "UPDATE offres SET score_perso=? WHERE id=?",
            (json.dumps(scores), offre_id)
        )


# ---------------------------------------------------------------------------
# Recherche avancée
# ---------------------------------------------------------------------------
def search_offres(filters: dict, user_id: int, limit: int = 50, offset: int = 0) -> list:
    tags = filters.get("tags", [])

    with get_conn() as conn:
        wheres = ["1=1"]
        params = []

        q = filters.get("q", "").strip()
        if q:
            parts = []
            if filters.get("in_titre", True):
                parts.append("o.titre LIKE ?")
                params.append(f"%{q}%")
            if filters.get("in_description", True):
                parts.append("o.description LIKE ?")
                params.append(f"%{q}%")
            if filters.get("in_acheteur", False):
                parts.append("o.acheteur LIKE ?")
                params.append(f"%{q}%")
            if parts:
                wheres.append(f"({' OR '.join(parts)})")

        if filters.get("score_min") is not None:
            wheres.append("s.score >= ?")
            params.append(filters["score_min"])
        if filters.get("score_max") is not None:
            wheres.append("s.score <= ?")
            params.append(filters["score_max"])

        recos = filters.get("recommandation") or []
        if recos:
            wheres.append(f"s.recommandation IN ({','.join('?'*len(recos))})")
            params.extend(recos)

        srcs = filters.get("source") or []
        if srcs:
            wheres.append(f"o.source IN ({','.join('?'*len(srcs))})")
            params.extend(srcs)

        statuts = filters.get("statut") or []
        if statuts:
            wheres.append(f"o.statut IN ({','.join('?'*len(statuts))})")
            params.extend(statuts)

        if filters.get("date_limite_from"):
            wheres.append("o.date_limite >= ?")
            params.append(filters["date_limite_from"])
        if filters.get("date_limite_to"):
            wheres.append("o.date_limite <= ?")
            params.append(filters["date_limite_to"])

        if filters.get("budget_min") is not None:
            wheres.append("(o.budget_max >= ? OR o.budget_min >= ?)")
            params.extend([filters["budget_min"], filters["budget_min"]])
        if filters.get("budget_max") is not None:
            wheres.append("(o.budget_min <= ? OR o.budget_min IS NULL)")
            params.append(filters["budget_max"])

        if filters.get("non_vues_seulement"):
            wheres.append("(o.vue_par NOT LIKE ? OR o.vue_par IS NULL OR o.vue_par = '[]')")
            params.append(f"%{user_id}%")
        elif filters.get("vues_seulement"):
            wheres.append("o.vue_par LIKE ?")
            params.append(f"%{user_id}%")

        for tag in tags:
            wheres.append(
                "EXISTS (SELECT 1 FROM tags t WHERE t.offre_id=o.id AND t.user_id=? AND t.label=?)"
            )
            params.extend([user_id, tag])

        where_clause = " AND ".join(wheres)

        sql = f"""
            SELECT o.*,
                   s.score, s.resume, s.points_forts, s.points_faibles,
                   s.recommandation, s.created_at as score_date
            FROM offres o
            LEFT JOIN scores s ON s.offre_id = o.id AND s.user_id = {user_id}
            WHERE {where_clause}
            ORDER BY s.score DESC, o.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            for field in ("points_forts", "points_faibles"):
                if d.get(field):
                    try:
                        d[field] = json.loads(d[field])
                    except Exception:
                        pass
            d["tags"] = get_tags_for_offre(d["id"], user_id)
            d["action"] = json.loads(d.get("actions") or "{}").get(str(user_id))
            d["score_perso_val"] = json.loads(d.get("score_perso") or "{}").get(str(user_id))
            d["vue"] = user_id in json.loads(d.get("vue_par") or "[]")
            for k in ["vue_par", "actions", "score_perso"]:
                d.pop(k, None)
            results.append(d)

        return results