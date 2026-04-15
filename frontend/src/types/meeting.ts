export type MeetingPlatform = 'zoom' | 'teams' | 'google_meet' | 'manual'

export type MeetingStatus =
  | 'uploaded'
  | 'queued'
  | 'transcribing'
  | 'transcribed'
  | 'analyzing'
  | 'analyzed'
  | 'failed'
  | 'archived'

export interface Meeting {
  id: string
  title: string
  description?: string
  platform: MeetingPlatform
  meeting_date: string
  duration_seconds?: number
  recording_url?: string
  recording_size_bytes?: number
  recording_format?: string
  status: MeetingStatus
  processing_error?: string
  processing_started_at?: string
  processing_completed_at?: string
  zoom_meeting_id?: string
  teams_meeting_id?: string
  organizer_id?: string
  participant_count?: number
  created_by?: string
  created_at: string
  updated_at: string
  // Relations
  organizer?: Person
  participants?: MeetingParticipant[]
  action_items_count?: number
}

export interface MeetingParticipant {
  id: string
  meeting_id: string
  person_id: string
  speaker_label?: string
  joined_at?: string
  left_at?: string
  participation_duration_seconds?: number
  is_confirmed: boolean
  person?: Person
}

export interface TranscriptionSegment {
  id: string
  transcription_id: string
  meeting_id: string
  segment_index: number
  speaker_label?: string
  person_id?: string
  start_time: number
  end_time: number
  text: string
  confidence?: number
  person?: Person
}

export interface Transcription {
  id: string
  meeting_id: string
  whisper_model: string
  language: string
  word_count?: number
  duration_seconds?: number
  confidence_avg?: number
  created_at: string
  segments?: TranscriptionSegment[]
}

export interface AIAnalysis {
  id: string
  meeting_id: string
  llm_model: string
  executive_summary?: string
  meeting_sentiment?: 'positive' | 'neutral' | 'tense' | 'unproductive'
  topics_discussed?: string[]
  prompt_tokens?: number
  completion_tokens?: number
  created_at: string
}

// Para importar desde la API
export interface Person {
  id: string
  full_name: string
  email?: string
  department?: string
  area?: string
  role?: string
  avatar_url?: string
  is_active: boolean
  adherence_rate?: number
  created_at: string
  updated_at: string
}
