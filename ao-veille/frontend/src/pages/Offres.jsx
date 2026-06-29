// src/pages/Offres.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { ScoreBadge, RecoBadge } from '../components/ScoreBadge'

const css = `
  .offres { padding:32px; }
  .offres-title { font-size:32px; margin-bottom:20px; }
  .offres-layout { display:flex; gap:24px; align-items:flex-start; }

  /* Panneau filtres */
  .filters-panel { width:260px; flex-shrink:0; background:var(--bg2);
    border:1px solid var(--border); border-radius:var(--r2); padding:16px;
    position:sticky; top:24px; }
  .filters-panel h3 { font-size:11px; text-transform:uppercase; letter-spacing:.08em;
    color:var(--text3); margin:0 0 12px 0; font-family:var(--font-mono); }
  .filter-section { margin-bottom:14px; }
  .filter-label { font-size:10px; text-transform:uppercase; letter-spacing:.06em;
    color:var(--text3); margin-bottom:6px; font-weight:600; }
  .filter-input { width:100%; background:var(--bg); border:1px solid var(--border);
    border-radius:6px; padding:6px 8px; color:inherit; font-size:13px; box-sizing:border-box; }
  .filter-input:focus { outline:none; border-color:var(--accent); }
  .filter-chips { display:flex; gap:6px; flex-wrap:wrap; }
  .chip { padding:3px 10px; border-radius:20px; border:1px solid var(--border);
    background:transparent; color:var(--text3); cursor:pointer; font-size:11px;
    font-weight:600; transition:all .15s; }
  .chip.active-go     { border-color:#2ecc8a; background:#2ecc8a22; color:#2ecc8a; }
  .chip.active-etudier{ border-color:#f0a848; background:#f0a84822; color:#f0a848; }
  .chip.active-nogo   { border-color:#e05c6a; background:#e05c6a22; color:#e05c6a; }
  .chip.active-src    { border-color:#4f8ef7; background:#4f8ef722; color:#4f8ef7; }
  .range-row { display:flex; gap:6px; align-items:center; }
  .range-row input { flex:1; }
  .range-sep { font-size:11px; color:var(--text3); }
  .tag-pill { display:inline-flex; align-items:center; gap:3px; padding:2px 8px;
    border-radius:20px; background:#4f8ef722; color:#4f8ef7; font-size:11px; }
  .tag-pill button { background:none; border:none; color:#4f8ef7; cursor:pointer;
    padding:0; line-height:1; font-size:12px; }
  .btn-reset { width:100%; background:transparent; color:var(--text3);
    border:1px solid var(--border); padding:6px; border-radius:8px;
    cursor:pointer; font-size:12px; margin-top:6px; }
  .saved-item { display:flex; align-items:center; gap:4px; margin-bottom:4px; }
  .saved-btn { flex:1; text-align:left; background:transparent; border:1px solid var(--border);
    border-radius:6px; padding:4px 8px; cursor:pointer; font-size:11px; color:inherit; }
  .saved-del { background:transparent; border:none; color:#e05c6a; cursor:pointer;
    font-size:13px; padding:0 2px; }

  /* Tableau */
  .offres-main { flex:1; min-width:0; }
  .table-toolbar { display:flex; justify-content:space-between; align-items:center;
    margin-bottom:12px; }
  .table-count { font-size:12px; color:var(--text3); }
  .btn-export { background:var(--bg3); color:var(--text2); border:1px solid var(--border);
    padding:6px 14px; border-radius:6px; cursor:pointer; font-size:12px; }
  .btn-export:hover { color:var(--text); border-color:var(--border2); }
  .table-wrap { overflow-x:auto; }
  table { width:100%; border-collapse:collapse; }
  thead th { text-align:left; padding:10px 14px; font-size:11px; text-transform:uppercase;
    letter-spacing:.08em; color:var(--text3); border-bottom:1px solid var(--border);
    font-family:var(--font-mono); font-weight:500; white-space:nowrap; }
  tbody tr { border-bottom:1px solid var(--border); transition:background .1s; }
  tbody tr:hover { background:var(--bg2); }
  tbody td { padding:10px 14px; vertical-align:middle; }
  .td-titre { max-width:300px; }
  .td-titre a { color:var(--text); font-size:13px; line-height:1.4; }
  .td-titre a:hover { color:var(--accent); }
  .td-sub { font-size:11px; color:var(--text3); margin-top:2px; }
  .td-tags { display:flex; flex-wrap:wrap; gap:3px; }
  .td-action { font-size:11px; }
  .td-date { white-space:nowrap; font-size:12px; color:var(--text2); }
  .td-budget { white-space:nowrap; font-size:12px; color:var(--text2); }
  .new-badge { background:#4f8ef722; color:#4f8ef7; border-radius:20px;
    padding:1px 7px; font-size:10px; font-weight:700; margin-left:6px; }
  .empty { text-align:center; padding:64px 0; color:var(--text3); font-size:14px; }
  .pagination { display:flex; gap:8px; margin-top:20px; align-items:center;
    justify-content:flex-end; }
  .pagination button { background:var(--bg3); color:var(--text2);
    border:1px solid var(--border); padding:6px 14px; border-radius:6px; cursor:pointer; }
  .pagination button:disabled { opacity:.4; cursor:not-allowed; }
  .pagination button:hover:not(:disabled) { border-color:var(--border2); color:var(--text); }
  .page-info { font-size:12px; color:var(--text3); }
`

const RECOS = [
  { value: "go",        label: "GO",        cls: "active-go" },
  { value: "a_etudier", label: "À étudier", cls: "active-etudier" },
  { value: "no_go",     label: "NO GO",     cls: "active-nogo" },
]

const LIMIT = 25

function fmtBudget(min, max) {
  if (!max && !min) return '—'
  const fmt = n => n >= 1000 ? `${(n/1000).toFixed(0)}k€` : `${n}€`
  if (min && max) return `${fmt(min)} – ${fmt(max)}`
  return max ? `≤ ${fmt(max)}` : `≥ ${fmt(min)}`
}

export default function Offres() {
  const { request, downloadCsv } = useApi()
  const [searchParams, setSearchParams] = useSearchParams()

  const q          = searchParams.get('q')          || ''
  const scoreMin   = searchParams.get('scoreMin')   || ''
  const scoreMax   = searchParams.get('scoreMax')   || ''
  const recos      = searchParams.get('recos')      ? searchParams.get('recos').split(',') : []
  const sources    = searchParams.get('sources')    ? searchParams.get('sources').split(',') : []
  const dateDu     = searchParams.get('dateDu')     || ''
  const dateAu     = searchParams.get('dateAu')     || ''
  const budgetMin  = searchParams.get('budgetMin')  || ''
  const budgetMax  = searchParams.get('budgetMax')  || ''
  const tags       = searchParams.get('tags')       ? searchParams.get('tags').split(',') : []
  const nonVues    = searchParams.get('nonVues')    === 'true'
  const inTitre    = searchParams.get('inTitre')    !== 'false'
  const inDesc     = searchParams.get('inDesc')     !== 'false'
  const inAcheteur = searchParams.get('inAcheteur') === 'true'
  const page       = parseInt(searchParams.get('page') || '0', 10)

  const [qInput, setQInput]         = useState(q)
  const [scoreMinI, setScoreMinI]   = useState(scoreMin)
  const [scoreMaxI, setScoreMaxI]   = useState(scoreMax)
  const [budgetMinI, setBudgetMinI] = useState(budgetMin)
  const [budgetMaxI, setBudgetMaxI] = useState(budgetMax)
  const [tagInput, setTagInput]     = useState('')

  const [offres, setOffres]                   = useState([])
  const [loading, setLoading]                 = useState(true)
  const [sourcesAll, setSourcesAll]           = useState([])
  const [knownTags, setKnownTags]             = useState([])
  const [savedSearches, setSavedSearches]     = useState([])
  const [showSave, setShowSave]               = useState(false)
  const [saveName, setSaveName]               = useState('')
  const [saveNotify, setSaveNotify]           = useState(false)

  useEffect(() => { loadMeta() }, [])

  async function loadMeta() {
    const [srcs, saved, knownT] = await Promise.all([
      request("/api/sources"),
      request("/api/search/saved"),
      request("/api/tags"),
    ])
    if (srcs)   setSourcesAll(srcs.map(s => s.name))
    if (saved)  setSavedSearches(saved)
    if (knownT) setKnownTags(knownT)
  }

  const loadOffres = useCallback(async () => {
    setLoading(true)
    try {
      const filters = {
        q, in_titre: inTitre, in_description: inDesc, in_acheteur: inAcheteur,
        score_min:          scoreMin  !== '' ? parseFloat(scoreMin)  : undefined,
        score_max:          scoreMax  !== '' ? parseFloat(scoreMax)  : undefined,
        recommandation:     recos.length   ? recos   : undefined,
        source:             sources.length ? sources : undefined,
        date_limite_from:   dateDu   || undefined,
        date_limite_to:     dateAu   || undefined,
        budget_min:         budgetMin !== '' ? parseFloat(budgetMin) : undefined,
        budget_max:         budgetMax !== '' ? parseFloat(budgetMax) : undefined,
        tags:               tags.length ? tags : undefined,
        non_vues_seulement: nonVues || undefined,
        limit:  LIMIT,
        offset: page * LIMIT,
      }
      const data = await request("/api/search", {
        method: "POST",
        body: JSON.stringify(filters),
      })
      if (data) setOffres(data)
    } finally {
      setLoading(false)
    }
  }, [request, q, inTitre, inDesc, inAcheteur, scoreMin, scoreMax,
      recos.join(','), sources.join(','), dateDu, dateAu,
      budgetMin, budgetMax, tags.join(','), nonVues, page])

  useEffect(() => { loadOffres() }, [loadOffres])

  function setParam(key, value) {
    const next = new URLSearchParams(searchParams)
    if (value !== '' && value !== null && value !== undefined) {
      next.set(key, value)
    } else {
      next.delete(key)
    }
    next.delete('page')
    setSearchParams(next, { replace: true })
  }

  function setPage(fn) {
    const next = new URLSearchParams(searchParams)
    const newPage = typeof fn === 'function' ? fn(page) : fn
    next.set('page', String(newPage))
    setSearchParams(next, { replace: true })
  }

  function toggleReco(v) {
    const next = recos.includes(v) ? recos.filter(x => x !== v) : [...recos, v]
    setParam('recos', next.join(','))
  }

  function toggleSource(v) {
    const next = sources.includes(v) ? sources.filter(x => x !== v) : [...sources, v]
    setParam('sources', next.join(','))
  }

  function addTag(label) {
    const t = label.trim().toLowerCase()
    if (!t || tags.includes(t)) return
    setParam('tags', [...tags, t].join(','))
    setTagInput('')
  }

  function removeTag(t) {
    setParam('tags', tags.filter(x => x !== t).join(','))
  }

  function applyTextFilters() {
    const next = new URLSearchParams(searchParams)
    qInput     ? next.set('q', qInput)           : next.delete('q')
    scoreMinI  ? next.set('scoreMin', scoreMinI) : next.delete('scoreMin')
    scoreMaxI  ? next.set('scoreMax', scoreMaxI) : next.delete('scoreMax')
    budgetMinI ? next.set('budgetMin', budgetMinI) : next.delete('budgetMin')
    budgetMaxI ? next.set('budgetMax', budgetMaxI) : next.delete('budgetMax')
    next.delete('page')
    setSearchParams(next, { replace: true })
  }

  function resetFilters() {
    setQInput(''); setScoreMinI(''); setScoreMaxI('')
    setBudgetMinI(''); setBudgetMaxI(''); setTagInput('')
    setSearchParams(new URLSearchParams(), { replace: true })
  }

  function buildFilters() {
    return {
      q, in_titre: inTitre, in_description: inDesc, in_acheteur: inAcheteur,
      score_min:          scoreMin  !== '' ? parseFloat(scoreMin)  : undefined,
      score_max:          scoreMax  !== '' ? parseFloat(scoreMax)  : undefined,
      recommandation:     recos.length   ? recos   : undefined,
      source:             sources.length ? sources : undefined,
      date_limite_from:   dateDu   || undefined,
      date_limite_to:     dateAu   || undefined,
      budget_min:         budgetMin !== '' ? parseFloat(budgetMin) : undefined,
      budget_max:         budgetMax !== '' ? parseFloat(budgetMax) : undefined,
      tags:               tags.length ? tags : undefined,
      non_vues_seulement: nonVues || undefined,
    }
  }

  function loadSaved(s) {
    const f = s.filters
    const next = new URLSearchParams()
    if (f.q)                    next.set('q', f.q)
    if (f.score_min != null)    next.set('scoreMin', f.score_min)
    if (f.score_max != null)    next.set('scoreMax', f.score_max)
    if (f.recommandation?.length) next.set('recos', f.recommandation.join(','))
    if (f.source?.length)       next.set('sources', f.source.join(','))
    if (f.date_limite_from)     next.set('dateDu', f.date_limite_from)
    if (f.date_limite_to)       next.set('dateAu', f.date_limite_to)
    if (f.budget_min != null)   next.set('budgetMin', f.budget_min)
    if (f.budget_max != null)   next.set('budgetMax', f.budget_max)
    if (f.tags?.length)         next.set('tags', f.tags.join(','))
    if (f.non_vues_seulement)   next.set('nonVues', 'true')
    setSearchParams(next, { replace: true })
    setQInput(f.q || '')
    setScoreMinI(f.score_min != null ? String(f.score_min) : '')
    setScoreMaxI(f.score_max != null ? String(f.score_max) : '')
    setBudgetMinI(f.budget_min != null ? String(f.budget_min) : '')
    setBudgetMaxI(f.budget_max != null ? String(f.budget_max) : '')
  }

  async function handleSaveSearch() {
    if (!saveName.trim()) return
    await request("/api/search/saved", {
      method: "POST",
      body: JSON.stringify({ name: saveName, filters: buildFilters(), notify: saveNotify }),
    })
    setSaveName(''); setShowSave(false)
    loadMeta()
  }

  async function handleDeleteSaved(id) {
    await request(`/api/search/saved/${id}`, { method: "DELETE" })
    loadMeta()
  }

  async function handleAction(offreId, action) {
    await request(`/api/offres/${offreId}/action`, {
      method: "POST",
      body: JSON.stringify({ action }),
    })
    setOffres(prev => prev.map(o => o.id === offreId ? { ...o, action } : o))
  }

  async function handleAddTag(offreId, label) {
    const t = label.trim().toLowerCase()
    if (!t) return
    await request(`/api/offres/${offreId}/tags`, {
      method: "POST",
      body: JSON.stringify({ label: t }),
    })
    setOffres(prev => prev.map(o => o.id === offreId
      ? { ...o, tags: [...(o.tags||[]).filter(x => x.label !== t), { label: t, color: "#4f8ef7" }] }
      : o
    ))
    loadMeta()
  }

  async function handleRemoveTag(offreId, label) {
    await request(`/api/offres/${offreId}/tags/${encodeURIComponent(label)}`, { method: "DELETE" })
    setOffres(prev => prev.map(o => o.id === offreId
      ? { ...o, tags: (o.tags||[]).filter(x => x.label !== label) }
      : o
    ))
    loadMeta()
  }

  const activeFiltersCount = [
    q, scoreMin, scoreMax, budgetMin, budgetMax, dateDu, dateAu,
    recos.length, sources.length, tags.length, nonVues
  ].filter(Boolean).length

  return (
    <>
      <style>{css}</style>
      <div className="offres">
        <h2 className="offres-title">Appels d'offres</h2>

        <div className="offres-layout">

          {/* Panneau filtres */}
          <div className="filters-panel">
            <h3>Filtres {activeFiltersCount > 0 && `(${activeFiltersCount})`}</h3>

            <div className="filter-section">
              <div className="filter-label">Texte libre</div>
              <input
                className="filter-input"
                value={qInput}
                onChange={e => setQInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && applyTextFilters()}
                onBlur={applyTextFilters}
                placeholder="java angular…"
              />
              <div style={{ display:'flex', gap:8, marginTop:6, fontSize:11 }}>
                <label style={{ display:'flex', alignItems:'center', gap:3, cursor:'pointer' }}>
                  <input type="checkbox" checked={inTitre}
                    onChange={e => setParam('inTitre', e.target.checked ? null : 'false')} />
                  Titre
                </label>
                <label style={{ display:'flex', alignItems:'center', gap:3, cursor:'pointer' }}>
                  <input type="checkbox" checked={inDesc}
                    onChange={e => setParam('inDesc', e.target.checked ? null : 'false')} />
                  Description
                </label>
                <label style={{ display:'flex', alignItems:'center', gap:3, cursor:'pointer' }}>
                  <input type="checkbox" checked={inAcheteur}
                    onChange={e => setParam('inAcheteur', e.target.checked ? 'true' : null)} />
                  Acheteur
                </label>
              </div>
            </div>

            <div className="filter-section">
              <div className="filter-label">Recommandation</div>
              <div className="filter-chips">
                {RECOS.map(r => (
                  <button key={r.value}
                    className={`chip ${recos.includes(r.value) ? r.cls : ''}`}
                    onClick={() => toggleReco(r.value)}>
                    {r.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-section">
              <div className="filter-label">Score IA</div>
              <div className="range-row">
                <input className="filter-input" value={scoreMinI}
                  onChange={e => setScoreMinI(e.target.value)}
                  onBlur={applyTextFilters} placeholder="min" />
                <span className="range-sep">–</span>
                <input className="filter-input" value={scoreMaxI}
                  onChange={e => setScoreMaxI(e.target.value)}
                  onBlur={applyTextFilters} placeholder="max" />
              </div>
            </div>

            <div className="filter-section">
              <div className="filter-label">Budget TJM (€)</div>
              <div className="range-row">
                <input className="filter-input" value={budgetMinI}
                  onChange={e => setBudgetMinI(e.target.value)}
                  onBlur={applyTextFilters} placeholder="min" />
                <span className="range-sep">–</span>
                <input className="filter-input" value={budgetMaxI}
                  onChange={e => setBudgetMaxI(e.target.value)}
                  onBlur={applyTextFilters} placeholder="max" />
              </div>
            </div>

            <div className="filter-section">
              <div className="filter-label">Date limite</div>
              <div className="range-row">
                <input
                  type="text"
                  className="filter-input"
                  value={dateDu}
                  onChange={e => setParam('dateDu', e.target.value)}
                  placeholder="YYYY-MM-DD"
                />
                <span className="range-sep">→</span>
                <input
                  type="text"
                  className="filter-input"
                  value={dateAu}
                  onChange={e => setParam('dateAu', e.target.value)}
                  placeholder="YYYY-MM-DD"
                />
              </div>
            </div>

            <div className="filter-section">
              <div className="filter-label">Source</div>
              <div className="filter-chips">
                {sourcesAll.map(s => (
                  <button key={s}
                    className={`chip ${sources.includes(s) ? 'active-src' : ''}`}
                    onClick={() => toggleSource(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-section">
              <div className="filter-label">Mes tags</div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:4, marginBottom:6 }}>
                {tags.map(t => (
                  <span key={t} className="tag-pill">
                    {t}
                    <button onClick={() => removeTag(t)}>×</button>
                  </span>
                ))}
              </div>
              <div style={{ display:'flex', gap:4 }}>
                <input className="filter-input" value={tagInput}
                  onChange={e => setTagInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addTag(tagInput)}
                  placeholder="+ tag" list="known-tags-filter" />
                <datalist id="known-tags-filter">
                  {knownTags.map(t => <option key={t.label} value={t.label} />)}
                </datalist>
                <button onClick={() => addTag(tagInput)}
                  style={{ background:'var(--bg)', border:'1px solid var(--border)',
                           borderRadius:6, padding:'0 8px', cursor:'pointer' }}>+</button>
              </div>
            </div>

            <div className="filter-section">
              <label style={{ display:'flex', alignItems:'center', gap:6,
                              cursor:'pointer', fontSize:12 }}>
                <input type="checkbox" checked={nonVues}
                  onChange={e => setParam('nonVues', e.target.checked ? 'true' : null)} />
                Non vues uniquement
              </label>
            </div>

            <button className="btn-reset" onClick={resetFilters}>
              Réinitialiser les filtres
            </button>

            <div style={{ marginTop:14, borderTop:'1px solid var(--border)', paddingTop:12 }}>
              {!showSave ? (
                <button onClick={() => setShowSave(true)}
                  style={{ width:'100%', background:'transparent', color:'var(--text3)',
                           border:'1px solid var(--border)', padding:'5px', borderRadius:6,
                           cursor:'pointer', fontSize:11 }}>
                  Sauvegarder cette recherche
                </button>
              ) : (
                <div>
                  <input className="filter-input" value={saveName}
                    onChange={e => setSaveName(e.target.value)}
                    placeholder="Nom…" style={{ marginBottom:6 }} />
                  <label style={{ display:'flex', alignItems:'center', gap:4,
                                  fontSize:11, marginBottom:6 }}>
                    <input type="checkbox" checked={saveNotify}
                      onChange={e => setSaveNotify(e.target.checked)} />
                    Notifier sur nouvelles offres
                  </label>
                  <div style={{ display:'flex', gap:4 }}>
                    <button onClick={handleSaveSearch}
                      style={{ flex:1, background:'var(--accent)', color:'#fff', border:'none',
                               borderRadius:6, padding:'5px', cursor:'pointer', fontSize:11 }}>
                      Sauvegarder
                    </button>
                    <button onClick={() => setShowSave(false)}
                      style={{ background:'transparent', border:'1px solid var(--border)',
                               borderRadius:6, padding:'5px 8px', cursor:'pointer', fontSize:11 }}>
                      ✕
                    </button>
                  </div>
                </div>
              )}

              {savedSearches.length > 0 && (
                <div style={{ marginTop:10 }}>
                  <div style={{ fontSize:10, color:'var(--text3)', marginBottom:4,
                                textTransform:'uppercase', letterSpacing:'.06em' }}>
                    Recherches sauvegardées
                  </div>
                  {savedSearches.map(s => (
                    <div key={s.id} className="saved-item">
                      <button className="saved-btn" onClick={() => loadSaved(s)}>
                        {s.name}{s.notify && <span style={{ marginLeft:4, color:'#4f8ef7' }}>*</span>}
                      </button>
                      <button className="saved-del" onClick={() => handleDeleteSaved(s.id)}>✕</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Tableau */}
          <div className="offres-main">
            <div className="table-toolbar">
              <span className="table-count">
                {loading ? 'Chargement…' : `${offres.length} offre(s)${offres.length === LIMIT ? '+' : ''}`}
              </span>
              <button className="btn-export" onClick={downloadCsv}>Export CSV</button>
            </div>

            {loading ? (
              <div className="empty">Chargement...</div>
            ) : !offres?.length ? (
              <div className="empty">Aucune offre trouvée</div>
            ) : (
              <>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Titre / Acheteur</th>
                        <th>Score</th>
                        <th>Reco.</th>
                        <th>Budget</th>
                        <th>Date limite</th>
                        <th>Tags</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {offres.map(o => (
                        <OffreRow
                          key={o.id}
                          offre={o}
                          searchParams={searchParams}
                          onAction={handleAction}
                          onAddTag={handleAddTag}
                          onRemoveTag={handleRemoveTag}
                          knownTags={knownTags}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="pagination">
                  <button disabled={page === 0} onClick={() => setPage(p => p - 1)}>Préc.</button>
                  <span className="page-info">Page {page + 1}</span>
                  <button disabled={offres.length < LIMIT} onClick={() => setPage(p => p + 1)}>Suiv.</button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

function OffreRow({ offre: o, searchParams, onAction, onAddTag, onRemoveTag, knownTags }) {
  const [tagInput, setTagInput]       = useState('')
  const [showTagInput, setShowTagInput] = useState(false)

  const recoColor = o.recommandation === 'go'    ? '#2ecc8a'
                  : o.recommandation === 'no_go' ? '#e05c6a'
                  : '#f0a848'

  return (
    <tr style={{ borderLeft: o.recommandation ? `3px solid ${recoColor}` : '3px solid transparent' }}>
      <td className="td-titre">
        <Link
          to={`/offres/${o.id}`}
          state={{ from: `/offres?${searchParams.toString()}` }}
        >
          {o.titre}
          {!o.vue && <span className="new-badge">NEW</span>}
        </Link>
        {o.acheteur && <div className="td-sub">{o.acheteur}</div>}
      </td>
      <td><ScoreBadge score={o.score} /></td>
      <td>
        {o.recommandation
          ? <RecoBadge reco={o.recommandation} />
          : <span style={{ color:'var(--text3)' }}>—</span>}
      </td>
      <td className="td-budget">{fmtBudget(o.budget_min, o.budget_max)}</td>
      <td className="td-date">{o.date_limite || '—'}</td>

      <td>
        <div className="td-tags">
          {(o.tags || []).map(t => (
            <span key={t.label} style={{
              background: (t.color||'#4f8ef7') + '22', color: t.color||'#4f8ef7',
              borderRadius:20, padding:'1px 7px', fontSize:10,
              display:'inline-flex', alignItems:'center', gap:2
            }}>
              {t.label}
              <button onClick={() => onRemoveTag(o.id, t.label)}
                style={{ background:'none', border:'none', color:'inherit',
                         cursor:'pointer', padding:0, fontSize:11, lineHeight:1 }}>×</button>
            </span>
          ))}
          {showTagInput ? (
            <input
              autoFocus
              value={tagInput}
              onChange={e => setTagInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter')  { onAddTag(o.id, tagInput); setTagInput(''); setShowTagInput(false) }
                if (e.key === 'Escape') { setShowTagInput(false) }
              }}
              onBlur={() => { if (tagInput) onAddTag(o.id, tagInput); setShowTagInput(false); setTagInput('') }}
              list="known-tags-row"
              style={{ width:70, fontSize:11, background:'var(--bg)',
                       border:'1px solid var(--border)', borderRadius:20,
                       padding:'1px 6px', color:'inherit' }}
            />
          ) : (
            <button onClick={() => setShowTagInput(true)}
              style={{ background:'none', border:'1px dashed var(--border)', borderRadius:20,
                       padding:'1px 7px', fontSize:10, color:'var(--text3)', cursor:'pointer' }}>
              + tag
            </button>
          )}
          <datalist id="known-tags-row">
            {knownTags.map(t => <option key={t.label} value={t.label} />)}
          </datalist>
        </div>
      </td>

      <td className="td-action">
        <select
          value={o.action || ''}
          onChange={e => onAction(o.id, e.target.value || null)}
          style={{ background:'var(--bg)', border:'1px solid var(--border)',
                   borderRadius:6, padding:'3px 6px', fontSize:11, color:'inherit',
                   cursor:'pointer' }}
        >
          <option value="">—</option>
          <option value="ignoré">Ignoré</option>
          <option value="répondu">Répondu</option>
          <option value="gagné">Gagné</option>
          <option value="perdu">Perdu</option>
        </select>
      </td>
    </tr>
  )
}