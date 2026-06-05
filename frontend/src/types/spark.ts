export interface SparkTarget {
  id: number;
  nickname: string;
  remark?: string | null;
  receiver_id: string;
  custom_template?: string | null;
  enabled: boolean;
  last_status?: string | null;
  last_run_at?: string | null;
  last_error?: string | null;
}

export interface SparkSettings {
  enabled: boolean;
  execute_time: string;
  default_template?: string | null;
  random_template_enabled: boolean;
  daily_limit: number;
  skip_today: boolean;
}

export interface TodayStatus {
  execute_date: string;
  target_count: number;
  success_count: number;
  failed_count: number;
  unsupported_count: number;
  skipped_count: number;
  job_status: string;
  last_execute_at?: string | null;
}

export interface SparkRecord {
  id: number;
  execute_date: string;
  execute_time: string;
  target_nickname?: string | null;
  message?: string | null;
  channel: string;
  status: string;
  error_message?: string | null;
}
