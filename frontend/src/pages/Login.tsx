import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Mail, Lock, ArrowRight } from 'lucide-react'
import LoadingSpinner from '../components/LoadingSpinner'

const Login: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [step, setStep] = useState<'email' | 'password'>('email')
  const [loading, setLoading] = useState(false)
  
  const { requestLogin, login } = useAuth()

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    setLoading(true)
    const success = await requestLogin(email)
    setLoading(false)
    
    if (success) {
      setStep('password')
    }
  }

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password.trim()) return

    setLoading(true)
    await login(email, password)
    setLoading(false)
  }

  const resetToEmail = () => {
    setStep('email')
    setPassword('')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-blue-100">
      <div className="max-w-md w-full space-y-8 p-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto h-12 w-12 bg-primary-500 rounded-lg flex items-center justify-center">
            <Mail className="h-6 w-6 text-white" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Deep Analysis
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Chat with your CSV data using AI
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          {step === 'email' ? (
            <form onSubmit={handleEmailSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="Enter your email"
                    required
                  />
                </div>
              </div>
              
              <button
                type="submit"
                disabled={loading || !email.trim()}
                className="w-full flex items-center justify-center px-4 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <LoadingSpinner size="sm" text="" />
                ) : (
                  <>
                    Send Login Code
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handlePasswordSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password from Email
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="Enter password from email"
                    required
                  />
                </div>
                <p className="mt-2 text-sm text-gray-600">
                  Check your email ({email}) for the login password
                </p>
              </div>
              
              <div className="space-y-3">
                <button
                  type="submit"
                  disabled={loading || !password.trim()}
                  className="w-full flex items-center justify-center px-4 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? (
                    <LoadingSpinner size="sm" text="" />
                  ) : (
                    <>
                      Sign In
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </button>
                
                <button
                  type="button"
                  onClick={resetToEmail}
                  className="w-full px-4 py-2 text-primary-600 hover:text-primary-700 text-sm"
                >
                  Use different email
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Info */}
        <div className="text-center text-sm text-gray-600">
          <p>We'll send you a secure password via email</p>
          <p className="mt-1">No account needed - just your email!</p>
        </div>
      </div>
    </div>
  )
}

export default Login