// src/pages/Logs.jsx
import React, { useState, useEffect, useCallback } from 'react'
import { useApi } from '../hooks/useApi'

const css = `
  .logs { padding:32px; }
  .logs-title { font-size:32px; margin-bottom:24px; }
  .log-list { display:flex; flex-direction:column; gap:6px; }
  .log-item { display:grid; grid-template-columns:160px 120px 1fr;
    gap:12px; padding:10px 14px; background:var(--bg2);
    border:1px solid var(--border); border-radius:var(--r);
    align-items:start; font-size:12px; }
  .log-time  { color:var(--text3); font-variant-numeric:tabular-nums; }
  .log-event { color:var(--accent); font-weight:500; }
  .log-event.error { color:var(--no-go); }
  .log-detail { color:var(--text2); word-break:break-all; }
  .empty { text-align:center; padding:64px 0; color:var(--text3); }
`

function eventColor(e) {
  if (e?.includes('error') || e?.includes('fail')) return 'log-event error'
  return 'log-event'
}

export default function Logs() {
  const { get } = useApi()
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  const loadLogs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await get('/api/logs?limit=100')
      if (data) setLogs(data)
    } finally {
      setLoading(false)
    }
  }, [get])

  useEffect(() => { loadLogs() }, [loadLogs])

  return (
    <>
      <style>{css}</style>
      <div className="logs">
        <h2 className="logs-title">Activité</h2>
        {loading ? (
          <div className="empty">Chargement...</div>
        ) : !logs?.length ? (
          <div className="empty">Aucun log — lancez un premier scraping depuis le tableau de bord.</div>
        ) : (
          <div className="log-list">
            {logs.map(l => (
              <div className="log-item" key={l.id}>
                <span className="log-time">{l.created_at?.replace('T',' ').slice(0,19)}</span>
                <span className={eventColor(l.event)}>[{l.source}] {l.event}</span>
                <span className="log-detail">{l.detail}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}