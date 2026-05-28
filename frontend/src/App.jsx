import { useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes, Navigate } from 'react-router-dom'
import IngestPage from './components/IngestPage'
import Dashboard from './components/Dashboard'

const NAV = [
  { to: '/ingest', label: 'Ingest Data', icon: '↑' },
  { to: '/dashboard', label: 'Dashboard', icon: '◈' },
]

function Sidebar() {
  return (
    <aside className="w-56 shrink-0 bg-brand-900 text-white flex flex-col min-h-screen">
      <div className="px-5 py-6 border-b border-brand-800">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🌿</span>
          <div>
            <div className="font-bold text-base leading-tight">Breathe ESG</div>
            <div className="text-xs text-brand-300 leading-tight">Data Platform</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-700 text-white'
                  : 'text-brand-200 hover:bg-brand-800 hover:text-white'
              }`
            }
          >
            <span className="text-base">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-4 border-t border-brand-800 text-xs text-brand-400">
        v0.1.0 · prototype
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/ingest" element={<IngestPage />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
