import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  Send, 
  ArrowLeft, 
  BarChart3,
  ThumbsUp,
  ThumbsDown,
  Code,
  Image as ImageIcon,
  Lightbulb,
  Loader,
  MessageSquare,
  Sparkles,
  Menu,
  X,
  Copy,
  Check,
  Download,
  Settings
} from 'lucide-react'
import { sessionsAPI, chatAPI } from '../services/api'
import { Session, Message, ChatResponse } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'

const ChatSession: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  
  const [session, setSession] = useState<Session | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (sessionId) {
      loadSessionData()
      loadMessages()
    }
  }, [sessionId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (!sidebarOpen) {
      inputRef.current?.focus()
    }
  }, [sidebarOpen])

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

    const userMessage = inputValue.trim()
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

  const copyToClipboard = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedCode(type)
      toast.success('Copied to clipboard!')
      setTimeout(() => setCopiedCode(null), 2000)
    } catch (error) {
      toast.error('Failed to copy')
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

  const askSmartQuestion = (question: string) => {
    setInputValue(question)
    inputRef.current?.focus()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
        <LoadingSpinner text="Loading session..." />
      </div>
    )
  }

  if (!session) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Session not found</h2>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn-primary"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ x: -320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -320, opacity: 0 }}
            transition={{ type: "spring", damping: 20, stiffness: 300 }}
            className="w-80 flex flex-col"
            style={{ 
              backgroundColor: 'var(--bg-secondary)', 
              borderRight: '1px solid var(--border-light)' 
            }}
          >
            {/* Sidebar Header */}
            <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid var(--border-light)' }}>
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center">
                  <MessageSquare className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h1 className="font-semibold text-lg" style={{ color: 'var(--text-primary)' }}>Chat Session</h1>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>AI Data Analysis</p>
                </div>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1 rounded hover:bg-opacity-20"
                style={{ background: 'var(--bg-tertiary)' }}
              >
                <X className="h-5 w-5" style={{ color: 'var(--text-secondary)' }} />
              </button>
            </div>

            {/* File Info */}
            <div className="p-4" style={{ borderBottom: '1px solid var(--border-light)' }}>
              <div className="flex items-center space-x-2 mb-2">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Active Session</span>
              </div>
              <h2 className="font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                {session.file_info?.original_filename || 'Unknown file'}
              </h2>
              <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                {session.csv_info?.preview_data?.length || 0} preview rows • {session.csv_info?.total_columns || 0} columns
              </p>
            </div>

            {/* Smart Questions */}
            <div className="flex-1 overflow-y-auto">
              <div className="p-4">
                <div className="flex items-center space-x-2 mb-4">
                  <Sparkles className="h-4 w-4" style={{ color: 'var(--accent-primary)' }} />
                  <h3 className="font-medium" style={{ color: 'var(--text-primary)' }}>Smart Questions</h3>
                </div>
                
                <div className="space-y-2">
                  {session.smart_questions?.map((question, index) => (
                    <motion.button
                      key={index}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => askSmartQuestion(question)}
                      className="w-full text-left p-3 text-sm rounded-lg transition-all duration-200 border"
                      style={{ 
                        backgroundColor: 'var(--bg-primary)',
                        borderColor: 'var(--border-light)',
                        color: 'var(--text-secondary)'
                      }}
                    >
                      <div className="flex items-start space-x-2">
                        <MessageSquare className="h-4 w-4 mt-0.5 flex-shrink-0" style={{ color: 'var(--text-tertiary)' }} />
                        <span>{question}</span>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </div>
            </div>

            {/* Deep Analysis Section */}
            <div className="p-4" style={{ borderTop: '1px solid var(--border-light)' }}>
              <button
                onClick={() => navigate(`/analysis/${sessionId}`)}
                className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white px-4 py-3 rounded-lg font-medium transition-all duration-200 flex items-center justify-center space-x-2"
              >
                <BarChart3 className="h-4 w-4" />
                <span>Deep Analysis</span>
              </button>
            </div>

            {/* Back to Dashboard */}
            <div className="p-4" style={{ borderTop: '1px solid var(--border-light)' }}>
              <button
                onClick={() => navigate('/dashboard')}
                className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors hover:bg-opacity-80"
                style={{ 
                  color: 'var(--text-secondary)'
                }}
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Back to Dashboard</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--border-light)' }}>
          <div className="flex items-center space-x-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 rounded-lg transition-colors"
                style={{ background: 'var(--bg-secondary)' }}
              >
                <Menu className="h-5 w-5" style={{ color: 'var(--text-secondary)' }} />
              </button>
            )}
            <div>
              <h1 className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                {session.file_info?.original_filename || 'Chat Session'}
              </h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Chat with your data using AI
              </p>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-4 py-6">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <MessageSquare className="h-8 w-8 text-white" />
                </div>
                <h2 className="text-2xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                  Start a conversation
                </h2>
                <p className="mb-6" style={{ color: 'var(--text-secondary)' }}>
                  Ask questions about your data and get AI-powered insights
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                  {session.smart_questions?.slice(0, 4).map((question, index) => (
                    <motion.button
                      key={index}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => askSmartQuestion(question)}
                      className="text-left p-4 rounded-xl border transition-all duration-200 hover:border-opacity-80"
                      style={{ 
                        backgroundColor: 'var(--bg-secondary)',
                        borderColor: 'var(--border-light)'
                      }}
                    >
                      <div className="flex items-start space-x-3">
                        <Lightbulb className="h-5 w-5 mt-0.5 flex-shrink-0" style={{ color: 'var(--accent-primary)' }} />
                        <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{question}</span>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((message, index) => (
                  <motion.div
                    key={message._id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`group ${message.role === 'user' ? 'ml-auto' : ''}`}
                  >
                    {message.role === 'user' ? (
                      <div className="flex justify-end">
                        <div className="max-w-3xl rounded-2xl px-6 py-4" style={{ 
                          backgroundColor: 'var(--accent-primary)', 
                          color: 'white' 
                        }}>
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        </div>
                      </div>
                    ) : (
                      <div className="flex space-x-4">
                        <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-full flex items-center justify-center flex-shrink-0">
                          <Sparkles className="h-4 w-4 text-white" />
                        </div>
                        <div className="flex-1 max-w-3xl">
                          <div className="prose prose-lg max-w-none">
                            <ReactMarkdown
                              components={{
                                code({ node, inline, className, children, ...props }: any) {
                                  const match = /language-(\w+)/.exec(className || '')
                                  const isInline = !className || !match
                                  return !isInline ? (
                                    <div className="my-4 relative group">
                                      <button
                                        onClick={() => copyToClipboard(String(children).replace(/\n$/, ''), `code-${index}`)}
                                        className="absolute top-2 right-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                                        style={{ background: 'var(--bg-tertiary)' }}
                                      >
                                        {copiedCode === `code-${index}` ? (
                                          <Check className="h-4 w-4" style={{ color: 'var(--accent-primary)' }} />
                                        ) : (
                                          <Copy className="h-4 w-4" style={{ color: 'var(--text-secondary)' }} />
                                        )}
                                      </button>
                                      <SyntaxHighlighter
                                        style={oneLight}
                                        language={match[1]}
                                        PreTag="div"
                                        customStyle={{
                                          background: 'var(--bg-tertiary)',
                                          border: '1px solid var(--border-light)',
                                          borderRadius: '12px',
                                          margin: 0
                                        }}
                                        {...props}
                                      >
                                        {String(children).replace(/\n$/, '')}
                                      </SyntaxHighlighter>
                                    </div>
                                  ) : (
                                    <code className="px-1.5 py-0.5 rounded text-sm font-mono" style={{ 
                                      backgroundColor: 'rgba(16, 163, 127, 0.1)', 
                                      color: 'var(--accent-primary)' 
                                    }} {...props}>
                                      {children}
                                    </code>
                                  )
                                },
                              }}
                            >
                              {message.content}
                            </ReactMarkdown>
                          </div>

                          {/* Code and explanation attachments */}
                          {message.metadata?.code && (
                            <div className="mt-4 border rounded-xl overflow-hidden" style={{ borderColor: 'var(--border-light)' }}>
                              <div className="px-4 py-3" style={{ 
                                backgroundColor: 'var(--bg-secondary)', 
                                borderBottom: '1px solid var(--border-light)' 
                              }}>
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-2">
                                    <Code className="h-4 w-4" style={{ color: 'var(--text-secondary)' }} />
                                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Generated Code</span>
                                  </div>
                                  <button
                                    onClick={() => copyToClipboard(message.metadata?.code!, `metadata-${index}`)}
                                    className="p-1 rounded transition-colors"
                                    style={{ background: 'var(--bg-tertiary)' }}
                                  >
                                    {copiedCode === `metadata-${index}` ? (
                                      <Check className="h-4 w-4" style={{ color: 'var(--accent-primary)' }} />
                                    ) : (
                                      <Copy className="h-4 w-4" style={{ color: 'var(--text-secondary)' }} />
                                    )}
                                  </button>
                                </div>
                              </div>
                              <SyntaxHighlighter
                                language="python"
                                style={oneLight}
                                customStyle={{ margin: 0, fontSize: '14px' }}
                              >
                                {message.metadata.code}
                              </SyntaxHighlighter>
                              {message.metadata.code_explanation && (
                                <div className="px-4 py-3" style={{ 
                                  backgroundColor: 'var(--bg-secondary)', 
                                  borderTop: '1px solid var(--border-light)' 
                                }}>
                                  <div className="prose prose-sm max-w-none">
                                                                    <ReactMarkdown>
                                  {message.metadata.code_explanation}
                                </ReactMarkdown>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Image attachment */}
                          {message.metadata?.file_url && (
                            <div className="mt-4 border rounded-xl overflow-hidden" style={{ borderColor: 'var(--border-light)' }}>
                              <div className="px-4 py-3" style={{ 
                                backgroundColor: 'var(--bg-secondary)', 
                                borderBottom: '1px solid var(--border-light)' 
                              }}>
                                <div className="flex items-center space-x-2">
                                  <ImageIcon className="h-4 w-4" style={{ color: 'var(--text-secondary)' }} />
                                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Generated Visualization</span>
                                </div>
                              </div>
                              <img 
                                src={message.metadata.file_url} 
                                alt="Generated chart"
                                className="w-full"
                              />
                            </div>
                          )}

                          {/* Feedback buttons */}
                          <div className="flex items-center space-x-1 mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => handleFeedback(message._id, 'thumbs_up')}
                              className="p-2 rounded-lg transition-colors hover:bg-gray-100"
                            >
                              <ThumbsUp className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                            </button>
                            <button
                              onClick={() => handleFeedback(message._id, 'thumbs_down')}
                              className="p-2 rounded-lg transition-colors hover:bg-gray-100"
                            >
                              <ThumbsDown className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
            
            {sending && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex space-x-4"
              >
                <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-full flex items-center justify-center">
                  <Loader className="h-4 w-4 text-white animate-spin" />
                </div>
                <div className="flex-1">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--text-tertiary)' }}></div>
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--text-tertiary)', animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--text-tertiary)', animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </motion.div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div style={{ 
          borderTop: '1px solid var(--border-light)', 
          backgroundColor: 'var(--bg-primary)' 
        }}>
          <div className="max-w-4xl mx-auto p-4">
            <div className="relative rounded-2xl border transition-all duration-200" style={{ 
              backgroundColor: 'var(--bg-secondary)', 
              borderColor: 'var(--border-light)' 
            }}>
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask a question about your data..."
                className="w-full px-6 py-4 bg-transparent border-none resize-none focus:outline-none max-h-32"
                rows={1}
                disabled={sending}
                style={{
                  minHeight: '56px',
                  height: 'auto',
                  overflowY: inputValue.split('\n').length > 3 ? 'scroll' : 'hidden',
                  color: 'var(--text-primary)'
                }}
              />
              <div className="absolute right-3 bottom-3">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={sendMessage}
                  disabled={!inputValue.trim() || sending}
                  className="w-10 h-10 text-white rounded-xl flex items-center justify-center transition-all duration-200 hover:opacity-80"
                  style={{ 
                    backgroundColor: !inputValue.trim() || sending ? 'var(--text-tertiary)' : 'var(--accent-primary)'
                  }}
                >
                  <Send className="h-4 w-4" />
                </motion.button>
              </div>
            </div>
            <p className="text-xs mt-2 text-center" style={{ color: 'var(--text-secondary)' }}>
              Press Enter to send, Shift + Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatSession