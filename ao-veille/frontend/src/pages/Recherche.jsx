// src/pages/Recherche.jsx
import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { ScoreBadge } from "../components/ScoreBadge";

const RECOS = [
  { value: "go", label: "GO", color: "#2ecc8a" },
  { value: "a_etudier", label: "À étudier", color: "#f0a848" },
  { value: "no_go", label: "NO GO", color: "#e05c6a" },
];

const ACTIONS = ["ignoré", "répondu", "gagné", "perdu"];

const ACTION_COLORS = {
  "ignoré": "#666",
  "répondu": "#4f8ef7",
  "gagné": "#2ecc8a",
  "perdu": "#e05c6a",
};

export default function Recherche() {
  const { request } = useApi();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Lire les filtres depuis l'URL
  const [q, setQ]               = useState(searchParams.get('q') || "");
  const [inTitre, setInTitre]   = useState(searchParams.get('inTitre') !== 'false');
  const [inDesc, setInDesc]     = useState(searchParams.get('inDesc') !== 'false');
  const [inAcheteur, setInAcheteur] = useState(searchParams.get('inAcheteur') === 'true');
  const [scoreMin, setScoreMin] = useState(searchParams.get('scoreMin') || "");
  const [scoreMax, setScoreMax] = useState(searchParams.get('scoreMax') || "");
  const [recos, setRecos]       = useState(searchParams.get('recos') ? searchParams.get('recos').split(',') : []);
  const [sources, setSources]   = useState(searchParams.get('sources') ? searchParams.get('sources').split(',') : []);
  const [dateDu, setDateDu]     = useState(searchParams.get('dateDu') || "");
  const [dateAu, setDateAu]     = useState(searchParams.get('dateAu') || "");
  const [budgetMin, setBudgetMin] = useState(searchParams.get('budgetMin') || "");
  const [budgetMax, setBudgetMax] = useState(searchParams.get('budgetMax') || "");
  const [tags, setTags]         = useState(searchParams.get('tags') ? searchParams.get('tags').split(',') : []);
  const [tagInput, setTagInput] = useState("");
  const [nonVues, setNonVues]   = useState(searchParams.get('nonVues') === 'true');
  const [results, setResults]   = useState(null);
  const [loading, setLoading]   = useState(false);
  const [hasSearched, setHasSearched] = useState(searchParams.get('searched') === 'true');

  const [savedSearches, setSavedSearches] = useState([]);
  const [saveName, setSaveName]           = useState("");
  const [showSave, setShowSave]           = useState(false);
  const [notify, setNotify]               = useState(false);
  const [knownTags, setKnownTags]         = useState([]);
  const [sourcesAll, setSourcesAll]       = useState([]);

  useEffect(() => { loadMeta(); }, []);

  // Si on revient sur la page avec searched=true, relancer la recherche auto
  useEffect(() => {
    if (hasSearched) handleSearch(true);
  }, []);

  async function loadMeta() {
    const [srcs, saved, knownT] = await Promise.all([
      request("/api/sources"),
      request("/api/search/saved"),
      request("/api/tags"),
    ]);
    if (srcs) setSourcesAll(srcs.map(s => s.name));
    if (saved) setSavedSearches(saved);
    if (knownT) setKnownTags(knownT);
  }

  function buildFilters() {
    return {
      q, in_titre: inTitre, in_description: inDesc, in_acheteur: inAcheteur,
      score_min: scoreMin !== "" ? parseFloat(scoreMin) : undefined,
      score_max: scoreMax !== "" ? parseFloat(scoreMax) : undefined,
      recommandation: recos.length ? recos : undefined,
      source: sources.length ? sources : undefined,
      date_limite_from: dateDu || undefined,
      date_limite_to: dateAu || undefined,
      budget_min: budgetMin !== "" ? parseFloat(budgetMin) : undefined,
      budget_max: budgetMax !== "" ? parseFloat(budgetMax) : undefined,
      tags: tags.length ? tags : undefined,
      non_vues_seulement: nonVues || undefined,
    };
  }

  // Persister les filtres dans l'URL
  function persistParams() {
    const next = new URLSearchParams();
    if (q)          next.set('q', q);
    if (!inTitre)   next.set('inTitre', 'false');
    if (!inDesc)    next.set('inDesc', 'false');
    if (inAcheteur) next.set('inAcheteur', 'true');
    if (scoreMin)   next.set('scoreMin', scoreMin);
    if (scoreMax)   next.set('scoreMax', scoreMax);
    if (recos.length)   next.set('recos', recos.join(','));
    if (sources.length) next.set('sources', sources.join(','));
    if (dateDu)     next.set('dateDu', dateDu);
    if (dateAu)     next.set('dateAu', dateAu);
    if (budgetMin)  next.set('budgetMin', budgetMin);
    if (budgetMax)  next.set('budgetMax', budgetMax);
    if (tags.length) next.set('tags', tags.join(','));
    if (nonVues)    next.set('nonVues', 'true');
    next.set('searched', 'true');
    setSearchParams(next, { replace: true });
  }

  async function handleSearch(silent = false) {
    if (!silent) persistParams();
    setLoading(true);
    setHasSearched(true);
    const res = await request("/api/search", {
      method: "POST",
      body: JSON.stringify({ ...buildFilters(), limit: 100 }),
    });
    if (res) setResults(res);
    setLoading(false);
  }

  async function handleSaveSearch() {
    if (!saveName.trim()) return;
    await request("/api/search/saved", {
      method: "POST",
      body: JSON.stringify({ name: saveName, filters: buildFilters(), notify }),
    });
    setSaveName(""); setShowSave(false);
    loadMeta();
  }

  async function handleDeleteSaved(id) {
    await request(`/api/search/saved/${id}`, { method: "DELETE" });
    loadMeta();
  }

  function loadSaved(s) {
    const f = s.filters;
    setQ(f.q || "");
    setInTitre(f.in_titre ?? true);
    setInDesc(f.in_description ?? true);
    setInAcheteur(f.in_acheteur ?? false);
    setScoreMin(f.score_min ?? "");
    setScoreMax(f.score_max ?? "");
    setRecos(f.recommandation || []);
    setSources(f.source || []);
    setDateDu(f.date_limite_from || "");
    setDateAu(f.date_limite_to || "");
    setBudgetMin(f.budget_min ?? "");
    setBudgetMax(f.budget_max ?? "");
    setTags(f.tags || []);
    setNonVues(f.non_vues_seulement || false);
  }

  function toggleReco(v) {
    setRecos(r => r.includes(v) ? r.filter(x => x !== v) : [...r, v]);
  }

  function toggleSource(v) {
    setSources(s => s.includes(v) ? s.filter(x => x !== v) : [...s, v]);
  }

  function addTag(label) {
    const t = label.trim().toLowerCase();
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagInput("");
  }

  function removeTag(t) {
    setTags(tags.filter(x => x !== t));
  }

  async function handleAction(offreId, action) {
    await request(`/api/offres/${offreId}/action`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    setResults(r => r.map(o => o.id === offreId ? { ...o, action } : o));
  }

  return (
    <div style={{ padding: "2rem", maxWidth: 1100, display: "flex", gap: "2rem" }}>

      {/* Panneau filtres */}
      <div style={{ width: 300, flexShrink: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Filtres</h2>
          {savedSearches.length > 0 && (
            <select
              onChange={e => {
                const s = savedSearches.find(x => x.id === parseInt(e.target.value));
                if (s) loadSaved(s);
              }}
              style={{ fontSize: "0.8rem", background: "var(--bg)", color: "inherit",
                       border: "1px solid var(--border)", borderRadius: 6, padding: "0.2rem 0.4rem" }}
            >
              <option value="">Mes recherches…</option>
              {savedSearches.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          )}
        </div>

        <Section label="Texte libre">
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            placeholder="java angular…"
            style={inputStyle}
          />
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.4rem", fontSize: "0.8rem" }}>
            <Checkbox label="Titre" checked={inTitre} onChange={setInTitre} />
            <Checkbox label="Description" checked={inDesc} onChange={setInDesc} />
            <Checkbox label="Acheteur" checked={inAcheteur} onChange={setInAcheteur} />
          </div>
        </Section>

        <Section label="Score IA">
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input value={scoreMin} onChange={e => setScoreMin(e.target.value)}
              placeholder="0" style={{ ...inputStyle, width: 60 }} />
            <span style={{ color: "var(--muted)" }}>à</span>
            <input value={scoreMax} onChange={e => setScoreMax(e.target.value)}
              placeholder="10" style={{ ...inputStyle, width: 60 }} />
          </div>
        </Section>

        <Section label="Recommandation">
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {RECOS.map(r => (
              <button key={r.value} onClick={() => toggleReco(r.value)} style={{
                padding: "0.25rem 0.7rem", borderRadius: 20, border: "1px solid",
                borderColor: recos.includes(r.value) ? r.color : "var(--border)",
                background: recos.includes(r.value) ? r.color + "22" : "transparent",
                color: recos.includes(r.value) ? r.color : "var(--muted)",
                cursor: "pointer", fontSize: "0.82rem", fontWeight: 600
              }}>
                {r.label}
              </button>
            ))}
          </div>
        </Section>

        {sourcesAll.length > 1 && (
          <Section label="Source">
            <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
              {sourcesAll.map(s => (
                <button key={s} onClick={() => toggleSource(s)} style={{
                  padding: "0.2rem 0.6rem", borderRadius: 20, border: "1px solid",
                  borderColor: sources.includes(s) ? "#4f8ef7" : "var(--border)",
                  background: sources.includes(s) ? "#4f8ef722" : "transparent",
                  color: sources.includes(s) ? "#4f8ef7" : "var(--muted)",
                  cursor: "pointer", fontSize: "0.78rem"
                }}>
                  {s}
                </button>
              ))}
            </div>
          </Section>
        )}

        <Section label="Date limite">
          <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
            <input type="date" value={dateDu} onChange={e => setDateDu(e.target.value)}
              style={inputStyle} />
            <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>→</span>
            <input type="date" value={dateAu} onChange={e => setDateAu(e.target.value)}
              style={inputStyle} />
          </div>
        </Section>

        <Section label="Budget (TJM €)">
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input value={budgetMin} onChange={e => setBudgetMin(e.target.value)}
              placeholder="min" style={{ ...inputStyle, width: 70 }} />
            <span style={{ color: "var(--muted)" }}>—</span>
            <input value={budgetMax} onChange={e => setBudgetMax(e.target.value)}
              placeholder="max" style={{ ...inputStyle, width: 70 }} />
            <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>€</span>
          </div>
        </Section>

        <Section label="Mes tags">
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginBottom: "0.4rem" }}>
            {tags.map(t => (
              <span key={t} style={{
                background: "#4f8ef722", color: "#4f8ef7",
                borderRadius: 20, padding: "0.2rem 0.6rem",
                fontSize: "0.78rem", display: "flex", alignItems: "center", gap: 4
              }}>
                {t}
                <button onClick={() => removeTag(t)}
                  style={{ background: "none", border: "none", color: "#4f8ef7",
                           cursor: "pointer", padding: 0, lineHeight: 1 }}>×</button>
              </span>
            ))}
          </div>
          <div style={{ display: "flex", gap: "0.4rem" }}>
            <input
              value={tagInput}
              onChange={e => setTagInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") addTag(tagInput); }}
              placeholder="Ajouter un tag…"
              list="known-tags"
              style={{ ...inputStyle, flex: 1 }}
            />
            <datalist id="known-tags">
              {knownTags.map(t => <option key={t.label} value={t.label} />)}
            </datalist>
            <button onClick={() => addTag(tagInput)}
              style={{ background: "var(--bg)", border: "1px solid var(--border)",
                       borderRadius: 6, padding: "0 0.6rem", cursor: "pointer" }}>
              +
            </button>
          </div>
        </Section>

        <Section label="">
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem",
                          cursor: "pointer", fontSize: "0.9rem" }}>
            <input type="checkbox" checked={nonVues} onChange={e => setNonVues(e.target.checked)} />
            Offres non vues uniquement
          </label>
        </Section>

        <button
          onClick={() => handleSearch()}
          disabled={loading}
          style={{
            width: "100%", background: "#4f8ef7", color: "#fff",
            border: "none", padding: "0.7rem", borderRadius: 8,
            cursor: "pointer", fontWeight: 700, fontSize: "0.95rem",
            marginBottom: "0.75rem"
          }}
        >
          {loading ? "Recherche…" : "Rechercher"}
        </button>

        {!showSave ? (
          <button onClick={() => setShowSave(true)} style={{
            width: "100%", background: "transparent", color: "var(--muted)",
            border: "1px solid var(--border)", padding: "0.5rem",
            borderRadius: 8, cursor: "pointer", fontSize: "0.85rem"
          }}>
            💾 Sauvegarder cette recherche
          </button>
        ) : (
          <div style={{ background: "var(--surface)", borderRadius: 8, padding: "0.75rem",
                        border: "1px solid var(--border)" }}>
            <input
              value={saveName}
              onChange={e => setSaveName(e.target.value)}
              placeholder="Nom de la recherche…"
              style={{ ...inputStyle, width: "100%", marginBottom: "0.4rem" }}
            />
            <label style={{ display: "flex", alignItems: "center", gap: "0.4rem",
                            fontSize: "0.82rem", marginBottom: "0.5rem" }}>
              <input type="checkbox" checked={notify} onChange={e => setNotify(e.target.checked)} />
              Me notifier sur les nouvelles offres
            </label>
            <div style={{ display: "flex", gap: "0.4rem" }}>
              <button onClick={handleSaveSearch} style={{
                flex: 1, background: "#4f8ef7", color: "#fff", border: "none",
                borderRadius: 6, padding: "0.4rem", cursor: "pointer", fontSize: "0.85rem"
              }}>
                Sauvegarder
              </button>
              <button onClick={() => setShowSave(false)} style={{
                background: "transparent", border: "1px solid var(--border)",
                borderRadius: 6, padding: "0.4rem 0.6rem", cursor: "pointer", fontSize: "0.85rem"
              }}>
                ✕
              </button>
            </div>
          </div>
        )}

        {savedSearches.length > 0 && (
          <div style={{ marginTop: "1rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: "0.4rem" }}>
              Recherches sauvegardées
            </div>
            {savedSearches.map(s => (
              <div key={s.id} style={{ display: "flex", alignItems: "center", gap: "0.4rem",
                                       marginBottom: "0.3rem" }}>
                <button onClick={() => loadSaved(s)} style={{
                  flex: 1, textAlign: "left", background: "transparent",
                  border: "1px solid var(--border)", borderRadius: 6,
                  padding: "0.3rem 0.6rem", cursor: "pointer", fontSize: "0.82rem",
                  color: "inherit"
                }}>
                  {s.name}
                  {s.notify && <span style={{ marginLeft: 4, color: "#4f8ef7" }}>🔔</span>}
                </button>
                <button onClick={() => handleDeleteSaved(s.id)} style={{
                  background: "transparent", border: "none", color: "#e05c6a",
                  cursor: "pointer", fontSize: "0.9rem", padding: "0 0.2rem"
                }}>
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Résultats */}
      <div style={{ flex: 1 }}>
        {results === null && !hasSearched && (
          <div style={{ color: "var(--muted)", paddingTop: "3rem", textAlign: "center" }}>
            Définissez vos critères et lancez la recherche.
          </div>
        )}
        {loading && (
          <div style={{ color: "var(--muted)", paddingTop: "3rem", textAlign: "center" }}>
            Recherche en cours…
          </div>
        )}
        {results !== null && !loading && (
          <>
            <div style={{ marginBottom: "1rem", color: "var(--muted)", fontSize: "0.9rem" }}>
              {results.length} offre(s) trouvée(s)
            </div>
            {results.length === 0 && (
              <div style={{ color: "var(--muted)" }}>Aucun résultat pour ces critères.</div>
            )}
            {results.map(o => (
              <OffreCard
                key={o.id}
                offre={o}
                onNavigate={() => navigate(`/offres/${o.id}`, { state: { from: `/recherche?${searchParams.toString()}` } })}
                onAction={handleAction}
                request={request}
                knownTags={knownTags}
                onTagsChange={loadMeta}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
}

function OffreCard({ offre: o, onNavigate, onAction, request, knownTags, onTagsChange }) {
  const [tagInput, setTagInput] = useState("");
  const [localTags, setLocalTags] = useState(o.tags || []);

  async function handleAddTag(label) {
    const t = label.trim().toLowerCase();
    if (!t) return;
    await request(`/api/offres/${o.id}/tags`, {
      method: "POST",
      body: JSON.stringify({ label: t }),
    });
    setLocalTags(prev => [...prev.filter(x => x.label !== t), { label: t, color: "#4f8ef7" }]);
    setTagInput("");
    onTagsChange();
  }

  async function handleRemoveTag(label) {
    await request(`/api/offres/${o.id}/tags/${encodeURIComponent(label)}`, { method: "DELETE" });
    setLocalTags(prev => prev.filter(x => x.label !== label));
    onTagsChange();
  }

  const recoColor = o.recommandation === "go" ? "#2ecc8a"
                  : o.recommandation === "no_go" ? "#e05c6a" : "#f0a848";

  return (
    <div style={{
      background: "var(--surface)", borderRadius: 10, padding: "1rem 1.25rem",
      border: "1px solid var(--border)", marginBottom: "0.75rem",
      borderLeft: `3px solid ${recoColor}`
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ flex: 1, cursor: "pointer" }} onClick={onNavigate}>
          <div style={{ fontWeight: 600, marginBottom: "0.2rem" }}>{o.titre}</div>
          <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>{o.acheteur}</div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexShrink: 0 }}>
          {o.score != null && <ScoreBadge score={o.score} />}
          {!o.vue && (
            <span style={{
              background: "#4f8ef722", color: "#4f8ef7",
              borderRadius: 20, padding: "0.1rem 0.5rem", fontSize: "0.72rem", fontWeight: 700
            }}>
              NEW
            </span>
          )}
        </div>
      </div>

      {o.resume && (
        <div style={{ fontSize: "0.82rem", color: "var(--muted)", margin: "0.5rem 0",
                      fontStyle: "italic" }}>
          {o.resume}
        </div>
      )}

      <div style={{ display: "flex", gap: "1rem", fontSize: "0.8rem", color: "var(--muted)",
                    flexWrap: "wrap", margin: "0.4rem 0" }}>
        {o.budget_max && <span>💰 {o.budget_max}€</span>}
        {o.date_limite && <span>📅 {o.date_limite}</span>}
        <span>📍 {o.source}</span>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                    marginTop: "0.6rem", flexWrap: "wrap", gap: "0.5rem" }}>
        <div style={{ display: "flex", gap: "0.3rem", alignItems: "center", flexWrap: "wrap" }}>
          {localTags.map(t => (
            <span key={t.label} style={{
              background: (t.color || "#4f8ef7") + "22", color: t.color || "#4f8ef7",
              borderRadius: 20, padding: "0.15rem 0.5rem", fontSize: "0.75rem",
              display: "flex", alignItems: "center", gap: 3
            }}>
              {t.label}
              <button onClick={() => handleRemoveTag(t.label)}
                style={{ background: "none", border: "none", color: "inherit",
                         cursor: "pointer", padding: 0, fontSize: "0.8rem", lineHeight: 1 }}>
                ×
              </button>
            </span>
          ))}
          <div style={{ display: "flex", gap: "0.2rem" }}>
            <input
              value={tagInput}
              onChange={e => setTagInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") handleAddTag(tagInput); }}
              placeholder="+ tag"
              list="known-tags-card"
              style={{
                width: 80, fontSize: "0.75rem", background: "var(--bg)",
                border: "1px solid var(--border)", borderRadius: 20,
                padding: "0.1rem 0.5rem", color: "inherit"
              }}
            />
            <datalist id="known-tags-card">
              {knownTags.map(t => <option key={t.label} value={t.label} />)}
            </datalist>
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.3rem" }}>
          {ACTIONS.map(a => (
            <button key={a} onClick={() => onAction(o.id, o.action === a ? null : a)}
              style={{
                padding: "0.2rem 0.5rem", borderRadius: 20, border: "1px solid",
                borderColor: o.action === a ? ACTION_COLORS[a] : "var(--border)",
                background: o.action === a ? ACTION_COLORS[a] + "22" : "transparent",
                color: o.action === a ? ACTION_COLORS[a] : "var(--muted)",
                cursor: "pointer", fontSize: "0.72rem", fontWeight: o.action === a ? 700 : 400
              }}>
              {a}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Section({ label, children }) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      {label && (
        <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--muted)",
                      textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.4rem" }}>
          {label}
        </div>
      )}
      {children}
    </div>
  );
}

function Checkbox({ label, checked, onChange }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 4,
                    cursor: "pointer", fontSize: "0.8rem" }}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      {label}
    </label>
  );
}

const inputStyle = {
  background: "var(--bg)", border: "1px solid var(--border)",
  borderRadius: 6, padding: "0.4rem 0.6rem", color: "inherit",
  fontSize: "0.85rem", width: "100%"
};