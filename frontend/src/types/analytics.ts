export interface PersonAdherence {
  person_id: string
  full_name: string
  department?: string
  area?: string
  total_items: number
  completed_items: number
  overdue_items: number
  on_time_items: number
  late_items: number
  adherence_rate: number  // % completados / total
  on_time_rate: number    // % completados a tiempo / completados
}

export interface MonthlyKPI {
  month: string            // ISO date string
  meetings_processed: number
  total_action_items: number
  completed_items: number
  overdue_items: number
  avg_days_overdue: number
  global_on_time_rate: number
}

export interface DashboardSummary {
  total_meetings: number
  meetings_this_month: number
  total_action_items: number
  pending_items: number
  overdue_items: number
  completed_this_month: number
  global_adherence_rate: number
  global_on_time_rate: number
  top_overdue_person?: PersonAdherence
  top_adherent_person?: PersonAdherence
}
