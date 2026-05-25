// src/components/ScoreBadge.jsx
import React from 'react'

const styles = {
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '3px 10px',
    borderRadius: 99,
    fontFamily: 'var(--font-head)',
    fontWeight: 700,
    fontSize: 13,
    letterSpacing: '-0.01em',
  }
}

function scoreColor(score) {
  if (score === null || score === undefined) return { bg: '#1c2030', color: '#545e72' }
  if (score >= 7.5) return { bg: 'rgba(46,204,138,.15)', color: '#2ecc8a' }
  if (score >= 5)   return { bg: 'rgba(240,168,72,.15)',  color: '#f0a848' }
  return              { bg: 'rgba(224,92,106,.15)',  color: '#e05c6a' }
}

export function ScoreBadge({ score }) {
  const { bg, color } = scoreColor(score)
  return (
    <span style={{ ...styles.badge, background: bg, color }}>
      {score !== null && score !== undefined ? score.toFixed(1) : '—'} /10
    </span>
  )
}

export function RecoBadge({ reco }) {
  const map = {
    go:        { label: '✓ GO',       bg: 'rgba(46,204,138,.15)', color: '#2ecc8a' },
    no_go:     { label: '✗ NO GO',    bg: 'rgba(224,92,106,.15)', color: '#e05c6a' },
    a_etudier: { label: '~ À étudier',bg: 'rgba(240,168,72,.15)', color: '#f0a848' },
  }
  const { label, bg, color } = map[reco] || { label: '?', bg: '#1c2030', color: '#545e72' }
  return <span style={{ ...styles.badge, background: bg, color }}>{label}</span>
}
