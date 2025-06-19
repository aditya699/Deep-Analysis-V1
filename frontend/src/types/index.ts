export interface User {
  email: string
  access_token: string
}

export interface Session {
  _id: string
  session_id: string
  user_email: string
  user_id: string
  file_info: {
    original_filename: string
    blob_name: string
    container_name: string
    file_url: string
    file_size: number
    content_type: string
  }
  csv_info: {
    total_columns: number
    column_names: string[]
    preview_data: Record<string, any>[]
  }
  smart_questions: string[]
  created_at: string
  updated_at: string
  status: string
}

export interface Message {
  _id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  content_type: string
  metadata?: {
    code?: string
    code_explanation?: string
    file_url?: string
  }
}

export interface ChatResponse {
  response: string
  code?: string
  code_explanation?: string
  file_url?: string
  message_id: string
}

export interface UploadResponse {
  session_id: string
  file_url: string
  file_name: string
  preview_data: Record<string, any>[]
  file_info: {
    original_filename: string
    blob_name: string
    container_name: string
    file_url: string
    file_size: number
    content_type: string
  }
  smart_questions: string[]
  message: string
  success: boolean
}

export interface DeepAnalysisStatus {
  status: string
  kpi_list: string[]
  kpi_status: Record<string, number>
  report_url?: string
  created_at: string
  updated_at: string
}

export interface PaginationInfo {
  current_page: number
  total_pages: number
  total_count: number
  limit: number
  has_next: boolean
  has_prev: boolean
}