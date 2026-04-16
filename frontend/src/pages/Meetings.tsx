/**
 * Meetings — Página principal de reuniones.
 *
 * Fase 1: Conectada a la API real.
 * - MeetingsTable carga y filtra las reuniones
 * - UploadModal maneja la creación en 2 pasos (metadatos + archivo)
 * - react-hot-toast provee notificaciones no bloqueantes
 */

import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import MeetingsTable from '../components/meetings/MeetingsTable'
import UploadModal from '../components/meetings/UploadModal'

export default function Meetings() {
  const [showUpload, setShowUpload] = useState(false)

  return (
    <div className="space-y-5">
      {/* Toaster global para esta página */}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#e2e8f0',
            border: '1px solid #334155',
            fontSize: '13px',
          },
          success: { iconTheme: { primary: '#4ade80', secondary: '#1e293b' } },
          error:   { iconTheme: { primary: '#f87171', secondary: '#1e293b' } },
        }}
      />

      {/* Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-white">Reuniones</h1>
        <button
          onClick={() => setShowUpload(true)}
          className="btn-primary text-sm h-9 px-4 flex items-center gap-2"
        >
          <span className="text-base leading-none">+</span>
          Nueva Reunión
        </button>
      </div>

      {/* Tabla conectada a la API */}
      <MeetingsTable />

      {/* Modal de upload */}
      {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}
    </div>
  )
}
