"""
api/main.py — API REST AO Veille (multi-utilisateurs)
"""
import csv
import io
import json
import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr

from api.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from scraper.database import (
    deactivate_user,
    get_all_user_config,
    get_logs,
    get_offre_by_id,
    get_offres,
    get_stats,
    get_user_by_email,
    get_user_by_id,
    create_user,
    insert_log,
    list_users,
    reset_user_config,
    set_offre_action,
    set_user_config,
    update_user,
    update_last_login,
)
from scraper.database import (
    get_sources, get_source, upsert_source, update_source, delete_source,
    get_tags_for_user, get_tags_for_offre, add_tag, remove_tag,
    get_saved_searches, save_search, delete_saved_search,
    mark_vue, set_action as db_set_action,
    set_score_perso, search_offres, migrate_v3,
)
from scraper.source_analyzer import analyze_url_sync
from scraper.generic_scraper import run_generic_scraper

migrate_v3()

app = FastAPI(title="AO Veille API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# Health check
# ===========================================================================
@app.get("/")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ===========================================================================
# Auth
# ===========================================================================
class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not user["actif"]:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    update_last_login(user["id"])
    token = create_access_token(user["id"], user["role"], user["nom"])
    insert_log("auth", "login_ok", json.dumps({"email": req.email}), user_id=user["id"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "nom": user["nom"],
        "user_id": user["id"],
    }


@app.post("/api/auth/logout")
def logout(current_user: dict = Depends(get_current_user)):
    insert_log("auth", "logout", "", user_id=current_user["id"])
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "nom": current_user["nom"],
        "role": current_user["role"],
        "last_login": current_user.get("last_login"),
    }


@app.put("/api/auth/password")
def change_password(
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    old_pw = body.get("old_password", "")
    new_pw = body.get("new_password", "")
    if not verify_password(old_pw, current_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect")
    if len(new_pw) < 6:
        raise HTTPException(status_code=400, detail="Mot de passe trop court (6 caractères min)")
    update_user(current_user["id"], password_hash=hash_password(new_pw))
    return {"status": "ok"}


# ===========================================================================
# Sources
# ===========================================================================
@app.get("/api/sources")
def api_get_sources(current_user=Depends(get_current_user)):
    return get_sources()


@app.post("/api/sources/analyze")
def api_analyze_source(body: dict, current_user=Depends(get_current_user)):
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(400, "url requis")
    cookies = body.get("cookies", [])
    result = analyze_url_sync(url, cookies or None)
    if not result["success"]:
        raise HTTPException(422, result["error"])
    return result


@app.post("/api/sources")
def api_create_source(body: dict, current_user=Depends(get_current_user)):
    data = {
        "name": body["name"],
        "display_name": body["display_name"],
        "base_url": body["base_url"],
        "list_url": body["list_url"],
        "auth_type": body.get("auth_type", "none"),
        "cookies_json": json.dumps(body["cookies_json"]) if body.get("cookies_json") else None,
        "config_json": json.dumps(body["config_json"]) if body.get("config_json") else None,
        "active": 1,
        "confidence": body.get("confidence", 0.0),
    }
    upsert_source(data)
    return {"status": "ok"}


@app.put("/api/sources/{source_id}")
def api_update_source(source_id: int, body: dict, current_user=Depends(get_current_user)):
    fields = {}
    for k in ["display_name", "list_url", "auth_type", "active", "confidence"]:
        if k in body:
            fields[k] = body[k]
    if "config_json" in body:
        fields["config_json"] = json.dumps(body["config_json"])
    if "cookies_json" in body:
        fields["cookies_json"] = json.dumps(body["cookies_json"])
    update_source(source_id, fields)
    return {"status": "ok"}


@app.delete("/api/sources/{source_id}")
def api_delete_source(source_id: int, current_user=Depends(get_current_user)):
    src = get_source(source_id)
    if src and src["name"] == "piter.at":
        raise HTTPException(400, "Impossible de supprimer la source piter.at")
    delete_source(source_id)
    return {"status": "ok"}


@app.post("/api/sources/{source_id}/test")
def api_test_source(source_id: int, current_user=Depends(get_current_user)):
    import asyncio
    from scraper.source_analyzer import preview_offers, fetch_with_playwright

    src = get_source(source_id)
    if not src:
        raise HTTPException(404, "Source introuvable")

    config = json.loads(src.get("config_json") or "{}")
    cookies = json.loads(src.get("cookies_json") or "[]")

    loop = asyncio.new_event_loop()
    fetch_result = loop.run_until_complete(
        fetch_with_playwright(src["list_url"], cookies or None)
    )
    loop.close()

    if not fetch_result["success"]:
        raise HTTPException(422, fetch_result["error"])

    previews = preview_offers(fetch_result["html"], config)
    return {"status": "ok", "preview": previews}


@app.post("/api/trigger/scrape/{source_id}")
def api_trigger_scrape_source(source_id: int, current_user=Depends(get_current_user)):
    src = get_source(source_id)
    if not src:
        raise HTTPException(404, "Source introuvable")
    if src["name"] == "piter.at":
        from scraper.piter_scraper import run_scraper
        result = run_scraper()
    else:
        result = run_generic_scraper(source_id)
    return result


# ===========================================================================
# Tags
# ===========================================================================
@app.get("/api/tags")
def api_get_tags(current_user=Depends(get_current_user)):
    return get_tags_for_user(current_user["id"])


@app.post("/api/offres/{offre_id}/tags")
def api_add_tag(offre_id: int, body: dict, current_user=Depends(get_current_user)):
    label = body.get("label", "").strip()
    color = body.get("color", "#4f8ef7")
    if not label:
        raise HTTPException(400, "label requis")
    add_tag(offre_id, current_user["id"], label, color)
    return {"status": "ok"}


@app.delete("/api/offres/{offre_id}/tags/{label}")
def api_remove_tag(offre_id: int, label: str, current_user=Depends(get_current_user)):
    remove_tag(offre_id, current_user["id"], label)
    return {"status": "ok"}


# ===========================================================================
# Vue / Action / Score perso
# ===========================================================================
@app.post("/api/offres/{offre_id}/vue")
def api_mark_vue(offre_id: int, current_user=Depends(get_current_user)):
    mark_vue(offre_id, current_user["id"])
    return {"status": "ok"}


@app.post("/api/offres/{offre_id}/action")
def api_set_action(offre_id: int, body: dict, current_user=Depends(get_current_user)):
    action = body.get("action")
    db_set_action(offre_id, current_user["id"], action)
    return {"status": "ok"}


@app.put("/api/offres/{offre_id}/action")
def api_set_action_legacy(
    offre_id: int,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    action = body.get("action")
    if action not in ("ignore", "repondu", "gagne", "perdu", None):
        raise HTTPException(status_code=422, detail="Action invalide")
    set_offre_action(offre_id, current_user["id"], action, body.get("note"))
    return {"status": "ok"}


@app.post("/api/offres/{offre_id}/score-perso")
def api_set_score_perso(offre_id: int, body: dict, current_user=Depends(get_current_user)):
    score = body.get("score")
    set_score_perso(offre_id, current_user["id"], score)
    return {"status": "ok"}


# ===========================================================================
# Recherche avancée
# ===========================================================================
@app.post("/api/search")
def api_search(body: dict, current_user=Depends(get_current_user)):
    limit = min(body.pop("limit", 50), 200)
    offset = body.pop("offset", 0)
    results = search_offres(body, current_user["id"], limit, offset)
    return results


@app.get("/api/search/saved")
def api_get_saved_searches(current_user=Depends(get_current_user)):
    return get_saved_searches(current_user["id"])


@app.post("/api/search/saved")
def api_save_search(body: dict, current_user=Depends(get_current_user)):
    name = body.get("name", "").strip()
    filters = body.get("filters", {})
    notify = body.get("notify", False)
    if not name:
        raise HTTPException(400, "name requis")
    save_search(current_user["id"], name, filters, notify)
    return {"status": "ok"}


@app.delete("/api/search/saved/{search_id}")
def api_delete_saved_search(search_id: int, current_user=Depends(get_current_user)):
    delete_saved_search(search_id, current_user["id"])
    return {"status": "ok"}


# ===========================================================================
# Admin — Gestion des utilisateurs
# ===========================================================================
@app.get("/api/admin/users")
def admin_list_users(admin: dict = Depends(require_admin)):
    return list_users()


class CreateUserRequest(BaseModel):
    email: str
    nom: str
    role: str = "commercial"
    password: str


@app.post("/api/admin/users", status_code=201)
def admin_create_user(req: CreateUserRequest, admin: dict = Depends(require_admin)):
    if req.role not in ("admin", "commercial"):
        raise HTTPException(status_code=422, detail="Rôle invalide (admin ou commercial)")
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email déjà utilisé")
    user = create_user(req.email, req.nom, req.role, req.password)
    insert_log("admin", "user_created",
               json.dumps({"email": req.email, "role": req.role}),
               user_id=admin["id"])
    return {k: user[k] for k in ("id", "email", "nom", "role", "actif", "created_at")}


@app.put("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, body: dict, admin: dict = Depends(require_admin)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    allowed = {}
    if "nom" in body:
        allowed["nom"] = body["nom"]
    if "email" in body:
        allowed["email"] = body["email"]
    if "role" in body and body["role"] in ("admin", "commercial"):
        allowed["role"] = body["role"]
    if "actif" in body:
        allowed["actif"] = int(bool(body["actif"]))

    update_user(user_id, **allowed)
    insert_log("admin", "user_updated",
               json.dumps({"user_id": user_id, "fields": list(allowed.keys())}),
               user_id=admin["id"])
    return {"status": "ok"}


@app.delete("/api/admin/users/{user_id}")
def admin_deactivate_user(user_id: int, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas désactiver votre propre compte")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    deactivate_user(user_id)
    insert_log("admin", "user_deactivated", json.dumps({"user_id": user_id}), user_id=admin["id"])
    return {"status": "ok"}


@app.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, admin: dict = Depends(require_admin)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    tmp_password = secrets.token_urlsafe(8)
    update_user(user_id, password_hash=hash_password(tmp_password))
    insert_log("admin", "password_reset", json.dumps({"user_id": user_id}), user_id=admin["id"])
    return {"status": "ok", "temporary_password": tmp_password}


# ===========================================================================
# Config utilisateur
# ===========================================================================
@app.get("/api/config")
def get_config(current_user: dict = Depends(get_current_user)):
    return get_all_user_config(current_user["id"])


@app.put("/api/config")
def update_config(body: dict, current_user: dict = Depends(get_current_user)):
    VALID_KEYS = {
        "keywords_include", "keywords_exclude", "budget_min", "budget_max",
        "min_days_remaining", "ai_score_threshold", "company_context",
        "prompt_template", "score_go_threshold", "score_etudier_threshold",
    }
    updated = []
    for key, value in body.items():
        if key in VALID_KEYS:
            set_user_config(current_user["id"], key, value)
            updated.append(key)
    return {"status": "ok", "updated": updated}


@app.put("/api/config/{key}")
def update_config_key(key: str, body: dict, current_user: dict = Depends(get_current_user)):
    VALID_KEYS = {
        "keywords_include", "keywords_exclude", "budget_min", "budget_max",
        "min_days_remaining", "ai_score_threshold", "company_context",
        "prompt_template", "score_go_threshold", "score_etudier_threshold",
    }
    if key not in VALID_KEYS:
        raise HTTPException(status_code=404, detail="Clé de configuration inconnue")
    set_user_config(current_user["id"], key, body.get("value"))
    return {"status": "ok", "key": key, "updated_at": datetime.utcnow().isoformat()}


@app.post("/api/config/reset")
def reset_config(current_user: dict = Depends(get_current_user)):
    reset_user_config(current_user["id"])
    return {"status": "ok", "message": "Configuration réinitialisée aux valeurs par défaut"}


@app.get("/api/admin/users/{user_id}/config")
def admin_get_user_config(user_id: int, admin: dict = Depends(require_admin)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return get_all_user_config(user_id)


@app.put("/api/admin/users/{user_id}/config")
def admin_update_user_config(user_id: int, body: dict, admin: dict = Depends(require_admin)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    updated = []
    for key, value in body.items():
        set_user_config(user_id, key, value)
        updated.append(key)
    return {"status": "ok", "updated": updated}


# ===========================================================================
# Offres
# ===========================================================================
@app.get("/api/offres")
def list_offres(
    source: Optional[str] = None,
    recommandation: Optional[str] = None,
    search: Optional[str] = None,
    score_min: Optional[float] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    user_id_filter: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    is_admin = current_user["role"] == "admin"
    filter_uid = user_id_filter if is_admin else None

    return get_offres(
        user_id=current_user["id"],
        source=source,
        recommandation=recommandation,
        search=search,
        score_min=score_min,
        limit=limit,
        offset=offset,
        is_admin=is_admin,
        filter_user_id=filter_uid,
    )


@app.get("/api/offres/{offre_id}")
def detail_offre(offre_id: int, current_user: dict = Depends(get_current_user)):
    offre = get_offre_by_id(offre_id, current_user["id"])
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    return offre


# ===========================================================================
# Stats
# ===========================================================================
@app.get("/api/stats")
def stats(
    user_id_filter: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    is_admin = current_user["role"] == "admin"
    uid = current_user["id"]

    if is_admin and user_id_filter:
        return get_stats(user_id_filter, is_admin=False)
    return get_stats(uid, is_admin=is_admin)


# ===========================================================================
# Logs
# ===========================================================================
@app.get("/api/logs")
def logs(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    is_admin = current_user["role"] == "admin"
    uid = None if is_admin else current_user["id"]
    return get_logs(limit=limit, user_id=uid)


# ===========================================================================
# Triggers manuels
# ===========================================================================
@app.post("/api/trigger/scrape")
def trigger_scrape(admin: dict = Depends(require_admin)):
    try:
        from scraper.piter_scraper import run_scraper
        result = run_scraper()
        insert_log("piter.at", "scrape_done", json.dumps(result), user_id=admin["id"])
        return {"status": "ok", "message": str(result)}
    except Exception as e:
        insert_log("piter.at", "scrape_error", str(e), user_id=admin["id"])
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trigger/score")
def trigger_score(current_user: dict = Depends(get_current_user)):
    try:
        from scraper.ai_scorer import run_scorer, run_scorer_all_users
        is_admin = current_user["role"] == "admin"

        if is_admin:
            result = run_scorer_all_users()
        else:
            result = run_scorer(current_user["id"])

        return {"status": "ok", "message": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# Export CSV
# ===========================================================================
@app.get("/api/export/csv")
def export_csv(current_user: dict = Depends(get_current_user)):
    is_admin = current_user["role"] == "admin"
    offres = get_offres(
        user_id=current_user["id"],
        limit=5000,
        is_admin=is_admin,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Titre", "Acheteur", "Budget min", "Budget max",
        "Date limite", "URL", "Source",
        "Score IA", "Recommandation", "Résumé", "Action",
    ])
    for o in offres:
        writer.writerow([
            o.get("titre"), o.get("acheteur"),
            o.get("budget_min"), o.get("budget_max"),
            o.get("date_limite"), o.get("url"), o.get("source"),
            o.get("score"), o.get("recommandation"), o.get("resume"),
            o.get("action"),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=offres.csv"},
    )