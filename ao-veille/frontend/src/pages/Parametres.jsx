// src/pages/Parametres.jsx
import React, { useState, useEffect, useCallback } from 'react'

const API = '/api'

const css = `
  .params-page { padding: 32px 40px; max-width: 820px; }
  .params-title { font-size: 22px; color: var(--text); margin-bottom: 8px; }
  .params-subtitle { font-size: 13px; color: var(--text3); margin-bottom: 32px; }

  .params-section { background: var(--bg2); border: 1px solid var(--border);
    border-radius: 10px; padding: 28px; margin-bottom: 24px; }
  .params-section-title { font-size: 15px; font-weight: 600; color: var(--text);
    margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
  .params-section-icon { font-size: 18px; }

  .params-field { margin-bottom: 20px; }
  .params-label { font-size: 12px; color: var(--text3); text-transform: uppercase;
    letter-spacing: .05em; margin-bottom: 8px; }
  .params-input { background: var(--bg3); border: 1px solid var(--border);
    border-radius: 6px; color: var(--text); font-size: 13px; padding: 8px 12px;
    width: 100%; box-sizing: border-box; font-family: inherit; }
  .params-input:focus { outline: none; border-color: var(--accent); }
  .params-textarea { resize: vertical; min-height: 100px; }
  .params-textarea-lg { min-height: 220px; font-family: var(--font-mono); font-size: 12px; }

  .params-row { display: flex; gap: 16px; }
  .params-row .params-field { flex: 1; }

  .tags-container { display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
    background: var(--bg3); border: 1px solid var(--border); border-radius: 6px;
    padding: 8px 10px; min-height: 40px; }
  .tag { display: flex; align-items: center; gap: 4px; background: rgba(79,142,247,.15);
    color: var(--accent); border-radius: 4px; padding: 3px 8px; font-size: 12px; }
  .tag-remove { cursor: pointer; color: var(--text3); font-size: 14px; line-height: 1;
    padding: 0 2px; }
  .tag-remove:hover { color: var(--no-go); }
  .tag-input { background: transparent; border: none; outline: none; color: var(--text);
    font-size: 12px; min-width: 80px; flex: 1; font-family: inherit; }

  .seuils-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .seuil-group { display: flex; align-items: center; gap: 8px; }
  .seuil-label { font-size: 13px; color: var(--text2); white-space: nowrap; }
  .seuil-input { background: var(--bg3); border: 1px solid var(--border);
    border-radius: 6px; color: var(--text); font-size: 13px; padding: 6px 10px;
    width: 70px; text-align: center; font-family: inherit; }
  .seuil-input:focus { outline: none; border-color: var(--accent); }

  .advanced-toggle { background: none; border: none; color: var(--text3);
    font-size: 12px; cursor: pointer; padding: 0; display: flex; align-items: center;
    gap: 4px; margin-bottom: 12px; }
  .advanced-toggle:hover { color: var(--text); }

  .params-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }
  .btn { border: none; border-radius: 6px; padding: 9px 20px; font-size: 13px;
    cursor: pointer; font-family: inherit; font-weight: 500; transition: opacity .15s; }
  .btn:hover { opacity: .85; }
  .btn:disabled { opacity: .4; cursor: not-allowed; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-ghost { background: var(--bg3); color: var(--text2); border: 1px solid var(--border); }
  .btn-danger { background: transparent; color: var(--no-go); border: 1px solid var(--no-go); }

  .toast { position: fixed; bottom: 28px; right: 28px; background: var(--bg2);
    border: 1px solid var(--border); border-radius: 8px; padding: 12px 20px;
    font-size: 13px; color: var(--text); box-shadow: 0 4px 20px rgba(0,0,0,.4);
    z-index: 1000; display: flex; align-items: center; gap: 8px; }
  .toast-ok  { border-left: 3px solid var(--go); }
  .toast-err { border-left: 3px solid var(--no-go); }

  .loading { color: var(--text3); font-size: 13px; padding: 40px; text-align: center; }
  .hint { font-size: 11px; color: var(--text3); margin-top: 6px; }
`

function TagInput({ values, onChange }) {
  const [input, setInput] = useState('')

  const add = () => {
    const v = input.trim().toLowerCase()
    if (v && !values.includes(v)) onChange([...values, v])
    setInput('')
  }

  const remove = (kw) => onChange(values.filter(k => k !== kw))

  return (
    <div className="tags-container">
      {values.map(kw => (
        <span key={kw} className="tag">
          {kw}
          <span className="tag-remove" onClick={() => remove(kw)}>×</span>
        </span>
      ))}
      <input
        className="tag-input"
        value={input}
        placeholder="+ ajouter"
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add() } }}
        onBlur={add}
      />
    </div>
  )
}

function Toast({ msg, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3000)
    return () => clearTimeout(t)
  }, [onClose])
  if (!msg) return null
  return (
    <div className={`toast ${msg.ok ? 'toast-ok' : 'toast-err'}`}>
      <span>{msg.ok ? '✓' : '✗'}</span> {msg.text}
    </div>
  )
}

export default function Parametres() {
  const [loading, setLoading]       = useState(true)
  const [saving, setSaving]         = useState(false)
  const [toast, setToast]           = useState(null)
  const [showPrompt, setShowPrompt] = useState(false)

  const [filtrage, setFiltrage] = useState({
    keywords_include:   [],
    keywords_exclude:   [],
    budget_min:         '',
    budget_max:         '',
    min_days_remaining: '0',
    ai_score_threshold: '4.0',
  })
  const [scoring, setScoring] = useState({
    company_context:         '',
    prompt_template:         '',
    score_go_threshold:      '8.0',
    score_etudier_threshold: '5.0',
  })

  const fetchConfig = useCallback(async () => {
    setLoading(true)
    try {
      const res  = await fetch(`${API}/config`)
      const data = await res.json()
      const f = data.filtrage || {}
      const s = data.scoring  || {}
      setFiltrage({
        keywords_include:   f.keywords_include?.value   ?? [],
        keywords_exclude:   f.keywords_exclude?.value   ?? [],
        budget_min:         f.budget_min?.value   != null ? String(f.budget_min.value)   : '',
        budget_max:         f.budget_max?.value   != null ? String(f.budget_max.value)   : '',
        min_days_remaining: String(f.min_days_remaining?.value ?? 0),
        ai_score_threshold: String(f.ai_score_threshold?.value ?? 4.0),
      })
      setScoring({
        company_context:         s.company_context?.value         ?? '',
        prompt_template:         s.prompt_template?.value         ?? '',
        score_go_threshold:      String(s.score_go_threshold?.value      ?? 8.0),
        score_etudier_threshold: String(s.score_etudier_threshold?.value ?? 5.0),
      })
    } catch {
      setToast({ ok: false, text: 'Impossible de charger la configuration' })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchConfig() }, [fetchConfig])

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = {
        keywords_include:        filtrage.keywords_include,
        keywords_exclude:        filtrage.keywords_exclude,
        budget_min:              filtrage.budget_min  !== '' ? parseFloat(filtrage.budget_min)  : null,
        budget_max:              filtrage.budget_max  !== '' ? parseFloat(filtrage.budget_max)  : null,
        min_days_remaining:      parseInt(filtrage.min_days_remaining, 10) || 0,
        ai_score_threshold:      parseFloat(filtrage.ai_score_threshold) || 4.0,
        company_context:         scoring.company_context,
        prompt_template:         scoring.prompt_template,
        score_go_threshold:      parseFloat(scoring.score_go_threshold) || 8.0,
        score_etudier_threshold: parseFloat(scoring.score_etudier_threshold) || 5.0,
      }
      const res = await fetch(`${API}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(await res.text())
      setToast({ ok: true, text: 'Paramètres sauvegardés' })
    } catch (e) {
      setToast({ ok: false, text: `Erreur : ${e.message}` })
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    if (!window.confirm('Remettre tous les paramètres à leurs valeurs par défaut ?')) return
    try {
      const res = await fetch(`${API}/config/reset`, { method: 'POST' })
      if (!res.ok) throw new Error()
      setToast({ ok: true, text: 'Paramètres réinitialisés' })
      await fetchConfig()
    } catch {
      setToast({ ok: false, text: 'Erreur lors de la réinitialisation' })
    }
  }

  if (loading) return <div className="loading">Chargement…</div>

  return (
    <>
      <style>{css}</style>
      <div className="params-page">
        <div className="params-title">Paramètres</div>
        <div className="params-subtitle">
          Les modifications sont actives dès le prochain scraping ou scoring — aucun redémarrage nécessaire.
        </div>

        {/* Filtrage */}
        <div className="params-section">
          <div className="params-section-title">
            <span className="params-section-icon">⧖</span> Filtrage des offres
          </div>

          <div className="params-field">
            <div className="params-label">Mots-clés obligatoires</div>
            <TagInput
              values={filtrage.keywords_include}
              onChange={v => setFiltrage(f => ({ ...f, keywords_include: v }))}
            />
            <div className="hint">Au moins un doit être présent dans le titre ou la description. Entrée ou virgule pour ajouter.</div>
          </div>

          <div className="params-field">
            <div className="params-label">Mots-clés exclus</div>
            <TagInput
              values={filtrage.keywords_exclude}
              onChange={v => setFiltrage(f => ({ ...f, keywords_exclude: v }))}
            />
            <div className="hint">Si un de ces mots est trouvé, l'offre est rejetée immédiatement.</div>
          </div>

          <div className="params-row">
            <div className="params-field">
              <div className="params-label">TJM minimum (€)</div>
              <input className="params-input" type="number" placeholder="vide = pas de filtre"
                value={filtrage.budget_min}
                onChange={e => setFiltrage(f => ({ ...f, budget_min: e.target.value }))} />
            </div>
            <div className="params-field">
              <div className="params-label">TJM maximum (€)</div>
              <input className="params-input" type="number" placeholder="vide = pas de filtre"
                value={filtrage.budget_max}
                onChange={e => setFiltrage(f => ({ ...f, budget_max: e.target.value }))} />
            </div>
          </div>

          <div className="params-row">
            <div className="params-field">
              <div className="params-label">Délai minimum avant date limite (jours)</div>
              <input className="params-input" type="number" min="0"
                value={filtrage.min_days_remaining}
                onChange={e => setFiltrage(f => ({ ...f, min_days_remaining: e.target.value }))} />
            </div>
            <div className="params-field">
              <div className="params-label">Score IA minimum affiché</div>
              <input className="params-input" type="number" step="0.5" min="0" max="10"
                value={filtrage.ai_score_threshold}
                onChange={e => setFiltrage(f => ({ ...f, ai_score_threshold: e.target.value }))} />
            </div>
          </div>
        </div>

        {/* Scoring IA */}
        <div className="params-section">
          <div className="params-section-title">
            <span className="params-section-icon">◈</span> Scoring IA
          </div>

          <div className="params-field">
            <div className="params-label">Contexte entreprise</div>
            <textarea className="params-input params-textarea"
              value={scoring.company_context}
              onChange={e => setScoring(s => ({ ...s, company_context: e.target.value }))}
              placeholder="Décrivez votre entreprise : spécialités, TJM, zones géographiques…" />
            <div className="hint">Injecté dans chaque prompt envoyé à Claude. Plus c'est précis, meilleur est le scoring.</div>
          </div>

          <div className="params-field">
            <div className="params-label">Seuils de recommandation</div>
            <div className="seuils-row">
              <div className="seuil-group">
                <span className="seuil-label">🟢 GO si score ≥</span>
                <input className="seuil-input" type="number" step="0.5" min="0" max="10"
                  value={scoring.score_go_threshold}
                  onChange={e => setScoring(s => ({ ...s, score_go_threshold: e.target.value }))} />
              </div>
              <div className="seuil-group">
                <span className="seuil-label">🟡 À étudier si score ≥</span>
                <input className="seuil-input" type="number" step="0.5" min="0" max="10"
                  value={scoring.score_etudier_threshold}
                  onChange={e => setScoring(s => ({ ...s, score_etudier_threshold: e.target.value }))} />
              </div>
              <span className="seuil-label" style={{ color: 'var(--no-go)' }}>🔴 NO GO en dessous</span>
            </div>
          </div>

          <div className="params-field">
            <button className="advanced-toggle" onClick={() => setShowPrompt(p => !p)}>
              {showPrompt ? '▾' : '▸'} Template du prompt {showPrompt ? '(masquer)' : '(afficher)'}
            </button>
            {showPrompt && (
              <>
                <textarea className="params-input params-textarea params-textarea-lg"
                  value={scoring.prompt_template}
                  onChange={e => setScoring(s => ({ ...s, prompt_template: e.target.value }))} />
                <div className="hint">
                  Variables : {'{company_context}'}, {'{titre}'}, {'{acheteur}'}, {'{budget}'}, {'{date_limite}'}, {'{source}'}, {'{description}'}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="params-actions">
          <button className="btn btn-danger" onClick={handleReset}>Réinitialiser</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Sauvegarde…' : 'Sauvegarder'}
          </button>
        </div>
      </div>

      <Toast msg={toast} onClose={() => setToast(null)} />
    </>
  )
}