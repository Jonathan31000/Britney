// src/pages/Dashboard.jsx
import React, { useState } from 'react'
import { useFetch, triggerAction } from '../hooks/useApi'

const css = `
  .dash { padding:32px; }
  .dash-header { display:flex; align-items:flex-end; justify-content:space-between; margin-bottom:32px; }
  .dash-title  { font-size:32px; color:var(--text); }
  .dash-sub    { font-size:13px; color:var(--text3); margin-top:4px; }
  .dash-actions { display:flex; gap:10px; }
  .btn-primary { background:var(--accent); color:#fff; padding:10px 20px; font-weight:500; }
  .btn-primary:hover { background:var(--accent2); }
  .btn-ghost { background:var(--bg3); color:var(--text2); border:1px solid var(--border); }
  .btn-ghost:hover { border-color:var(--border2); color:var(--text); }
  .btn-ghost:disabled { opacity:.5; cursor:not-allowed; }
  .stats-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:32px; }
  .stat-card { background:var(--bg2); border:1px solid var(--border); border-radius:var(--r2);
    padding:20px 24px; }
  .stat-value { font-family:var(--font-head); font-size:36px; font-weight:800; line-height:1; }
  .stat-label { font-size:12px; color:var(--text3); margin-top:6px; text-transform:uppercase;
    letter-spacing:.08em; }
  .reco-grid  { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:32px; }
  .reco-card  { background:var(--bg2); border:1px solid var(--border); border-radius:var(--r2);
    padding:20px 24px; display:flex; align-items:center; gap:16px; }
  .reco-dot   { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
  .reco-n     { font-family:var(--font-head); font-size:28px; font-weight:800; }
  .reco-l     { font-size:12px; color:var(--text3); margin-top:2px; }
  .sources-card { background:var(--bg2); border:1px solid var(--border);
    border-radius:var(--r2); padding:20px 24px; }
  .sources-title { font-size:13px; color:var(--text3); text-transform:uppercase;
    letter-spacing:.08em; margin-bottom:14px; }
  .source-row { display:flex; align-items:center; justify-content:space-between;
    padding:8px 0; border-bottom:1px solid var(--border); }
  .source-row:last-child { border-bottom:none; }
  .source-bar { height:4px; background:var(--accent); border-radius:2px; margin-top:4px; }
  .toast { position:fixed; bottom:24px; right:24px; background:var(--bg3);
    border:1px solid var(--border2); border-radius:var(--r2); padding:12px 20px;
    font-size:13px; color:var(--text); animation:fadein .2s; z-index:999; }
  @keyframes fadein { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }
`

export default function Dashboard() {
  const { data: stats, loading, refresh } = useFetch('/stats')
  const [toast, setToast] = useState(null)
  const [running, setRunning] = useState(false)

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  async function handleScrape() {
    setRunning(true)
    showToast('Scraping lancé...')
    const r = await triggerAction('/trigger/scrape')
    showToast(r.status === 'ok' ? `Scraping OK : ${r.message}` : `Erreur : ${r.message}`)
    setRunning(false)
    refresh()
  }

  async function handleScore() {
    setRunning(true)
    showToast('Scoring IA lancé...')
    const r = await triggerAction('/trigger/score')
    showToast(r.status === 'ok' ? `Scoring OK : ${r.message}` : `Erreur : ${r.message}`)
    setRunning(false)
    refresh()
  }

  if (loading) return <div style={{padding:32,color:'var(--text3)'}}>Chargement...</div>

  const total = stats?.total || 0

  return (
    <>
      <style>{css}</style>
      <div className="dash">
        <div className="dash-header">
          <div>
            <h2 className="dash-title">Tableau de bord</h2>
            <p className="dash-sub">Vue d'ensemble des appels d'offres collectés</p>
          </div>
          <div className="dash-actions">
            <button className="btn-ghost" onClick={handleScore} disabled={running}>
              ◈ Scorer IA
            </button>
            <button className="btn-primary" onClick={handleScrape} disabled={running}>
              ↻ Lancer scraping
            </button>
          </div>
        </div>

        {/* Stats principales */}
        <div className="stats-grid">
          {[
            { v: stats?.total,     l: 'Total offres',    c: 'var(--text)' },
            { v: stats?.nouvelles, l: 'Non traitées',    c: 'var(--etudier)' },
            { v: stats?.filtre_ok, l: 'Filtre OK',       c: 'var(--accent)' },
            { v: stats?.scored,    l: 'Scorées par IA',  c: 'var(--go)' },
          ].map(({ v, l, c }) => (
            <div className="stat-card" key={l}>
              <div className="stat-value" style={{ color: c }}>{v ?? 0}</div>
              <div className="stat-label">{l}</div>
            </div>
          ))}
        </div>

        {/* Recommandations IA */}
        <div className="reco-grid">
          {[
            { n: stats?.go,       l: 'GO — À soumettre',     c: 'var(--go)' },
            { n: stats?.a_etudier,l: 'À étudier',             c: 'var(--etudier)' },
            { n: stats?.no_go,    l: 'NO GO — Écartées',     c: 'var(--no-go)' },
          ].map(({ n, l, c }) => (
            <div className="reco-card" key={l}>
              <div className="reco-dot" style={{ background: c }} />
              <div>
                <div className="reco-n" style={{ color: c }}>{n ?? 0}</div>
                <div className="reco-l">{l}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Sources */}
        {stats?.sources && Object.keys(stats.sources).length > 0 && (
          <div className="sources-card">
            <div className="sources-title">Sources actives</div>
            {Object.entries(stats.sources).map(([src, n]) => (
              <div className="source-row" key={src}>
                <div>
                  <span style={{ color: 'var(--text)' }}>{src}</span>
                  <div className="source-bar"
                    style={{ width: `${Math.round((n / total) * 200)}px` }} />
                </div>
                <span style={{ color: 'var(--accent)', fontFamily: 'var(--font-head)',
                  fontWeight: 700, fontSize: 18 }}>{n}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {toast && <div className="toast">{toast}</div>}
    </>
  )
}
