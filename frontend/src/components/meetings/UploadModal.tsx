/**
 * UploadModal — Formulario de 2 pasos para subir una grabación.
 *
 * Paso 1: Metadatos (título, plataforma, fecha)
 * Paso 2: Drag & drop del archivo de audio/video + barra de progreso
 *
 * POR QUÉ 2 pasos: primero creamos el registro en la BD (obtenemos el meeting.id),
 * luego subimos el archivo asociado a ese id. Si el upload falla, el registro
 * queda en estado "uploaded" sin archivo — el usuario puede reintentar.
 */

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import { meetingsApi } from '../../lib/api'
import { useMeetingsStore } from '../../stores/meetingsStore'
import type { MeetingPlatform } from '../../types/meeting'

const PLATFORMS: { value: MeetingPlatform; label: string }[] = [
  { value: 'zoom',        label: 'Zoom' },
  { value: 'teams',       label: 'Microsoft Teams' },
  { value: 'google_meet', label: 'Google Meet' },
  { value: 'manual',      label: 'Grabación manual' },
]

const ACCEPTED_FORMATS = {
  'audio/mpeg': ['.mp3'],
  'audio/mp4': ['.m4a'],
  'audio/wav': ['.wav'],
  'video/mp4': ['.mp4'],
  'video/webm': ['.webm'],
  'video/x-matroska': ['.mkv'],
}

interface Props {
  onClose: () => void
}

type Step = 'metadata' | 'upload'

export default function UploadModal({ onClose }: Props) {
  const { upsertMeeting, fetchMeetings } = useMeetingsStore()

  // Paso 1 — metadatos
  const [step, setStep] = useState<Step>('metadata')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [platform, setPlatform] = useState<MeetingPlatform>('zoom')
  const [meetingDate, setMeetingDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [savingMeta, setSavingMeta] = useState(false)

  // Paso 2 — archivo
  const [meetingId, setMeetingId] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [uploadDone, setUploadDone] = useState(false)

  // ── Paso 1: crear el registro en la BD ──────────────────────────────────────
  async function handleSaveMeta(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return

    setSavingMeta(true)
    try {
      const res = await meetingsApi.create({
        title: title.trim(),
        description: description.trim() || undefined,
        platform,
        meeting_date: meetingDate,
      })
      setMeetingId(res.data.id)
      upsertMeeting(res.data)
      setStep('upload')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Error al crear la reunión')
    } finally {
      setSavingMeta(false)
    }
  }

  // ── Paso 2: upload del archivo ───────────────────────────────────────────────
  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (!meetingId || accepted.length === 0 || uploading) return
      const file = accepted[0]

      setUploading(true)
      setUploadProgress(0)
      try {
        const res = await meetingsApi.upload(meetingId, file, (pct) => {
          setUploadProgress(pct)
        })
        upsertMeeting(res.data.meeting)
        setUploadDone(true)
        toast.success('Archivo subido — iniciando transcripción...')
        await fetchMeetings() // refresca la lista completa
      } catch (err: any) {
        toast.error(err?.response?.data?.detail ?? 'Error al subir el archivo')
        setUploading(false)
      }
    },
    [meetingId, uploading, upsertMeeting, fetchMeetings]
  )

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED_FORMATS,
    maxFiles: 1,
    disabled: uploading || uploadDone,
  })

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={uploadDone ? onClose : undefined}
      />

      <div className="relative z-10 w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-700">
          <div>
            <h2 className="text-base font-semibold text-white">Nueva Reunión</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {step === 'metadata' ? 'Paso 1 de 2 — Información' : 'Paso 2 de 2 — Grabación'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-white transition-colors"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-5">
          {step === 'metadata' ? (
            <form onSubmit={handleSaveMeta} className="space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Título *</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Ej: Revisión Q2 — Equipo Comercial"
                  className="input w-full text-sm"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Descripción</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Contexto opcional..."
                  className="input w-full text-sm resize-none"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Plataforma</label>
                  <select
                    value={platform}
                    onChange={(e) => setPlatform(e.target.value as MeetingPlatform)}
                    className="input w-full text-sm"
                  >
                    {PLATFORMS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Fecha</label>
                  <input
                    type="date"
                    value={meetingDate}
                    onChange={(e) => setMeetingDate(e.target.value)}
                    className="input w-full text-sm"
                    required
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={onClose} className="btn-ghost text-sm px-4 h-9">
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={!title.trim() || savingMeta}
                  className="btn-primary text-sm px-4 h-9 disabled:opacity-50"
                >
                  {savingMeta ? 'Guardando...' : 'Siguiente →'}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              {/* Dropzone */}
              <div
                {...getRootProps()}
                className={[
                  'border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer',
                  isDragReject
                    ? 'border-red-500 bg-red-500/10'
                    : isDragActive
                    ? 'border-indigo-400 bg-indigo-500/10'
                    : uploadDone
                    ? 'border-green-500 bg-green-500/10 cursor-default'
                    : uploading
                    ? 'border-slate-600 bg-slate-800 cursor-not-allowed'
                    : 'border-slate-600 hover:border-indigo-500 hover:bg-slate-800',
                ].join(' ')}
              >
                <input {...getInputProps()} />

                {uploadDone ? (
                  <div>
                    <div className="text-3xl mb-2">✅</div>
                    <p className="text-green-400 font-medium text-sm">Archivo subido correctamente</p>
                    <p className="text-slate-500 text-xs mt-1">
                      La transcripción comenzará en segundos
                    </p>
                  </div>
                ) : uploading ? (
                  <div>
                    <div className="text-3xl mb-3">⬆️</div>
                    <p className="text-slate-300 text-sm font-medium mb-3">
                      Subiendo... {uploadProgress}%
                    </p>
                    {/* Barra de progreso */}
                    <div className="w-full bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-indigo-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                ) : isDragReject ? (
                  <div>
                    <div className="text-3xl mb-2">❌</div>
                    <p className="text-red-400 text-sm">Formato no soportado</p>
                  </div>
                ) : (
                  <div>
                    <div className="text-3xl mb-2">🎵</div>
                    <p className="text-slate-300 text-sm font-medium">
                      {isDragActive ? 'Suelta el archivo aquí' : 'Arrastra el archivo aquí'}
                    </p>
                    <p className="text-slate-500 text-xs mt-1">
                      o haz clic para buscar
                    </p>
                    <p className="text-slate-600 text-xs mt-3">
                      MP3, M4A, WAV, MP4, WEBM, MKV · máx 500 MB
                    </p>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2">
                {uploadDone ? (
                  <button onClick={onClose} className="btn-primary text-sm px-4 h-9">
                    Ver reuniones →
                  </button>
                ) : (
                  <button
                    onClick={onClose}
                    disabled={uploading}
                    className="btn-ghost text-sm px-4 h-9 disabled:opacity-50"
                  >
                    {uploading ? 'Subiendo...' : 'Cancelar'}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
