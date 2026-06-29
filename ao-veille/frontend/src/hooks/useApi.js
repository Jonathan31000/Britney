// frontend/src/hooks/useApi.js
import { useCallback } from "react";
import { useAuth } from "./useAuth";

export function useApi() {
  const { token, logout } = useAuth();

  const request = useCallback(
    async (path, options = {}) => {
      const headers = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      };

      const res = await fetch(path, { ...options, headers });

      if (res.status === 401) {
        logout();
        return null;
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Erreur ${res.status}`);
      }

      if (res.status === 204) return null;

      return res.json();
    },
    [token, logout]
  );

  const get = useCallback((path) => request(path), [request]);

  const post = useCallback(
    (path, body) =>
      request(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
    [request]
  );

  const put = useCallback(
    (path, body) =>
      request(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
    [request]
  );

  const del = useCallback(
    (path) => request(path, { method: "DELETE" }),
    [request]
  );

  const downloadCsv = useCallback(async () => {
    const res = await fetch("/api/export/csv", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "offres.csv";
    a.click();
    URL.revokeObjectURL(url);
  }, [token]);

  return { request, get, post, put, del, downloadCsv };
}