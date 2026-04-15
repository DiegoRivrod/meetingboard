import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { supabase } from './lib/supabase'
import type { Session } from './lib/supabase'

import Layout     from './components/layout/Layout'
import Auth       from './pages/Auth'
import Dashboard  from './pages/Dashboard'
import Meetings   from './pages/Meetings'
import ActionLog  from './pages/ActionLog'
import People     from './pages/People'
import Settings   from './pages/Settings'

function App() {
  const [session, setSession] = useState<Session | null>(
    localStorage.getItem('dev_auth') ? ({} as Session) : null
  )
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // DEV: si hay bypass activo, no consultar Supabase
    if (localStorage.getItem('dev_auth')) return

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    }).catch(() => {
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center
                          text-white font-bold text-lg mx-auto mb-3 animate-pulse">
            M
          </div>
          <p className="text-xs text-slate-600">Cargando MeetingBoard...</p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1a1a26',
            color: '#e2e8f0',
            border: '1px solid rgba(255,255,255,0.08)',
            fontSize: '13px',
          },
        }}
      />

      <Routes>
        {!session ? (
          <>
            <Route path="/auth" element={<Auth />} />
            <Route path="*"    element={<Navigate to="/auth" replace />} />
          </>
        ) : (
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"  element={<Dashboard />} />
            <Route path="/meetings"   element={<Meetings />} />
            <Route path="/action-log" element={<ActionLog />} />
            <Route path="/people"     element={<People />} />
            <Route path="/settings"   element={<Settings />} />
            <Route path="*"           element={<Navigate to="/dashboard" replace />} />
          </Route>
        )}
      </Routes>
    </BrowserRouter>
  )
}

export default App
