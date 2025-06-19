import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { 
  Upload, 
  MessageCircle, 
  FileText, 
  Trash2, 
  User, 
  LogOut,
  BarChart3,
  Search,
  Plus,
  Sparkles,
  Calendar,
  Database,
  ChevronRight,
  Moon,
  Sun,
  Settings,
  History
} from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { sessionsAPI, chatAPI } from '../services/api'
import { Session, UploadResponse } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'

const Dashboard: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const loadSessions = async (page = 1) => {
    try {
      setLoading(true)
      const response = await sessionsAPI.getAllSessions(page, 10)
      setSessions(response.sessions)
      setCurrentPage(response.pagination.current_page)
      setTotalPages(response.pagination.total_pages)
    } catch (error) {
      toast.error('Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSessions()
  }, [])

  const onDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    if (!file.name.endsWith('.csv')) {
      toast.error('Please upload a CSV file')
      return
    }

    if (file.size > 30 * 1024 * 1024) {
      toast.error('File size must be less than 30MB')
      return
    }

    setUploading(true)
    try {
      const response: UploadResponse = await chatAPI.uploadCSV(file)
      toast.success('CSV uploaded successfully!')
      navigate(`/chat/${response.session_id}`)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to upload CSV')
    } finally {
      setUploading(false)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv']
    },
    multiple: false,
    disabled: uploading
  })

  const deleteSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this session?')) return

    try {
      await sessionsAPI.deleteSession(sessionId)
      toast.success('Session deleted successfully')
      loadSessions(currentPage)
    } catch (error) {
      toast.error('Failed to delete session')
    }
  }

  const filteredSessions = (sessions || []).filter(session =>
    session?.file_info?.original_filename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    session?.session_id?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Header */}
      <header className="sticky top-0 z-10 backdrop-blur-sm" style={{ 
        backgroundColor: 'rgba(255, 255, 255, 0.8)', 
        borderBottom: '1px solid var(--border-light)' 
      }}>
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
                <Database className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Deep Analysis</h1>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>AI-powered data insights</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2 px-3 py-2 rounded-lg" style={{ background: 'var(--bg-secondary)' }}>
                <User className="h-4 w-4" style={{ color: 'var(--text-secondary)' }} />
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{user?.email}</span>
              </div>
              <button
                onClick={logout}
                className="flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors hover:bg-opacity-80"
                style={{ background: 'var(--bg-secondary)' }}
              >
                <LogOut className="h-4 w-4" style={{ color: 'var(--text-secondary)' }} />
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 lg:px-8 py-12">
        {/* Welcome Section */}
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="w-20 h-20 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-3xl flex items-center justify-center mx-auto mb-6">
              <MessageCircle className="h-10 w-10 text-white" />
            </div>
            <h1 className="text-5xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Chat with Your Data
            </h1>
            <p className="text-xl max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
              Upload your CSV files and start asking questions. Our AI will analyze your data and provide intelligent insights in natural language.
            </p>
          </motion.div>
        </div>

        {/* Upload Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-16"
        >
          <div
            {...getRootProps()}
            className={`
              relative border-2 border-dashed rounded-3xl p-16 text-center cursor-pointer transition-all duration-300
              ${isDragActive 
                ? 'scale-105 shadow-2xl' 
                : 'hover:shadow-xl'
              }
              ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
            `}
            style={{ 
              borderColor: isDragActive ? 'var(--accent-primary)' : 'var(--border-medium)',
              backgroundColor: isDragActive ? 'rgba(16, 163, 127, 0.05)' : 'var(--bg-secondary)'
            }}
          >
            <input {...getInputProps()} />
            <div className="space-y-8">
              {uploading ? (
                <div className="space-y-4">
                  <div className="w-20 h-20 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-3xl flex items-center justify-center mx-auto">
                    <div className="spinner w-8 h-8"></div>
                  </div>
                  <div>
                    <p className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Processing your CSV...</p>
                    <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>This may take a moment</p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="w-20 h-20 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-3xl flex items-center justify-center mx-auto">
                    <Upload className="h-10 w-10 text-white" />
                  </div>
                  <div className="space-y-3">
                    <h3 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {isDragActive ? 'Drop your CSV file here' : 'Upload your CSV file'}
                    </h3>
                    <p className="text-lg" style={{ color: 'var(--text-secondary)' }}>
                      Drag and drop or click to browse • Max 30MB
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        </motion.div>

        {/* Sessions Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-8"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <History className="h-6 w-6" style={{ color: 'var(--text-primary)' }} />
              <h2 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
                Recent Sessions
              </h2>
            </div>
            
            {sessions.length > 0 && (
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                <input
                  type="text"
                  placeholder="Search sessions..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-2 rounded-lg border text-sm w-64"
                  style={{ 
                    backgroundColor: 'var(--bg-tertiary)',
                    borderColor: 'var(--border-medium)',
                    color: 'var(--text-primary)'
                  }}
                />
              </div>
            )}
          </div>

          {loading ? (
            <div className="text-center py-12">
              <LoadingSpinner text="Loading sessions..." />
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="text-center py-16 rounded-2xl" style={{ backgroundColor: 'var(--bg-secondary)' }}>
              <div className="w-16 h-16 bg-gradient-to-br from-gray-400 to-gray-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <FileText className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                {searchTerm ? 'No sessions found' : 'No sessions yet'}
              </h3>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                {searchTerm ? 'Try adjusting your search terms' : 'Upload your first CSV file to get started'}
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {filteredSessions.map((session) => (
                <motion.div
                  key={session.session_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ y: -2 }}
                  className="card group cursor-pointer"
                  onClick={() => navigate(`/chat/${session.session_id}`)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 flex-1">
                      <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
                        <Database className="h-6 w-6 text-white" />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold truncate group-hover:text-opacity-80" style={{ color: 'var(--text-primary)' }}>
                          {session.file_info?.original_filename || 'Unknown File'}
                        </h3>
                        <div className="flex items-center space-x-4 mt-1">
                          <span className="text-sm flex items-center" style={{ color: 'var(--text-secondary)' }}>
                            <Calendar className="h-3 w-3 mr-1" />
                            {formatDate(session.created_at)}
                          </span>
                                                     {session.csv_info && (
                             <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                               {session.csv_info.preview_data?.length} preview rows • {session.csv_info.total_columns} columns
                             </span>
                           )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/analysis/${session.session_id}`)
                        }}
                        className="btn-secondary text-xs flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <BarChart3 className="h-3 w-3" />
                        <span>Analyze</span>
                      </button>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteSession(session.session_id)
                        }}
                        className="p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50"
                        style={{ color: 'var(--text-tertiary)' }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                      
                      <ChevronRight className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: 'var(--text-tertiary)' }} />
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center space-x-2 mt-8">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <button
                  key={page}
                  onClick={() => loadSessions(page)}
                  className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                    page === currentPage 
                      ? 'btn-primary' 
                      : 'btn-secondary'
                  }`}
                >
                  {page}
                </button>
              ))}
            </div>
          )}
        </motion.div>

        {/* Features Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-20 grid md:grid-cols-3 gap-8"
        >
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto">
              <MessageCircle className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Natural Language</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Ask questions about your data in plain English. No SQL or complex queries needed.
            </p>
          </div>
          
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-600 rounded-2xl flex items-center justify-center mx-auto">
              <BarChart3 className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Deep Analysis</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Get comprehensive reports with visualizations and insights automatically generated.
            </p>
          </div>
          
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl flex items-center justify-center mx-auto">
              <Sparkles className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>AI-Powered</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Leverage advanced AI to discover patterns and trends in your data automatically.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default Dashboard