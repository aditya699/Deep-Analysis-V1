import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  Send, 
  ArrowLeft, 
  Download, 
  BarChart3,
  MessageCircle,
  ThumbsUp,
  ThumbsDown,
  Code,
  Image as ImageIcon,
  Lightbulb,
  Loader
} from 'lucide-react'
import { sessionsAPI, chatAPI, deepAnalysisAPI } from '../services/api'
import { Session, Message, ChatResponse, DeepAnalysisStatus } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism'

const ChatSession: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  
  const [session, setSession] = useState<Session | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState<DeepAnalysisStatus | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (sessionId) {
      loadSessionData()
      loadMessages()
    }
  }, [sessionId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

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

  const loadMessages = async () => {
    try {
      const response = await sessionsAPI.getSessionMessages(sessionId!)
      setMessages(response.messages)
    } catch (error) {
      toast.error('Failed to load messages')
    }
  }

  const sendMessage = async () => {
    if (!inputValue.trim() || sending) return

    const userMessage = inputValue
    setInputValue('')
    setSending(true)

    // Add user message to UI immediately
    const tempUserMessage: Message = {
      _id: 'temp-user',
      session_id: sessionId!,
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString(),
      content_type: 'text'
    }
    setMessages(prev => [...prev, tempUserMessage])

    try {
      const response: ChatResponse = await chatAPI.sendMessage(sessionId!, userMessage)
      
      // Replace temp message and add assistant response
      const assistantMessage: Message = {
        _id: response.message_id,
        session_id: sessionId!,
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
        content_type: 'text',
        metadata: {
          code: response.code,
          code_explanation: response.code_explanation,
          file_url: response.file_url
        }
      }

      const finalUserMessage: Message = {
        ...tempUserMessage,
        _id: 'user-' + Date.now()
      }

      setMessages(prev => [...prev.slice(0, -1), finalUserMessage, assistantMessage])
    } catch (error: any) {
      // Remove temp message on error
      setMessages(prev => prev.slice(0, -1))
      toast.error(error?.response?.data?.detail || 'Failed to send message')
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleFeedback = async (messageId: string, feedback: 'thumbs_up' | 'thumbs_down') => {
    try {
      await chatAPI.submitFeedback(messageId, feedback)
      toast.success('Feedback submitted!')
    } catch (error) {
      toast.error('Failed to submit feedback')
    }
  }

  const startDeepAnalysis = async () => {
    if (!sessionId) return
    
    setAnalysisLoading(true)
    try {
      await deepAnalysisAPI.startAnalysis(sessionId)
      toast.success('Deep analysis started!')
      // Poll for status
      const interval = setInterval(async () => {
        try {
          const status = await deepAnalysisAPI.getAnalysisStatus(sessionId)
          setAnalysisStatus(status)
          if (status.status === 'Deep Analysis Complete' || status.status === 'Deep Analysis Failed') {
            clearInterval(interval)
            setAnalysisLoading(false)
            if (status.status === 'Deep Analysis Complete') {
              toast.success('Deep analysis completed!')
            }
          }
        } catch (error) {
          clearInterval(interval)
          setAnalysisLoading(false)
        }
      }, 3000)
    } catch (error) {
      setAnalysisLoading(false)
      toast.error('Failed to start deep analysis')
    }
  }

  const askSmartQuestion = (question: string) => {
    setInputValue(question)
    inputRef.current?.focus()
  }

  if (loading) {
    return <LoadingSpinner text="Loading session..." />
  }

  if (!session) {
    return <div>Session not found</div>
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="p-2 text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-100"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                {session.file_info.original_filename}
              </h1>
              <p className="text-sm text-gray-500">
                {session.csv_info.total_columns} columns • {session.csv_info.preview_data.length} preview rows
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={startDeepAnalysis}
              disabled={analysisLoading}
              className="flex items-center px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
            >
              {analysisLoading ? (
                <Loader className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <BarChart3 className="h-4 w-4 mr-2" />
              )}
              Deep Analysis
            </button>
            
            {analysisStatus?.report_url && (
              <a
                href={analysisStatus.report_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                <Download className="h-4 w-4 mr-2" />
                Report
              </a>
            )}
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar with Smart Questions */}
        <div className="w-80 bg-white border-r flex flex-col">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-900 flex items-center">
              <Lightbulb className="h-5 w-5 mr-2 text-yellow-500" />
              Smart Questions
            </h2>
          </div>
          
          <div className="flex-1 p-4 space-y-2 overflow-y-auto">
            {session.smart_questions.map((question, index) => (
              <button
                key={index}
                onClick={() => askSmartQuestion(question)}
                className="w-full text-left p-3 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
              >
                {question}
              </button>
            ))}
          </div>

          {analysisStatus && (
            <div className="p-4 border-t">
              <h3 className="font-medium text-gray-900 mb-2">Analysis Status</h3>
              <div className="text-sm">
                <p className="text-gray-600">{analysisStatus.status}</p>
                {analysisStatus.kpi_list.length > 0 && (
                  <div className="mt-2">
                    <p className="font-medium">KPIs:</p>
                    <ul className="text-xs text-gray-500">
                      {analysisStatus.kpi_list.map((kpi, index) => (
                        <li key={index} className="flex items-center">
                          <span className={`w-2 h-2 rounded-full mr-2 ${
                            analysisStatus.kpi_status[kpi] === 1 ? 'bg-green-500' :
                            analysisStatus.kpi_status[kpi] === -1 ? 'bg-red-500' : 'bg-gray-300'
                          }`} />
                          {kpi}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message._id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`
                    max-w-2xl rounded-lg p-4 shadow-sm
                    ${message.role === 'user' 
                      ? 'bg-primary-500 text-white' 
                      : 'bg-white text-gray-900'
                    }
                  `}>
                    <div className="prose prose-sm max-w-none">
                      {message.role === 'user' ? (
                        <p className="text-white">{message.content}</p>
                      ) : (
                        <ReactMarkdown
                          components={{
                            code({ node, inline, className, children, ...props }) {
                              const match = /language-(\w+)/.exec(className || '')
                              return !inline && match ? (
                                <SyntaxHighlighter
                                  style={tomorrow}
                                  language={match[1]}
                                  PreTag="div"
                                  {...props}
                                >
                                  {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                              ) : (
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              )
                            }
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      )}
                    </div>

                    {/* Code and Image attachments */}
                    {message.metadata?.code && (
                      <div className="mt-3 p-3 bg-gray-100 rounded-lg">
                        <div className="flex items-center text-sm text-gray-600 mb-2">
                          <Code className="h-4 w-4 mr-1" />
                          Generated Code
                        </div>
                        <SyntaxHighlighter
                          language="python"
                          style={tomorrow}
                          customStyle={{ margin: 0, fontSize: '12px' }}
                        >
                          {message.metadata.code}
                        </SyntaxHighlighter>
                        {message.metadata.code_explanation && (
                          <p className="mt-2 text-sm text-gray-600">
                            {message.metadata.code_explanation}
                          </p>
                        )}
                      </div>
                    )}

                    {message.metadata?.file_url && (
                      <div className="mt-3">
                        <div className="flex items-center text-sm text-gray-600 mb-2">
                          <ImageIcon className="h-4 w-4 mr-1" />
                          Generated Visualization
                        </div>
                        <img 
                          src={message.metadata.file_url} 
                          alt="Generated chart"
                          className="max-w-full h-auto rounded-lg border"
                        />
                      </div>
                    )}

                    {/* Feedback buttons for assistant messages */}
                    {message.role === 'assistant' && (
                      <div className="flex items-center justify-end space-x-2 mt-3 pt-3 border-t border-gray-200">
                        <button
                          onClick={() => handleFeedback(message._id, 'thumbs_up')}
                          className="p-1 text-gray-400 hover:text-green-500"
                        >
                          <ThumbsUp className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleFeedback(message._id, 'thumbs_down')}
                          className="p-1 text-gray-400 hover:text-red-500"
                        >
                          <ThumbsDown className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            
            {sending && (
              <div className="flex justify-start">
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <LoadingSpinner size="sm" text="AI is thinking..." />
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t bg-white p-4">
            <div className="flex items-end space-x-3">
              <div className="flex-1">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask a question about your data..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                  disabled={sending}
                />
              </div>
              <button
                onClick={sendMessage}
                disabled={!inputValue.trim() || sending}
                className="p-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatSession