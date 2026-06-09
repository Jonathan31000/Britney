// frontend/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import Sidebar from "./components/Sidebar";

import Login        from "./pages/Login";
import Dashboard    from "./pages/Dashboard";
import Offres       from "./pages/Offres";
import OffreDetail  from "./pages/OffreDetail";
import Parametres   from "./pages/Parametres";
import Logs         from "./pages/Logs";
import AdminUsers   from "./pages/AdminUsers";

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
        <span style={{ color: "var(--text-muted)" }}>Chargement...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

function RequireAdmin({ children }) {
  const { user } = useAuth();
  if (user?.role !== "admin") {
    return <Navigate to="/" replace />;
  }
  return children;
}

function AppLayout({ children }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, overflowY: "auto" }}>
        {children}
      </main>
    </div>
  );
}

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" replace /> : <Login />}
      />

      <Route path="/" element={
        <RequireAuth><AppLayout><Dashboard /></AppLayout></RequireAuth>
      } />

      <Route path="/offres" element={
        <RequireAuth><AppLayout><Offres /></AppLayout></RequireAuth>
      } />

      <Route path="/offres/:id" element={
        <RequireAuth><AppLayout><OffreDetail /></AppLayout></RequireAuth>
      } />

      <Route path="/parametres" element={
        <RequireAuth><AppLayout><Parametres /></AppLayout></RequireAuth>
      } />

      <Route path="/logs" element={
        <RequireAuth><AppLayout><Logs /></AppLayout></RequireAuth>
      } />

      <Route path="/admin/utilisateurs" element={
        <RequireAuth>
          <RequireAdmin>
            <AppLayout><AdminUsers /></AppLayout>
          </RequireAdmin>
        </RequireAuth>
      } />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}