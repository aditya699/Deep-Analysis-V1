import axios, { AxiosResponse } from 'axios'

const API_BASE_URL = 'http://localhost:8000'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor to include auth token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Add response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      try {
        await authAPI.refreshToken()
        // Retry original request
        return apiClient.request(error.config)
      } catch {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_email')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  requestLogin: async (email: string) => {
    const response: AxiosResponse = await apiClient.post('/auth/request-login', { email })
    return response.data
  },

  verifyPassword: async (email: string, password: string) => {
    const response: AxiosResponse = await apiClient.post('/auth/verify-password', { 
      email, 
      password 
    })
    return response.data
  },

  refreshToken: async () => {
    const response: AxiosResponse = await apiClient.post('/auth/refresh-token')
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token)
    }
    return response.data
  }
}

// Chat API
export const chatAPI = {
  uploadCSV: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response: AxiosResponse = await apiClient.post('/chat/upload_csv', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  sendMessage: async (sessionId: string, userQuery: string) => {
    const response: AxiosResponse = await apiClient.post('/chat/chat', null, {
      params: {
        session_id: sessionId,
        user_query: userQuery
      }
    })
    return response.data
  },

  submitFeedback: async (messageId: string, feedback: 'thumbs_up' | 'thumbs_down') => {
    const response: AxiosResponse = await apiClient.post('/chat/feedback', null, {
      params: {
        message_id: messageId,
        feedback
      }
    })
    return response.data
  },

  getChatSummary: async (sessionId: string) => {
    const response: AxiosResponse = await apiClient.post('/chat/chat_summary', null, {
      params: {
        session_id: sessionId
      }
    })
    return response.data
  }
}

// Sessions API
export const sessionsAPI = {
  getAllSessions: async (page = 1, limit = 10) => {
    const response: AxiosResponse = await apiClient.get('/sessions/get_all_sessions', {
      params: { page, limit }
    })
    return response.data
  },

  getSessionById: async (sessionId: string) => {
    const response: AxiosResponse = await apiClient.get('/sessions/get_session_by_id', {
      params: { session_id: sessionId }
    })
    return response.data
  },

  deleteSession: async (sessionId: string) => {
    const response: AxiosResponse = await apiClient.delete('/sessions/delete_session', {
      params: { session_id: sessionId }
    })
    return response.data
  },

  getSessionMessages: async (sessionId: string) => {
    const response: AxiosResponse = await apiClient.get('/sessions/get_session_messages', {
      params: { session_id: sessionId }
    })
    return response.data
  }
}

// Deep Analysis API
export const deepAnalysisAPI = {
  startAnalysis: async (sessionId: string) => {
    const response: AxiosResponse = await apiClient.post('/deep_analysis/start', null, {
      params: { session_id: sessionId }
    })
    return response.data
  },

  getAnalysisStatus: async (sessionId: string) => {
    try {
      const response: AxiosResponse = await apiClient.get(`/deep_analysis/status/${sessionId}`)
      return response.data
    } catch (error: any) {
      // If 404 or 500, likely no analysis exists yet
      if (error.response?.status === 404 || error.response?.status === 500) {
        return null
      }
      throw error
    }
  }
}

export default apiClient