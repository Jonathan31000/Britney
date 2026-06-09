// src/hooks/useApi.js
import { useState, useEffect, useCallback } from 'react'

const BASE = '/api'

export function useFetch(url, deps = []) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  const load = useCallback(async () => {
    if (!url) return
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(BASE + url)
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setData(await r.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [url])

  useEffect(() => { load() }, [load, ...deps])

  return { data, loading, error, refresh: load }
}

export async function triggerAction(path, params = {}) {
  const qs = new URLSearchParams(params).toString()
  const url = qs ? `${BASE}${path}?${qs}` : `${BASE}${path}`
  const r = await fetch(url, { method: 'POST' })
  return r.json()
}

export function buildOffreUrl(params) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== '' && v != null) q.set(k, v) })
  return `/offres?${q.toString()}`
}
