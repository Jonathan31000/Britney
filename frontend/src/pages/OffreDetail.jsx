// src/pages/OffreDetail.jsx
import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useFetch } from '../hooks/useApi'
import { ScoreBadge, RecoBadge } from '../components/ScoreBadge'

const css = `
  .detail { padding:32px; max-width:860px; }
  .detail-back { font-size:12px; color:var(--text3); margin-bottom:24px; display:inline-flex;
    align-items:center; gap:6px; }
  .detail-back:hover { color:var(--accent); }
  .detail-header { display:flex; align-items:flex-start; justify-content:space-between;
    gap:20px; margin-bottom:24px; }
  .detail-titre { font-size:26px; color:var(--text); line-height:1.3; flex:1; }
  .detail-badges { display:flex; gap:8px; flex-shrink:0; align-items:flex-start; }
  .meta-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:28px; }
  .meta-card { background:var(--bg2); border:1px solid var(--border);
    border-radius:var(--r2); padding:14px 16px; }
  .meta-label { font-size:10px; text-transform:uppercase; letter-spacing:.08em;
    color:var(--text3); margin-bottom:4px; }
  .meta-val   { font-size:14px; color:var(--text); }
  .section { background:var(--bg2); border:1px solid var(--border);
    border-radius:var(--r2); padding:20px 24px; margin-bottom:16px; }
  .section-title { font-size:11px; text-transform:uppercase; letter-spacing:.08em;
    color:var(--text3); margin-bottom:12px; }
  .description { font-size:13px; line-height:1.8; color:var(--text); white-space:pre-wrap;
    word-break:break-word; }
  .points ul { list-style:none; padding:0; }
  .points li { font-size:13px; padding:4px 0; display:flex; gap:8px; align-items:flex-start; }
  .points li::before { flex-shrink:0; }
  .pt-fort li::before  { content:'↑'; color:var(--go); }
  .pt-faible li::before { content:'↓'; color:var(--no-go); }
  .resume-text { font-size:14px; line-height:1.7; color:var(--text); font-style:italic; }
  .justif     { font-size:13px; color:var(--text2); margin-top:8px; }
  .btn-ext { display:inline-flex; align-items:center; gap:8px; background:var(--accent);
    color:#fff; padding:10px 20px; border-radius:var(--r); font-size:13px; cursor:pointer;
    font-family:var(--font-mono); text-decoration:none; }
  .btn-ext:hover { background:var(--accent2); color:#fff; }
`

function fmtBudget(min, max) {
  if (!max && !min) return 'Non renseigné'
  const fmt = n => n >= 1000 ? `${(n/1000).toFixed(0)} 000 €` : `${n} €`
  if (min && max && min !== max) return `${fmt(min)} – ${fmt(max)}`
  return max ? `${fmt(max)}` : `${fmt(min)}`
}

export default function OffreDetail() {
  const { id } = useParams()
  const { data: o, loading, error } = useFetch(`/offres/${id}`)

  if (loading) return <div style={{padding:32,color:'var(--text3)'}}>Chargement...</div>
  if (error || !o) return <div style={{padding:32,color:'var(--no-go)'}}>Offre introuvable.</div>

  return (
    <>
      <style>{css}</style>
      <div className="detail">
        <Link to="/offres" className="detail-back">← Retour à la liste</Link>

        <div className="detail-header">
          <h2 className="detail-titre">{o.titre}</h2>
          <div className="detail-badges">
            <ScoreBadge score={o.score} />
            {o.recommandation && <RecoBadge reco={o.recommandation} />}
          </div>
        </div>

        <div className="meta-grid">
          <div className="meta-card">
            <div className="meta-label">Acheteur</div>
            <div className="meta-val">{o.acheteur || '—'}</div>
          </div>
          <div className="meta-card">
            <div className="meta-label">Budget estimé</div>
            <div className="meta-val">{fmtBudget(o.budget_min, o.budget_max)}</div>
          </div>
          <div className="meta-card">
            <div className="meta-label">Date limite</div>
            <div className="meta-val" style={{color: o.date_limite ? 'var(--etudier)' : 'var(--text)'}}>
              {o.date_limite || '—'}
            </div>
          </div>
          <div className="meta-card">
            <div className="meta-label">Source</div>
            <div className="meta-val">{o.source}</div>
          </div>
          <div className="meta-card">
            <div className="meta-label">Collecté le</div>
            <div className="meta-val">{o.created_at?.slice(0,10) || '—'}</div>
          </div>
          <div className="meta-card">
            <div className="meta-label">Statut</div>
            <div className="meta-val">{o.statut}</div>
          </div>
        </div>

        {/* Résumé IA */}
        {o.resume && (
          <div className="section">
            <div className="section-title">Analyse IA</div>
            <p className="resume-text">{o.resume}</p>
          </div>
        )}

        {/* Points forts / faibles */}
        {(o.points_forts?.length > 0 || o.points_faibles?.length > 0) && (
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:16, marginBottom:16}}>
            {o.points_forts?.length > 0 && (
              <div className="section points pt-fort">
                <div className="section-title">Points forts</div>
                <ul>{o.points_forts.map((p,i) => <li key={i}>{p}</li>)}</ul>
              </div>
            )}
            {o.points_faibles?.length > 0 && (
              <div className="section points pt-faible">
                <div className="section-title">Points faibles</div>
                <ul>{o.points_faibles.map((p,i) => <li key={i}>{p}</li>)}</ul>
              </div>
            )}
          </div>
        )}

        {/* Description complète */}
        <div className="section">
          <div className="section-title">Description complète</div>
          <p className="description">{o.description || 'Aucune description disponible.'}</p>
        </div>

        {/* Lien source */}
        {o.url && (
          <a href={o.url} target="_blank" rel="noreferrer" className="btn-ext">
            ↗ Voir sur {o.source}
          </a>
        )}
      </div>
    </>
  )
}
