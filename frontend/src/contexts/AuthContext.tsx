import React, { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '../services/api'
import toast from 'react-hot-toast'

interface User {
  email: string
  access_token: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<boolean>
  requestLogin: (email: string) => Promise<boolean>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const email = localStorage.getItem('user_email')
    
    if (token && email) {
      setUser({ email, access_token: token })
    }
    setLoading(false)
  }, [])

  const requestLogin = async (email: string): Promise<boolean> => {
    try {
      const response = await authAPI.requestLogin(email)
      if (response.success) {
        toast.success('Login instructions sent to your email!')
        return true
      }
      return false
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to send login email')
      return false
    }
  }

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      const response = await authAPI.verifyPassword(email, password)
      if (response.success && response.access_token) {
        const userData = {
          email: response.email,
          access_token: response.access_token
        }
        
        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('user_email', response.email)
        setUser(userData)
        toast.success('Login successful!')
        return true
      }
      return false
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Login failed')
      return false
    }
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_email')
    setUser(null)
    toast.success('Logged out successfully')
  }

  const value = {
    user,
    loading,
    login,
    requestLogin,
    logout
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}