// src/App.jsx
import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Offres from './pages/Offres'
import OffreDetail from './pages/OffreDetail'
import Logs from './pages/Logs'

const css = `
  .layout { display:flex; min-height:100vh; }
  .main   { flex:1; overflow-y:auto; }
`

export default function App() {
  return (
    <BrowserRouter>
      <style>{css}</style>
      <div className="layout">
        <Sidebar />
        <main className="main">
          <Routes>
            <Route path="/"           element={<Dashboard />} />
            <Route path="/offres"     element={<Offres />} />
            <Route path="/offres/:id" element={<OffreDetail />} />
            <Route path="/logs"       element={<Logs />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
