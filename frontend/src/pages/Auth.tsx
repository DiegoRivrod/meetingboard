import { useState } from 'react'
import { supabase } from '../lib/supabase'
import toast from 'react-hot-toast'

export default function Auth() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    // DEV: bypass — cualquier credencial ingresa
    await new Promise(r => setTimeout(r, 600))
    localStorage.setItem('dev_auth', '1')
    toast.success('Bienvenido a MeetingBoard')
    window.location.reload()
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-accent rounded-xl flex items-center justify-center
                          text-white font-bold text-xl mx-auto mb-3 shadow-glow">
            M
          </div>
          <h1 className="text-xl font-semibold text-white">MeetingBoard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Inteligencia de reuniones y control de compromisos
          </p>
        </div>

        {/* Form */}
        <div className="card p-6 space-y-4">
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block font-medium uppercase tracking-wide">
                Correo electrónico
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="usuario@empresa.com"
                required
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block font-medium uppercase tracking-wide">
                Contraseña
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="••••••••"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>
        </div>

        <p className="text-xs text-slate-600 text-center mt-4">
          MeetingBoard v0.1.0 — Fase 0
        </p>
      </div>
    </div>
  )
}
