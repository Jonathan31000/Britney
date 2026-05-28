"""
api/main.py
API REST FastAPI — expose les offres au dashboard React.
"""
import os
import json
import sqlite3
from typing import Optional, List, Any
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./data/offres.db")

app = FastAPI(
    title="AO Veille API",
    description="API de veille des appels d'offres",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers DB
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row) -> dict:
    d = dict(row)
    for field in ["points_forts", "points_faibles"]:
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except Exception:
                d[field] = []
    return d


# ---------------------------------------------------------------------------
# Modèles Pydantic
# ---------------------------------------------------------------------------

class OffreOut(BaseModel):
    id: int
    source: str
    titre: str
    description: Optional[str]
    acheteur: Optional[str]
    budget_min: Optional[float]
    budget_max: Optional[float]
    date_limite: Optional[str]
    date_pub: Optional[str]
    url: Optional[str]
    statut: str
    created_at: str
    score: Optional[float] = None
    resume: Optional[str] = None
    points_forts: Optional[List[str]] = None
    points_faibles: Optional[List[str]] = None
    recommandation: Optional[str] = None


class StatsOut(BaseModel):
    total: int
    nouvelles: int
    filtre_ok: int
    scored: int
    go: int
    no_go: int
    a_etudier: int
    sources: dict


class TriggerOut(BaseModel):
    status: str
    message: str


class ConfigValueIn(BaseModel):
    value: Any


class ConfigBulkIn(BaseModel):
    # clé libre → valeur quelconque
    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Routes — health
# ---------------------------------------------------------------------------

@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ---------------------------------------------------------------------------
# Routes — offres
# ---------------------------------------------------------------------------

@app.get("/api/offres", response_model=List[OffreOut], tags=["offres"])
def list_offres(
    source: Optional[str]         = Query(None),
    statut: Optional[str]         = Query(None),
    recommandation: Optional[str] = Query(None),
    search: Optional[str]         = Query(None),
    score_min: Optional[float]    = Query(None),
    limit: int                    = Query(50, ge=1, le=200),
    offset: int                   = Query(0, ge=0),
):
    conn = get_db()
    try:
        where = ["1=1"]
        params = []

        if source:
            where.append("o.source = ?")
            params.append(source)
        if statut:
            where.append("o.statut = ?")
            params.append(statut)
        if recommandation:
            where.append("s.recommandation = ?")
            params.append(recommandation)
        if search:
            where.append("(o.titre LIKE ? OR o.description LIKE ? OR o.acheteur LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])
        if score_min is not None:
            where.append("s.score >= ?")
            params.append(score_min)

        sql = f"""
            SELECT o.*,
                   s.score, s.resume, s.points_forts, s.points_faibles, s.recommandation
            FROM offres o
            LEFT JOIN scores s ON s.offre_id = o.id
            WHERE {' AND '.join(where)}
            ORDER BY COALESCE(s.score, 0) DESC, o.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/offres/{offre_id}", response_model=OffreOut, tags=["offres"])
def get_offre(offre_id: int):
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT o.*, s.score, s.resume, s.points_forts, s.points_faibles, s.recommandation
            FROM offres o
            LEFT JOIN scores s ON s.offre_id = o.id
            WHERE o.id = ?
        """, (offre_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Offre non trouvée")
        return row_to_dict(row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Routes — stats & logs
# ---------------------------------------------------------------------------

@app.get("/api/stats", response_model=StatsOut, tags=["stats"])
def get_stats():
    conn = get_db()
    try:
        def count(sql, params=()):
            return conn.execute(sql, params).fetchone()[0] or 0

        total     = count("SELECT COUNT(*) FROM offres")
        nouvelles = count("SELECT COUNT(*) FROM offres WHERE statut='nouveau'")
        filtre_ok = count("SELECT COUNT(*) FROM offres WHERE statut IN ('filtre_ok','scored')")
        scored    = count("SELECT COUNT(*) FROM offres WHERE statut='scored'")
        go        = count("SELECT COUNT(*) FROM scores WHERE recommandation='go'")
        no_go     = count("SELECT COUNT(*) FROM scores WHERE recommandation='no_go'")
        a_etudier = count("SELECT COUNT(*) FROM scores WHERE recommandation='a_etudier'")

        sources_rows = conn.execute(
            "SELECT source, COUNT(*) as n FROM offres GROUP BY source"
        ).fetchall()
        sources = {r["source"]: r["n"] for r in sources_rows}

        return StatsOut(
            total=total, nouvelles=nouvelles, filtre_ok=filtre_ok,
            scored=scored, go=go, no_go=no_go, a_etudier=a_etudier,
            sources=sources,
        )
    finally:
        conn.close()


@app.get("/api/logs", tags=["logs"])
def get_logs(limit: int = Query(50, ge=1, le=500)):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Routes — config (V2)
# ---------------------------------------------------------------------------

@app.get("/api/config", tags=["config"])
def get_config_all():
    """Retourne tous les paramètres regroupés par section."""
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
    from scraper.database import get_all_config
    return get_all_config()


@app.put("/api/config/{key}", tags=["config"])
def update_config_one(key: str, body: ConfigValueIn):
    """Met à jour un seul paramètre."""
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
    from scraper.database import set_config
    try:
        set_config(key, body.value)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Clé inconnue : '{key}'")
    return {"status": "ok", "key": key, "updated_at": datetime.now().isoformat()}


@app.put("/api/config", tags=["config"])
def update_config_bulk(body: dict):
    """Met à jour plusieurs paramètres en une seule requête."""
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
    from scraper.database import set_config
    updated = []
    errors = []
    for key, value in body.items():
        try:
            set_config(key, value)
            updated.append(key)
        except KeyError:
            errors.append(key)
    if errors:
        raise HTTPException(status_code=404, detail=f"Clés inconnues : {errors}")
    return {"status": "ok", "updated": updated}


@app.post("/api/config/reset", tags=["config"])
def reset_config_all():
    """Remet tous les paramètres à leurs valeurs par défaut."""
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
    from scraper.database import reset_config, CONFIG_DEFAULTS
    reset_config()
    return {"status": "ok", "message": f"{len(CONFIG_DEFAULTS)} paramètres réinitialisés"}


# ---------------------------------------------------------------------------
# Routes — actions
# ---------------------------------------------------------------------------

@app.post("/api/trigger/scrape", response_model=TriggerOut, tags=["actions"])
def trigger_scrape():
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from scraper.piter_scraper import run_scraper
        result = run_scraper()
        return TriggerOut(status="ok", message=str(result))
    except Exception as e:
        return TriggerOut(status="error", message=str(e))


@app.post("/api/trigger/score", response_model=TriggerOut, tags=["actions"])
def trigger_score():
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from scraper.ai_scorer import run_scorer
        result = run_scorer()
        return TriggerOut(status="ok", message=str(result))
    except Exception as e:
        return TriggerOut(status="error", message=str(e))


# ---------------------------------------------------------------------------
# Routes — export
# ---------------------------------------------------------------------------

@app.get("/api/export/csv", tags=["export"])
def export_csv():
    import csv
    import io
    from fastapi.responses import StreamingResponse

    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT o.titre, o.acheteur, o.budget_min, o.budget_max,
                   o.date_limite, o.url, o.source,
                   s.score, s.recommandation, s.resume
            FROM offres o
            LEFT JOIN scores s ON s.offre_id = o.id
            WHERE o.statut = 'scored'
            ORDER BY s.score DESC
        """).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Titre", "Acheteur", "Budget min", "Budget max",
                         "Date limite", "URL", "Source", "Score IA",
                         "Recommandation", "Résumé"])
        for r in rows:
            writer.writerow(list(r))

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=offres.csv"},
        )
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)