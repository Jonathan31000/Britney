// frontend/src/hooks/useAuth.js
import { createContext, useContext, useState, useEffect, useCallback } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);       // { id, nom, email, role }
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true); // vrai pendant la vérification initiale

  // Restaurer la session depuis localStorage au démarrage
  useEffect(() => {
    const stored = localStorage.getItem("ao_token");
    const storedUser = localStorage.getItem("ao_user");
    if (stored && storedUser) {
      try {
        setToken(stored);
        setUser(JSON.parse(storedUser));
      } catch (_) {
        localStorage.removeItem("ao_token");
        localStorage.removeItem("ao_user");
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Erreur de connexion");
    }
    const data = await res.json();
    const userData = {
      id: data.user_id,
      nom: data.nom,
      role: data.role,
    };
    setToken(data.access_token);
    setUser(userData);
    localStorage.setItem("ao_token", data.access_token);
    localStorage.setItem("ao_user", JSON.stringify(userData));
    return userData;
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (_) {}
    setToken(null);
    setUser(null);
    localStorage.removeItem("ao_token");
    localStorage.removeItem("ao_user");
  }, [token]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans AuthProvider");
  return ctx;
}