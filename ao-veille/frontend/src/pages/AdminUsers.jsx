// frontend/src/pages/AdminUsers.jsx
import { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi";

const ROLE_LABELS = { admin: "Admin", commercial: "Commercial" };

function Badge({ actif }) {
  return (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 20,
      fontSize: "0.78rem", fontWeight: 600,
      background: actif ? "rgba(46,204,138,0.15)" : "rgba(150,150,150,0.15)",
      color: actif ? "var(--go)" : "var(--text-muted)",
    }}>
      {actif ? "● Actif" : "○ Inactif"}
    </span>
  );
}

function RoleBadge({ role }) {
  const isAdmin = role === "admin";
  return (
    <span style={{
      padding: "2px 10px", borderRadius: 20, fontSize: "0.78rem", fontWeight: 600,
      background: isAdmin ? "rgba(79,142,247,0.15)" : "rgba(240,168,72,0.15)",
      color: isAdmin ? "var(--accent)" : "var(--etudier)",
    }}>
      {ROLE_LABELS[role]}
    </span>
  );
}

function Modal({ title, onClose, children }) {
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div style={{
        background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)",
        width: 460, maxHeight: "85vh", overflowY: "auto", padding: "1.75rem",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.1rem", color: "var(--text)" }}>{title}</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", fontSize: "1.25rem", cursor: "pointer" }}>
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: "1.1rem" }}>
      <label style={{ display: "block", marginBottom: 5, color: "var(--text-muted)", fontSize: "0.83rem" }}>
        {label}
      </label>
      {children}
    </div>
  );
}

function Input({ value, onChange, type = "text", placeholder }) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        width: "100%", padding: "0.6rem 0.85rem",
        background: "var(--bg)", border: "1px solid var(--border)",
        borderRadius: 8, color: "var(--text)", fontSize: "0.92rem",
        outline: "none", boxSizing: "border-box",
      }}
    />
  );
}

function Select({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        width: "100%", padding: "0.6rem 0.85rem",
        background: "var(--bg)", border: "1px solid var(--border)",
        borderRadius: 8, color: "var(--text)", fontSize: "0.92rem",
        outline: "none", boxSizing: "border-box",
      }}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

function Btn({ onClick, children, variant = "primary", disabled = false }) {
  const styles = {
    primary: { background: "var(--accent)",   color: "#fff",            border: "none" },
    danger:  { background: "var(--no-go)",    color: "#fff",            border: "none" },
    ghost:   { background: "transparent",     color: "var(--text-muted)", border: "1px solid var(--border)" },
  };
  const s = styles[variant] || styles.primary;
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "0.55rem 1.1rem",
        border: s.border,
        borderRadius: 8,
        background: disabled ? "var(--border)" : s.background,
        color: s.color,
        cursor: disabled ? "not-allowed" : "pointer",
        fontSize: "0.88rem",
        fontWeight: 600,
      }}
    >
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Modal création
// ---------------------------------------------------------------------------
function CreateUserModal({ onClose, onCreated }) {
  const { post } = useApi();
  const [form, setForm] = useState({ email: "", nom: "", role: "commercial", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleCreate() {
    setError("");
    if (!form.email || !form.nom || !form.password) {
      setError("Tous les champs sont obligatoires");
      return;
    }
    setLoading(true);
    try {
      await post("/api/admin/users", form);
      onCreated();
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title="Nouvel utilisateur" onClose={onClose}>
      <Field label="Nom complet">
        <Input value={form.nom} onChange={(v) => setForm({ ...form, nom: v })} placeholder="Alice Martin" />
      </Field>
      <Field label="Email">
        <Input type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} placeholder="alice@esn.fr" />
      </Field>
      <Field label="Rôle">
        <Select
          value={form.role}
          onChange={(v) => setForm({ ...form, role: v })}
          options={[
            { value: "commercial", label: "Commercial" },
            { value: "admin", label: "Admin" },
          ]}
        />
      </Field>
      <Field label="Mot de passe">
        <Input type="password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} placeholder="••••••••" />
      </Field>
      {error && (
        <div style={{ color: "var(--no-go)", fontSize: "0.85rem", marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn variant="ghost" onClick={onClose}>Annuler</Btn>
        <Btn onClick={handleCreate} disabled={loading}>
          {loading ? "Création..." : "Créer"}
        </Btn>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Modal édition
// ---------------------------------------------------------------------------
function EditUserModal({ user, onClose, onSaved }) {
  const { put, post } = useApi();
  const [form, setForm] = useState({ nom: user.nom, email: user.email, role: user.role });
  const [tmpPw, setTmpPw] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    setError("");
    setLoading(true);
    try {
      await put(`/api/admin/users/${user.id}`, form);
      onSaved();
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleActif() {
    await put(`/api/admin/users/${user.id}`, { actif: !user.actif });
    onSaved();
    onClose();
  }

  async function handleResetPw() {
    const res = await post(`/api/admin/users/${user.id}/reset-password`);
    if (res && res.temporary_password) {
      setTmpPw(res.temporary_password);
    }
  }

  return (
    <Modal title={"Modifier — " + user.nom} onClose={onClose}>
      <Field label="Nom complet">
        <Input value={form.nom} onChange={(v) => setForm({ ...form, nom: v })} />
      </Field>
      <Field label="Email">
        <Input type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
      </Field>
      <Field label="Rôle">
        <Select
          value={form.role}
          onChange={(v) => setForm({ ...form, role: v })}
          options={[
            { value: "commercial", label: "Commercial" },
            { value: "admin", label: "Admin" },
          ]}
        />
      </Field>
      {error && (
        <div style={{ color: "var(--no-go)", fontSize: "0.85rem", marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginBottom: "1rem" }}>
        <Btn variant="ghost" onClick={onClose}>Annuler</Btn>
        <Btn onClick={handleSave} disabled={loading}>
          {loading ? "Sauvegarde..." : "Sauvegarder"}
        </Btn>
      </div>

      <div style={{ borderTop: "1px solid var(--border)", paddingTop: "1rem", display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Btn variant="ghost" onClick={handleResetPw}>🔑 Réinitialiser le mot de passe</Btn>
        <Btn variant={user.actif ? "danger" : "ghost"} onClick={handleToggleActif}>
          {user.actif ? "Désactiver le compte" : "Réactiver le compte"}
        </Btn>
      </div>

      {tmpPw && (
        <div style={{
          marginTop: "1rem", padding: "0.75rem",
          background: "rgba(79,142,247,0.1)", border: "1px solid var(--accent)", borderRadius: 8,
        }}>
          <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: 4 }}>
            Mot de passe temporaire — à communiquer à l'utilisateur :
          </div>
          <code style={{ color: "var(--accent)", fontSize: "1rem", fontWeight: 700 }}>
            {tmpPw}
          </code>
        </div>
      )}
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Ligne de tableau
// ---------------------------------------------------------------------------
function UserRow({ u, onEdit }) {
  const lastLogin = u.last_login
    ? new Date(u.last_login).toLocaleDateString("fr-FR", {
        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
      })
    : "Jamais";

  return (
    <tr style={{ borderTop: "1px solid var(--border)" }}>
      <td style={{ padding: "0.9rem 1rem", color: "var(--text)", fontWeight: 500 }}>
        {u.nom}
      </td>
      <td style={{ padding: "0.9rem 1rem", color: "var(--text-muted)", fontSize: "0.9rem" }}>
        {u.email}
      </td>
      <td style={{ padding: "0.9rem 1rem" }}>
        <RoleBadge role={u.role} />
      </td>
      <td style={{ padding: "0.9rem 1rem" }}>
        <Badge actif={u.actif} />
      </td>
      <td style={{ padding: "0.9rem 1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
        {lastLogin}
      </td>
      <td style={{ padding: "0.9rem 1rem" }}>
        <button
          onClick={() => onEdit(u)}
          style={{
            background: "none", border: "1px solid var(--border)", borderRadius: 6,
            padding: "4px 12px", color: "var(--text-muted)", cursor: "pointer", fontSize: "0.85rem",
          }}
        >
          ⚙ Modifier
        </button>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Page principale
// ---------------------------------------------------------------------------
export default function AdminUsers() {
  const { get } = useApi();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editUser, setEditUser] = useState(null);

  async function loadUsers() {
    setLoading(true);
    try {
      const data = await get("/api/admin/users");
      if (data) setUsers(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadUsers(); }, []);

  const headers = ["Nom", "Email", "Rôle", "Statut", "Dernière connexion", ""];

  return (
    <div style={{ padding: "2rem", maxWidth: 900 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h1 style={{ margin: 0, fontSize: "1.4rem", color: "var(--text)" }}>👥 Utilisateurs</h1>
        <Btn onClick={() => setShowCreate(true)}>+ Nouvel utilisateur</Btn>
      </div>

      {loading ? (
        <div style={{ color: "var(--text-muted)" }}>Chargement...</div>
      ) : (
        <div style={{
          background: "var(--surface)", borderRadius: 10,
          border: "1px solid var(--border)", overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--bg)", fontSize: "0.82rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                {headers.map((h) => (
                  <th key={h} style={{ padding: "0.75rem 1rem", textAlign: "left", fontWeight: 600 }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <UserRow key={u.id} u={u} onEdit={setEditUser} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateUserModal onClose={() => setShowCreate(false)} onCreated={loadUsers} />
      )}
      {editUser && (
        <EditUserModal user={editUser} onClose={() => setEditUser(null)} onSaved={loadUsers} />
      )}
    </div>
  );
}