export type ActionItemType = 'action_item' | 'decision' | 'commitment' | 'risk'

export type ActionItemStatus =
  | 'pending'
  | 'in_progress'
  | 'in_review'
  | 'completed'
  | 'overdue'
  | 'cancelled'

export type ActionItemPriority = 'low' | 'medium' | 'high' | 'critical'

export interface ActionItem {
  id: string
  meeting_id: string
  analysis_id?: string
  item_type: ActionItemType
  title: string
  description?: string
  context_quote?: string
  context_timestamp?: number
  assignee_id?: string
  assignee_name_raw?: string
  due_date?: string
  due_date_raw?: string
  status: ActionItemStatus
  completed_at?: string
  completed_by?: string
  completion_notes?: string
  was_on_time?: boolean
  days_overdue?: number
  ai_confidence?: number
  is_ai_generated: boolean
  was_manually_edited: boolean
  priority: ActionItemPriority
  tags?: string[]
  created_at: string
  updated_at: string
  // Relations
  assignee?: import('./meeting').Person
  meeting?: import('./meeting').Meeting
  updates?: ActionItemUpdate[]
}

export interface ActionItemUpdate {
  id: string
  action_item_id: string
  updated_by?: string
  field_changed: string
  old_value?: string
  new_value?: string
  change_note?: string
  created_at: string
}

export const ACTION_ITEM_TYPE_LABELS: Record<ActionItemType, string> = {
  action_item: 'Tarea',
  decision:    'Decisión',
  commitment:  'Compromiso',
  risk:        'Riesgo',
}

export const ACTION_ITEM_STATUS_LABELS: Record<ActionItemStatus, string> = {
  pending:     'Pendiente',
  in_progress: 'En Progreso',
  in_review:   'En Revisión',
  completed:   'Completado',
  overdue:     'Vencido',
  cancelled:   'Cancelado',
}

export const ACTION_ITEM_PRIORITY_LABELS: Record<ActionItemPriority, string> = {
  low:      'Baja',
  medium:   'Media',
  high:     'Alta',
  critical: 'Crítica',
}

export const KANBAN_COLUMNS: ActionItemStatus[] = [
  'pending',
  'in_progress',
  'in_review',
  'completed',
  'overdue',
]
