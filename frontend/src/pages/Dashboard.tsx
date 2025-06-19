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
  Clock,
  BarChart3,
  Plus,
  Search
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

  const filteredSessions = sessions.filter(session =>
    session.file_info.original_filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    session.session_id.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <BarChart3 className="h-8 w-8 text-primary-500" />
              <span className="ml-2 text-xl font-semibold text-gray-900">
                Deep Analysis
              </span>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-sm text-gray-600">
                <User className="h-4 w-4 mr-1" />
                {user?.email}
              </div>
              <button
                onClick={logout}
                className="flex items-center text-sm text-gray-600 hover:text-gray-900"
              >
                <LogOut className="h-4 w-4 mr-1" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Upload Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Chat with Your CSV Data
          </h1>
          <p className="text-gray-600 mb-6">
            Upload a CSV file and start asking questions about your data using AI
          </p>
          
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
              ${isDragActive 
                ? 'border-primary-500 bg-primary-50' 
                : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
              }
              ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            <input {...getInputProps()} />
            <div className="space-y-4">
              {uploading ? (
                <LoadingSpinner text="Uploading CSV..." />
              ) : (
                <>
                  <Upload className="mx-auto h-12 w-12 text-gray-400" />
                  <div>
                    <p className="text-lg font-medium text-gray-900">
                      {isDragActive ? 'Drop your CSV file here' : 'Upload CSV File'}
                    </p>
                    <p className="text-sm text-gray-600">
                      Drag and drop or click to select • Max 30MB
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Sessions Section */}
        <div>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Your Sessions</h2>
            
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search sessions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>

          {loading ? (
            <LoadingSpinner text="Loading sessions..." />
          ) : filteredSessions.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No sessions found</h3>
              <p className="mt-1 text-sm text-gray-500">
                {searchTerm ? 'Try adjusting your search' : 'Upload a CSV file to get started'}
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <AnimatePresence>
                {filteredSessions.map((session) => (
                  <motion.div
                    key={session._id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="bg-white rounded-lg shadow-sm border hover:shadow-md transition-shadow"
                  >
                    <div className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h3 className="text-lg font-medium text-gray-900 truncate">
                            {session.file_info.original_filename}
                          </h3>
                          <p className="text-sm text-gray-500 mt-1">
                            {session.csv_info.total_columns} columns • {session.csv_info.preview_data.length} preview rows
                          </p>
                          <div className="flex items-center text-xs text-gray-400 mt-2">
                            <Clock className="h-3 w-3 mr-1" />
                            {new Date(session.created_at).toLocaleDateString()}
                          </div>
                        </div>
                        
                        <button
                          onClick={() => deleteSession(session.session_id)}
                          className="text-gray-400 hover:text-red-500"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                      
                      <div className="mt-4 flex space-x-2">
                        <button
                          onClick={() => navigate(`/chat/${session.session_id}`)}
                          className="flex-1 flex items-center justify-center px-3 py-2 bg-primary-500 text-white text-sm rounded-md hover:bg-primary-600"
                        >
                          <MessageCircle className="h-4 w-4 mr-1" />
                          Chat
                        </button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center space-x-2 mt-8">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <button
                  key={page}
                  onClick={() => loadSessions(page)}
                  className={`
                    px-3 py-2 text-sm rounded-md
                    ${page === currentPage
                      ? 'bg-primary-500 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                    }
                  `}
                >
                  {page}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard