// src/pages/Offres.jsx
import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useFetch } from '../hooks/useApi'
import { ScoreBadge, RecoBadge } from '../components/ScoreBadge'

const css = `
  .offres { padding:32px; }
  .offres-header { margin-bottom:24px; }
  .offres-title { font-size:32px; }
  .filters { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:24px;
    background:var(--bg2); border:1px solid var(--border); border-radius:var(--r2); padding:16px; }
  .filters input  { flex:1; min-width:200px; }
  .filters select { min-width:150px; }
  .btn-export { background:var(--bg3); color:var(--text2); border:1px solid var(--border);
    margin-left:auto; }
  .btn-export:hover { color:var(--text); border-color:var(--border2); }
  .table-wrap { overflow-x:auto; }
  table { width:100%; border-collapse:collapse; }
  thead th { text-align:left; padding:10px 14px; font-size:11px; text-transform:uppercase;
    letter-spacing:.08em; color:var(--text3); border-bottom:1px solid var(--border);
    font-family:var(--font-mono); font-weight:500; white-space:nowrap; }
  tbody tr { border-bottom:1px solid var(--border); transition:background .1s; }
  tbody tr:hover { background:var(--bg2); }
  tbody td { padding:12px 14px; vertical-align:top; }
  .td-titre { max-width:320px; }
  .td-titre a { color:var(--text); font-size:13px; line-height:1.4; }
  .td-titre a:hover { color:var(--accent); }
  .td-sub  { font-size:11px; color:var(--text3); margin-top:2px; }
  .td-date { white-space:nowrap; font-size:12px; color:var(--text2); }
  .td-budget { white-space:nowrap; font-size:12px; color:var(--text2); }
  .result-count { font-size:13px; color:var(--text3); margin-bottom:12px; }
  .result-count strong { color:var(--text); }
  .empty { text-align:center; padding:64px 0; color:var(--text3); font-size:14px; }
  .pagination { display:flex; gap:8px; margin-top:20px; align-items:center;
    justify-content:flex-end; }
  .pagination button { background:var(--bg3); color:var(--text2);
    border:1px solid var(--border); padding:6px 14px; }
  .pagination button:disabled { opacity:.4; cursor:not-allowed; }
  .pagination button:hover:not(:disabled) { border-color:var(--border2); color:var(--text); }
  .page-info { font-size:12px; color:var(--text3); }
`

function fmtBudget(min, max) {
  if (!max && !min) return '—'
  const fmt = n => n >= 1000 ? `${(n/1000).toFixed(0)}k€` : `${n}€`
  if (min && max) return `${fmt(min)} – ${fmt(max)}`
  return max ? `≤ ${fmt(max)}` : `≥ ${fmt(min)}`
}

export default function Offres() {
  const [search,  setSearch]  = useState('')
  const [reco,    setReco]    = useState('')
  const [statut,  setStatut]  = useState('')
  const [scoreMin,setScoreMin]= useState('')
  const [page,    setPage]    = useState(0)
  const LIMIT = 25

  const filterParams = new URLSearchParams({
    ...(search   && { search }),
    ...(reco     && { recommandation: reco }),
    ...(statut   && { statut }),
    ...(scoreMin && { score_min: scoreMin }),
  })

  const params = new URLSearchParams({
    limit: LIMIT, offset: page * LIMIT,
    ...(search   && { search }),
    ...(reco     && { recommandation: reco }),
    ...(statut   && { statut }),
    ...(scoreMin && { score_min: scoreMin }),
  })

  const { data: offres, loading, refresh } = useFetch(`/offres?${params}`, [search, reco, statut, scoreMin, page])
  const { data: countData, refresh: refreshCount } = useFetch(`/offres/count?${filterParams}`, [search, reco, statut, scoreMin])

  function handleRefresh() { refresh(); refreshCount() }

  function handleSearch(e) { setSearch(e.target.value); setPage(0) }

  return (
    <>
      <style>{css}</style>
      <div className="offres">
        <div className="offres-header" style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
          <h2 className="offres-title">Appels d'offres</h2>
          <button className="btn-export" onClick={handleRefresh} disabled={loading}>
            ↻ Rafraîchir
          </button>
        </div>

        <div className="filters">
          <input
            type="search" placeholder="Rechercher titre, acheteur..."
            value={search} onChange={handleSearch}
          />
          <select value={reco} onChange={e => { setReco(e.target.value); setPage(0) }}>
            <option value="">Toutes reco.</option>
            <option value="go">GO</option>
            <option value="a_etudier">À étudier</option>
            <option value="no_go">NO GO</option>
          </select>
          <select value={statut} onChange={e => { setStatut(e.target.value); setPage(0) }}>
            <option value="">Tous statuts</option>
            <option value="nouveau">Nouveau</option>
            <option value="filtre_ok">Filtre OK</option>
            <option value="scored">Scoré</option>
          </select>
          <select value={scoreMin} onChange={e => { setScoreMin(e.target.value); setPage(0) }}>
            <option value="">Score min.</option>
            <option value="7.5">7.5+ ★★★</option>
            <option value="5">5+ ★★</option>
            <option value="2.5">2.5+ ★</option>
          </select>
          <a href="/api/export/csv" target="_blank">
            <button className="btn-export">↓ Export CSV</button>
          </a>
        </div>

        {countData != null && (
          <div className="result-count">
            <strong>{countData.count}</strong> résultat{countData.count !== 1 ? 's' : ''}
          </div>
        )}

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
                    <th>Score IA</th>
                    <th>Reco.</th>
                    <th>Budget</th>
                    <th>Date limite</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {offres.map(o => (
                    <tr key={o.id}>
                      <td className="td-titre">
                        <Link to={`/offres/${o.id}`}>{o.titre}</Link>
                        {o.acheteur && <div className="td-sub">{o.acheteur}</div>}
                      </td>
                      <td><ScoreBadge score={o.score} /></td>
                      <td>{o.recommandation ? <RecoBadge reco={o.recommandation} /> : <span style={{color:'var(--text3)'}}>—</span>}</td>
                      <td className="td-budget">{fmtBudget(o.budget_min, o.budget_max)}</td>
                      <td className="td-date">{o.date_limite || '—'}</td>
                      <td><span style={{fontSize:11,color:'var(--text3)'}}>{o.source}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <button disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Préc.</button>
              <span className="page-info">Page {page + 1}</span>
              <button disabled={offres.length < LIMIT} onClick={() => setPage(p => p + 1)}>Suiv. →</button>
            </div>
          </>
        )}
      </div>
    </>
  )
}
