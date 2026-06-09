// frontend/src/pages/Login.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(email, password);
      navigate(user.role === "admin" ? "/admin/utilisateurs" : "/");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <div style={{ width: 380, padding: "2.5rem", background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", boxShadow: "0 8px 32px rgba(0,0,0,0.3)" }}>
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text)" }}>AO Veille</div>
          <div style={{ color: "var(--text-muted)", marginTop: 4, fontSize: "0.9rem" }}>Connectez-vous à votre espace</div>
        </div>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1.25rem" }}>
            <label style={{ display: "block", marginBottom: 6, color: "var(--text-muted)", fontSize: "0.85rem" }}>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="vous@esn.fr" required
              style={{ width: "100%", padding: "0.65rem 0.9rem", background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)", fontSize: "0.95rem", outline: "none", boxSizing: "border-box" }} />
          </div>
          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", marginBottom: 6, color: "var(--text-muted)", fontSize: "0.85rem" }}>Mot de passe</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required
              style={{ width: "100%", padding: "0.65rem 0.9rem", background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)", fontSize: "0.95rem", outline: "none", boxSizing: "border-box" }} />
          </div>
          {error && (
            <div style={{ marginBottom: "1rem", padding: "0.65rem 0.9rem", background: "rgba(224,92,106,0.12)", border: "1px solid var(--no-go)", borderRadius: 8, color: "var(--no-go)", fontSize: "0.88rem" }}>{error}</div>
          )}
          <button type="submit" disabled={loading}
            style={{ width: "100%", padding: "0.75rem", background: loading ? "var(--border)" : "var(--accent)", color: "#fff", border: "none", borderRadius: 8, fontSize: "0.95rem", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer" }}>
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}