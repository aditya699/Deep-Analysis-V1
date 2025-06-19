import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, 
  Download, 
  BarChart3,
  CheckCircle,
  Clock,
  XCircle,
  Loader,
  FileText,
  Sparkles,
  TrendingUp
} from 'lucide-react'
import { sessionsAPI, deepAnalysisAPI } from '../services/api'
import { Session, DeepAnalysisStatus } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'

const DeepAnalysis: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  
  const [session, setSession] = useState<Session | null>(null)
  const [analysisStatus, setAnalysisStatus] = useState<DeepAnalysisStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [analysisStarted, setAnalysisStarted] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (sessionId) {
      loadSessionData()
      checkExistingAnalysis()
    }
  }, [sessionId])

  useEffect(() => {
    let interval: number | null = null
    
    if (analysisStarted && analysisStatus?.status !== 'Deep Analysis Complete' && analysisStatus?.status !== 'Deep Analysis Failed') {
      interval = setInterval(async () => {
        try {
          if (!sessionId) return
          
          const status = await deepAnalysisAPI.getAnalysisStatus(sessionId)
          if (status) {
            setAnalysisStatus(status)
            updateProgress(status)
            
            if (status.status === 'Deep Analysis Complete') {
              setProgress(100)
              toast.success('Deep analysis completed successfully!')
              if (interval) clearInterval(interval)
            } else if (status.status === 'Deep Analysis Failed') {
              toast.error('Deep analysis failed. Please try again.')
              if (interval) clearInterval(interval)
            }
          }
        } catch (error) {
          console.error('Error polling analysis status:', error)
          // Don't show error toast for polling failures - the server might just be busy
        }
      }, 2000) // Poll every 2 seconds
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [analysisStarted, analysisStatus?.status, sessionId])

  const loadSessionData = async () => {
    try {
      const sessionData = await sessionsAPI.getSessionById(sessionId!)
      setSession(sessionData)
    } catch (error) {
      toast.error('Failed to load session')
      navigate('/dashboard')
    } finally {
      setLoading(false)
    }
  }

  const checkExistingAnalysis = async () => {
    try {
      if (!sessionId) return
      
      const status = await deepAnalysisAPI.getAnalysisStatus(sessionId)
      if (status) {
        setAnalysisStatus(status)
        updateProgress(status)
        
        if (status.status !== 'Deep Analysis Complete' && status.status !== 'Deep Analysis Failed') {
          setAnalysisStarted(true)
        }
      }
    } catch (error) {
      // No existing analysis, that's fine
      console.log('No existing analysis found')
    }
  }

  const updateProgress = (status: DeepAnalysisStatus) => {
    if (!status || !status.kpi_list || !status.kpi_list.length) {
      setProgress(10)
      return
    }

    const completedKPIs = Object.values(status.kpi_status || {}).filter(value => value !== 0).length
    const totalKPIs = status.kpi_list.length
    const progressPercent = Math.min(90, (completedKPIs / totalKPIs) * 90)
    setProgress(progressPercent)
  }

  const startAnalysis = async () => {
    if (!sessionId) return
    
    try {
      await deepAnalysisAPI.startAnalysis(sessionId)
      setAnalysisStarted(true)
      setProgress(10)
      toast.success('Deep analysis started!')
    } catch (error) {
      toast.error('Failed to start deep analysis')
    }
  }

  const downloadReport = () => {
    if (analysisStatus?.report_url) {
      window.open(analysisStatus.report_url, '_blank')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Deep Analysis Complete': return 'text-green-600'
      case 'Deep Analysis Failed': return 'text-red-600'
      default: return 'text-blue-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Deep Analysis Complete': return <CheckCircle className="h-6 w-6 text-green-600" />
      case 'Deep Analysis Failed': return <XCircle className="h-6 w-6 text-red-600" />
      default: return <Clock className="h-6 w-6 text-blue-600" />
    }
  }

  const getKPIIcon = (status: number) => {
    if (status === 1) return <CheckCircle className="h-5 w-5 text-green-500" />
    if (status === -1) return <XCircle className="h-5 w-5 text-red-500" />
    return <Clock className="h-5 w-5 text-gray-400" />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-white">
        <LoadingSpinner text="Loading session..." />
      </div>
    )
  }

  if (!session) {
    return (
      <div className="flex items-center justify-center h-screen bg-white">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Session not found</h2>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-blue-600 hover:text-blue-700"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(`/chat/${sessionId}`)}
                className="p-2 text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  Deep Analysis
                </h1>
                <p className="text-sm text-gray-500">
                  {session.file_info?.original_filename || 'Unknown file'}
                </p>
              </div>
            </div>
            
            {analysisStatus?.status === 'Deep Analysis Complete' && (
              <button
                onClick={downloadReport}
                className="flex items-center space-x-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
              >
                <Download className="h-4 w-4" />
                <span>Download Report</span>
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {!analysisStarted ? (
          /* Start Analysis Screen */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-16"
          >
            <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-3xl flex items-center justify-center mx-auto mb-6">
              <BarChart3 className="h-12 w-12 text-white" />
            </div>
            
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              Ready for Deep Analysis
            </h1>
            
            <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
              Our AI will perform comprehensive analysis of your data, generating insights, 
              visualizations, and detailed reports with key performance indicators.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12 max-w-3xl mx-auto">
              <div className="bg-white p-6 rounded-xl border border-gray-200">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                  <TrendingUp className="h-6 w-6 text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Statistical Analysis</h3>
                <p className="text-sm text-gray-600">
                  Comprehensive statistical insights and trends in your data
                </p>
              </div>

              <div className="bg-white p-6 rounded-xl border border-gray-200">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                  <BarChart3 className="h-6 w-6 text-purple-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Visualizations</h3>
                <p className="text-sm text-gray-600">
                  Beautiful charts and graphs to understand your data
                </p>
              </div>

              <div className="bg-white p-6 rounded-xl border border-gray-200">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                  <FileText className="h-6 w-6 text-green-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Detailed Report</h3>
                <p className="text-sm text-gray-600">
                  Professional HTML report with all findings
                </p>
              </div>
            </div>

            <button
              onClick={startAnalysis}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-4 rounded-xl font-semibold text-lg transition-all duration-200 transform hover:scale-105"
            >
              <div className="flex items-center space-x-3">
                <Sparkles className="h-5 w-5" />
                <span>Start Deep Analysis</span>
              </div>
            </button>
          </motion.div>
        ) : (
          /* Progress Screen */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            {/* Status Header */}
            <div className="text-center">
              <div className="flex items-center justify-center space-x-3 mb-4">
                {analysisStatus && getStatusIcon(analysisStatus.status)}
                <h1 className={`text-2xl font-bold ${analysisStatus && getStatusColor(analysisStatus.status)}`}>
                  {analysisStatus?.status || 'Starting Analysis...'}
                </h1>
              </div>
              
              {analysisStatus?.status === 'Deep Analysis Complete' ? (
                <p className="text-gray-600">
                  Your analysis is complete! Download the report to view detailed insights.
                </p>
              ) : analysisStatus?.status === 'Deep Analysis Failed' ? (
                <p className="text-gray-600">
                  Analysis encountered an error. Please try again or contact support.
                </p>
              ) : (
                <p className="text-gray-600">
                  Please wait while we analyze your data. This may take a few minutes.
                </p>
              )}
            </div>

            {/* Progress Bar */}
            <div className="bg-white rounded-xl p-6 border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Analysis Progress</h2>
                <span className="text-2xl font-bold text-blue-600">{Math.round(progress)}%</span>
              </div>
              
              <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                <motion.div
                  className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                />
              </div>
              
              {progress < 100 && analysisStatus?.status !== 'Deep Analysis Failed' && (
                <div className="flex items-center justify-center text-gray-500">
                  <Loader className="h-4 w-4 animate-spin mr-2" />
                  <span>Analyzing your data...</span>
                </div>
              )}
            </div>

            {/* KPI Status */}
            {analysisStatus && analysisStatus.kpi_list && analysisStatus.kpi_list.length > 0 && (
              <div className="bg-white rounded-xl p-6 border border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Key Performance Indicators
                </h2>
                
                <div className="grid gap-3">
                  <AnimatePresence>
                    {analysisStatus.kpi_list.map((kpi, index) => (
                      <motion.div
                        key={kpi}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg"
                      >
                        {getKPIIcon((analysisStatus.kpi_status && analysisStatus.kpi_status[kpi]) || 0)}
                        <span className="flex-1 text-gray-900">{kpi}</span>
                        {(!analysisStatus.kpi_status || analysisStatus.kpi_status[kpi] === 0) && (
                          <Loader className="h-4 w-4 animate-spin text-blue-500" />
                        )}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-center space-x-4">
              <button
                onClick={() => navigate(`/chat/${sessionId}`)}
                className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Return to Chat
              </button>
              
              {analysisStatus?.status === 'Deep Analysis Failed' && (
                <button
                  onClick={startAnalysis}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Try Again
                </button>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default DeepAnalysis 