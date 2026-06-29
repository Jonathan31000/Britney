// frontend/src/components/Sidebar.jsx
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const LINKS_COMMERCIAL = [
  { to: "/",           label: "Tableau de bord" },
  { to: "/offres",     label: "Appels d'offres" },
  { to: "/sources",    label: "Sources" },
  { to: "/parametres", label: "Paramètres" },
  { to: "/logs",       label: "Activité" },
];

const LINKS_ADMIN = [
  { to: "/",                   label: "Tableau de bord" },
  { to: "/offres",             label: "Appels d'offres" },
  { to: "/sources",            label: "Sources" },
  { to: "/admin/utilisateurs", label: "Utilisateurs" },
  { to: "/parametres",         label: "Paramètres" },
  { to: "/logs",               label: "Activité" },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const links = user?.role === "admin" ? LINKS_ADMIN : LINKS_COMMERCIAL;

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <aside style={{ width: 220, minHeight: "100vh", background: "var(--surface)", borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", padding: "1.5rem 0", position: "sticky", top: 0 }}>
      <div style={{ padding: "0 1.25rem", marginBottom: "2rem" }}>
        <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text)" }}>AO Veille</div>
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>Veille appels d'offres</div>
      </div>
      <nav style={{ flex: 1 }}>
        {links.map(({ to, label }) => (
          <NavLink key={to} to={to} end={to === "/"}
            style={({ isActive }) => ({
              display: "flex", alignItems: "center", padding: "0.6rem 1.25rem",
              color: isActive ? "var(--accent)" : "var(--text-muted)",
              background: isActive ? "rgba(79,142,247,0.08)" : "transparent",
              textDecoration: "none", fontSize: "0.92rem", fontWeight: isActive ? 600 : 400,
              borderLeft: isActive ? "2px solid var(--accent)" : "2px solid transparent",
            })}>
            {label}
          </NavLink>
        ))}
      </nav>
      <div style={{ padding: "1rem 1.25rem", borderTop: "1px solid var(--border)" }}>
        <div style={{ marginBottom: "0.75rem" }}>
          <div style={{ fontSize: "0.88rem", color: "var(--text)", fontWeight: 500 }}>{user?.nom}</div>
          <div style={{ fontSize: "0.75rem", marginTop: 2, color: user?.role === "admin" ? "var(--accent)" : "var(--etudier)" }}>
            {user?.role === "admin" ? "Administrateur" : "Commercial"}
          </div>
        </div>
        <button onClick={handleLogout}
          style={{ width: "100%", padding: "0.5rem", background: "transparent", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text-muted)", cursor: "pointer", fontSize: "0.85rem" }}>
          Se déconnecter
        </button>
      </div>
    </aside>
  );
}