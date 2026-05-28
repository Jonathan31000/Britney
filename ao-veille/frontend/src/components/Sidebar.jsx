// src/components/Sidebar.jsx
import React from 'react'
import { NavLink } from 'react-router-dom'

const nav = [
  { to: '/',           label: 'Tableau de bord',  icon: '▦' },
  { to: '/offres',     label: "Appels d'offres",  icon: '◈' },
  { to: '/logs',       label: 'Activité',          icon: '≡' },
  { to: '/parametres', label: 'Paramètres',        icon: '⚙' },
]

const css = `
  .sidebar { display:flex; flex-direction:column; width:220px; min-height:100vh;
    background:var(--bg2); border-right:1px solid var(--border); padding:0; flex-shrink:0; }
  .sidebar-logo { padding:28px 24px 20px; border-bottom:1px solid var(--border); }
  .sidebar-logo h1 { font-size:22px; color:var(--text); line-height:1; }
  .sidebar-logo p  { font-size:11px; color:var(--text3); margin-top:4px; font-family:var(--font-mono); }
  .sidebar-nav { padding:16px 0; flex:1; }
  .sidebar-link { display:flex; align-items:center; gap:12px; padding:10px 24px;
    color:var(--text2); font-size:13px; transition:all .15s; text-decoration:none; }
  .sidebar-link:hover { color:var(--text); background:var(--bg3); }
  .sidebar-link.active { color:var(--accent); background:rgba(79,142,247,.08);
    border-right:2px solid var(--accent); }
  .sidebar-icon { font-size:16px; width:20px; text-align:center; }
  .sidebar-footer { padding:16px 24px; border-top:1px solid var(--border);
    font-size:11px; color:var(--text3); }
`

export default function Sidebar() {
  return (
    <>
      <style>{css}</style>
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>AO Veille</h1>
          <p>Appels d'offres · IA</p>
        </div>
        <nav className="sidebar-nav">
          {nav.map(n => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <span className="sidebar-icon">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">v2.0 · piter.at</div>
      </aside>
    </>
  )
}