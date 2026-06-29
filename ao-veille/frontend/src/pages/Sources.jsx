import { useState, useEffect } from "react";
import { useApi } from "../hooks/useApi";

const COLORS = ["#4f8ef7","#2ecc8a","#f0a848","#e05c6a","#a855f7","#06b6d4","#f97316"];

export default function Sources() {
  const { request } = useApi();
  const [sources, setSources] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [url, setUrl] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [testResults, setTestResults] = useState({});

  useEffect(() => { loadSources(); }, []);

  async function loadSources() {
    const data = await request("/api/sources");
    if (data) setSources(data);
  }

  async function handleAnalyze() {
    if (!url.trim()) return;
    setAnalyzing(true);
    setError("");
    setAnalysisResult(null);
    try {
      const res = await request("/api/sources/analyze", {
        method: "POST",
        body: JSON.stringify({ url: url.trim() }),
      });
      if (res) setAnalysisResult(res);
    } catch (e) {
      setError("Erreur lors de l'analyse : " + e.message);
    }
    setAnalyzing(false);
  }

  async function handleSave() {
    if (!analysisResult) return;
    setSaving(true);
    const cfg = analysisResult.config;
    await request("/api/sources", {
      method: "POST",
      body: JSON.stringify({
        name: cfg.source_name,
        display_name: cfg.display_name,
        base_url: new URL(url).origin,
        list_url: url,
        auth_type: cfg.auth_hint === "login_required" ? "cookies" : "none",
        config_json: cfg,
        confidence: cfg.confidence,
      }),
    });
    setSaving(false);
    setShowAdd(false);
    setAnalysisResult(null);
    setUrl("");
    loadSources();
  }

  async function toggleActive(src) {
    await request(`/api/sources/${src.id}`, {
      method: "PUT",
      body: JSON.stringify({ active: src.active ? 0 : 1 }),
    });
    loadSources();
  }

  async function handleDelete(src) {
    if (!confirm(`Supprimer la source "${src.display_name}" ?`)) return;
    await request(`/api/sources/${src.id}`, { method: "DELETE" });
    loadSources();
  }

  async function handleTest(src) {
    setTestResults(r => ({ ...r, [src.id]: { loading: true } }));
    const res = await request(`/api/sources/${src.id}/test`, { method: "POST" });
    setTestResults(r => ({ ...r, [src.id]: res || { error: "Échec" } }));
  }

  async function handleScrape(src) {
    await request(`/api/trigger/scrape/${src.id}`, { method: "POST" });
    loadSources();
  }

  const confidence = analysisResult?.config?.confidence || 0;
  const confColor = confidence >= 0.7 ? "#2ecc8a" : confidence >= 0.4 ? "#f0a848" : "#e05c6a";

  return (
    <div style={{ padding: "2rem", maxWidth: 900 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h1 style={{ margin: 0, fontSize: "1.5rem" }}>Sources de scraping</h1>
        <button
          onClick={() => setShowAdd(!showAdd)}
          style={{ background: "#4f8ef7", color: "#fff", border: "none",
                   padding: "0.5rem 1.2rem", borderRadius: 8, cursor: "pointer", fontWeight: 600 }}
        >
          {showAdd ? "Annuler" : "+ Ajouter une source"}
        </button>
      </div>

      {/* Liste des sources */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "2rem" }}>
        {sources.map(src => (
          <div key={src.id} style={{
            background: "var(--surface)", borderRadius: 10,
            padding: "1rem 1.25rem", border: "1px solid var(--border)",
            display: "flex", alignItems: "center", gap: "1rem"
          }}>
            <div style={{
              width: 10, height: 10, borderRadius: "50%",
              background: src.active ? "#2ecc8a" : "#666", flexShrink: 0
            }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{src.display_name}</div>
              <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginTop: 2 }}>
                {src.list_url}
                {src.last_scraped && ` · Dernier scraping : ${new Date(src.last_scraped).toLocaleString("fr-FR")}`}
                {src.confidence > 0 && (
                  <span style={{ marginLeft: 8, color: confColor }}>
                    Confiance IA : {Math.round(src.confidence * 100)}%
                  </span>
                )}
              </div>
              {testResults[src.id] && !testResults[src.id].loading && (
                <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "var(--muted)" }}>
                  Aperçu :
                  {testResults[src.id].preview?.map((o, i) => (
                    <div key={i} style={{ marginLeft: 8 }}>• {o.titre} — {o.acheteur}</div>
                  ))}
                  {testResults[src.id].error && <span style={{ color: "#e05c6a" }}>{testResults[src.id].error}</span>}
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}>
              <Btn onClick={() => handleTest(src)} loading={testResults[src.id]?.loading}>
                Tester
              </Btn>
              <Btn onClick={() => handleScrape(src)} variant="primary">
                Scraper
              </Btn>
              <Btn onClick={() => toggleActive(src)}>
                {src.active ? "Désactiver" : "Activer"}
              </Btn>
              {src.name !== "piter.at" && (
                <Btn onClick={() => handleDelete(src)} variant="danger">Suppr.</Btn>
              )}
            </div>
          </div>
        ))}
        {sources.length === 0 && (
          <p style={{ color: "var(--muted)" }}>Aucune source configurée.</p>
        )}
      </div>

      {/* Formulaire ajout */}
      {showAdd && (
        <div style={{
          background: "var(--surface)", borderRadius: 12,
          padding: "1.5rem", border: "1px solid var(--border)"
        }}>
          <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Analyser une nouvelle source</h2>

          <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem" }}>
            <input
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://www.nouvelle-plateforme.fr/offres"
              style={{
                flex: 1, background: "var(--bg)", border: "1px solid var(--border)",
                borderRadius: 8, padding: "0.6rem 1rem", color: "inherit",
                fontSize: "0.95rem"
              }}
            />
            <button
              onClick={handleAnalyze}
              disabled={analyzing || !url.trim()}
              style={{
                background: analyzing ? "#333" : "#4f8ef7", color: "#fff",
                border: "none", padding: "0.6rem 1.2rem", borderRadius: 8,
                cursor: analyzing ? "default" : "pointer", fontWeight: 600,
                minWidth: 160
              }}
            >
              {analyzing ? "Analyse en cours…" : "Analyser avec l'IA"}
            </button>
          </div>

          {error && (
            <div style={{ color: "#e05c6a", marginBottom: "1rem", fontSize: "0.9rem" }}>
              {error}
            </div>
          )}

          {analyzing && (
            <div style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "1rem" }}>
              Playwright charge la page… Claude analyse la structure HTML…
            </div>
          )}

          {analysisResult && (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
                <span style={{ color: "#2ecc8a", fontWeight: 600 }}>✓ Analyse terminée</span>
                <span style={{
                  background: confColor + "22", color: confColor,
                  padding: "0.2rem 0.6rem", borderRadius: 20, fontSize: "0.85rem", fontWeight: 600
                }}>
                  Confiance {Math.round(confidence * 100)}%
                </span>
                {analysisResult.config?.auth_hint === "login_required" && (
                  <span style={{ color: "#f0a848", fontSize: "0.85rem" }}>
                    ⚠ Authentification requise
                  </span>
                )}
              </div>

              {analysisResult.preview?.length > 0 && (
                <div style={{ marginBottom: "1rem" }}>
                  <div style={{ fontWeight: 600, marginBottom: "0.5rem", fontSize: "0.9rem" }}>
                    Aperçu — {analysisResult.preview.length} offre(s) détectée(s)
                  </div>
                  {analysisResult.preview.map((o, i) => (
                    <div key={i} style={{
                      background: "var(--bg)", borderRadius: 8, padding: "0.6rem 1rem",
                      marginBottom: "0.4rem", fontSize: "0.85rem"
                    }}>
                      <strong>{o.titre || "—"}</strong>
                      {o.acheteur && <span style={{ color: "var(--muted)" }}> · {o.acheteur}</span>}
                      {o.budget && <span style={{ color: "#4f8ef7" }}> · {o.budget}</span>}
                    </div>
                  ))}
                </div>
              )}

              {analysisResult.config?.notes && (
                <div style={{ color: "var(--muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                  Note IA : {analysisResult.config.notes}
                </div>
              )}

              <details style={{ marginBottom: "1rem" }}>
                <summary style={{ cursor: "pointer", color: "var(--muted)", fontSize: "0.85rem" }}>
                  Voir la configuration JSON générée
                </summary>
                <pre style={{
                  background: "var(--bg)", borderRadius: 8, padding: "1rem",
                  fontSize: "0.75rem", overflow: "auto", marginTop: "0.5rem"
                }}>
                  {JSON.stringify(analysisResult.config, null, 2)}
                </pre>
              </details>

              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  background: "#2ecc8a", color: "#0d0f12",
                  border: "none", padding: "0.6rem 1.5rem",
                  borderRadius: 8, cursor: "pointer", fontWeight: 700
                }}
              >
                {saving ? "Sauvegarde…" : "Valider et activer cette source"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Btn({ children, onClick, variant, loading, disabled }) {
  const bg = variant === "primary" ? "#4f8ef7"
           : variant === "danger"  ? "#e05c6a44"
           : "var(--bg)";
  const color = variant === "danger" ? "#e05c6a" : "inherit";
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      style={{
        background: bg, color, border: "1px solid var(--border)",
        padding: "0.35rem 0.8rem", borderRadius: 6, cursor: "pointer",
        fontSize: "0.82rem", opacity: loading ? 0.6 : 1
      }}
    >
      {loading ? "…" : children}
    </button>
  );
}