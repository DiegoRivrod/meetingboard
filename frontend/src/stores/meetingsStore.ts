/**
 * Store global de reuniones usando Zustand.
 *
 * POR QUÉ Zustand y no useState local:
 * - El UploadModal y la MeetingsTable viven en ramas distintas del árbol React.
 *   Pasar datos entre ellos por props sería "prop drilling" — pasar datos a través
 *   de componentes intermedios que no los necesitan. Zustand ofrece un store
 *   centralizado que cualquier componente puede leer/modificar directamente.
 * - El polling de estado (queued → transcribing → analyzed) necesita actualizar
 *   la lista desde cualquier lugar sin re-montar componentes.
 */

import { create } from 'zustand'
import { meetingsApi } from '../lib/api'
import type { Meeting, MeetingStatus, MeetingPlatform } from '../types/meeting'

interface MeetingsState {
  meetings: Meeting[]
  loading: boolean
  error: string | null
  filterStatus: MeetingStatus | 'all'
  filterPlatform: MeetingPlatform | 'all'
  searchQuery: string

  // Acciones
  fetchMeetings: () => Promise<void>
  upsertMeeting: (meeting: Meeting) => void
  removeMeeting: (id: string) => void
  setFilterStatus: (status: MeetingStatus | 'all') => void
  setFilterPlatform: (platform: MeetingPlatform | 'all') => void
  setSearchQuery: (q: string) => void
}

export const useMeetingsStore = create<MeetingsState>((set, get) => ({
  meetings: [],
  loading: false,
  error: null,
  filterStatus: 'all',
  filterPlatform: 'all',
  searchQuery: '',

  fetchMeetings: async () => {
    set({ loading: true, error: null })
    try {
      const { filterStatus, filterPlatform } = get()
      const params: Record<string, string> = {}
      if (filterStatus !== 'all') params.status = filterStatus
      if (filterPlatform !== 'all') params.platform = filterPlatform

      const res = await meetingsApi.list(params as any)
      set({ meetings: res.data, loading: false })
    } catch (err: any) {
      set({
        error: err?.response?.data?.detail ?? 'Error al cargar reuniones',
        loading: false,
      })
    }
  },

  // upsertMeeting: inserta o actualiza una reunión en la lista local.
  // Se usa cuando el backend notifica un cambio de estado (polling).
  upsertMeeting: (meeting) => {
    set((state) => {
      const idx = state.meetings.findIndex((m) => m.id === meeting.id)
      if (idx === -1) {
        return { meetings: [meeting, ...state.meetings] }
      }
      const updated = [...state.meetings]
      updated[idx] = meeting
      return { meetings: updated }
    })
  },

  removeMeeting: (id) => {
    set((state) => ({ meetings: state.meetings.filter((m) => m.id !== id) }))
  },

  setFilterStatus: (status) => set({ filterStatus: status }),
  setFilterPlatform: (platform) => set({ filterPlatform: platform }),
  setSearchQuery: (q) => set({ searchQuery: q }),
}))

// Selector derivado: aplica búsqueda y filtros localmente.
// POR QUÉ local y no en la API: los filtros de texto libre son instantáneos
// si los datos ya están en memoria. Evita round-trips para cada keystroke.
export function useFilteredMeetings() {
  return useMeetingsStore((state) => {
    const q = state.searchQuery.toLowerCase()
    return state.meetings.filter((m) => {
      const matchesSearch =
        !q ||
        m.title.toLowerCase().includes(q) ||
        (m.description ?? '').toLowerCase().includes(q)
      return matchesSearch
    })
  })
}
