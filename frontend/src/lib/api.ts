/**
 * Cliente HTTP para comunicarse con el backend FastAPI.
 * El frontend llama a /api/* que el proxy de Vite redirige a http://localhost:8000
 * En producción, la variable VITE_API_URL apunta al backend en Railway.
 */

import axios from 'axios'
import type { Meeting, MeetingPlatform } from '../types/meeting'
import type { ActionItem, ActionItemStatus, ActionItemPriority } from '../types/actionItem'

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// Interceptor: adjuntar token de Supabase Auth en cada request
apiClient.interceptors.request.use(async (config) => {
  const { supabase } = await import('./supabase')
  const { data } = await supabase.auth.getSession()
  if (data.session?.access_token) {
    config.headers.Authorization = `Bearer ${data.session.access_token}`
  }
  return config
})

// ─── Meetings ────────────────────────────────────────────────────────────────

export const meetingsApi = {
  list: (params?: { status?: string; platform?: MeetingPlatform }) =>
    apiClient.get<Meeting[]>('/meetings', { params }),

  get: (id: string) =>
    apiClient.get<Meeting>(`/meetings/${id}`),

  create: (data: {
    title: string
    description?: string
    platform: MeetingPlatform
    meeting_date: string
  }) => apiClient.post<Meeting>('/meetings', data),

  upload: (meetingId: string, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<{ message: string; meeting: Meeting }>(
      `/meetings/${meetingId}/upload`,
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (onProgress && e.total) {
            onProgress(Math.round((e.loaded / e.total) * 100))
          }
        },
        timeout: 300_000, // 5 min para archivos grandes
      }
    )
  },

  delete: (id: string) =>
    apiClient.delete(`/meetings/${id}`),

  getTranscription: (id: string) =>
    apiClient.get(`/meetings/${id}/transcription`),

  mapSpeaker: (meetingId: string, speakerLabel: string, personId: string) =>
    apiClient.post(`/meetings/${meetingId}/speakers`, { speaker_label: speakerLabel, person_id: personId }),
}

// ─── Action Items ─────────────────────────────────────────────────────────────

export const actionItemsApi = {
  list: (params?: {
    meeting_id?: string
    assignee_id?: string
    status?: ActionItemStatus
    item_type?: string
    priority?: ActionItemPriority
  }) => apiClient.get<ActionItem[]>('/action-items', { params }),

  get: (id: string) =>
    apiClient.get<ActionItem>(`/action-items/${id}`),

  create: (data: Partial<ActionItem>) =>
    apiClient.post<ActionItem>('/action-items', data),

  update: (id: string, data: Partial<ActionItem> & { change_note?: string }) =>
    apiClient.patch<ActionItem>(`/action-items/${id}`, data),

  updateStatus: (id: string, status: ActionItemStatus, note?: string) =>
    apiClient.patch<ActionItem>(`/action-items/${id}/status`, { status, change_note: note }),

  delete: (id: string) =>
    apiClient.delete(`/action-items/${id}`),
}

// ─── People ───────────────────────────────────────────────────────────────────

export const peopleApi = {
  list: (params?: { is_active?: boolean; area?: string }) =>
    apiClient.get('/people', { params }),

  get: (id: string) =>
    apiClient.get(`/people/${id}`),

  create: (data: { full_name: string; email?: string; department?: string; area?: string }) =>
    apiClient.post('/people', data),

  update: (id: string, data: object) =>
    apiClient.patch(`/people/${id}`, data),
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export const analyticsApi = {
  dashboard: () =>
    apiClient.get('/analytics/dashboard'),

  personAdherence: (params?: { area?: string; from_date?: string; to_date?: string }) =>
    apiClient.get('/analytics/adherence', { params }),

  monthlyKPIs: (months?: number) =>
    apiClient.get('/analytics/monthly-kpis', { params: { months } }),

  meetingStats: (meetingId: string) =>
    apiClient.get(`/analytics/meetings/${meetingId}`),
}
