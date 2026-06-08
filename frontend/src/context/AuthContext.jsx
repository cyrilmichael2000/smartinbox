import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext()
const API = 'http://localhost:8000'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (token) {
      axios.get(`${API}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      }).then(r => setUser(r.data)).catch(() => logout())
    }
  }, [token])

  const login = async (email, password) => {
    const r = await axios.post(`${API}/api/auth/login`, { email, password })
    localStorage.setItem('token', r.data.token)
    setToken(r.data.token)
    setUser(r.data)
    return r.data
  }

  const register = async (email, password, full_name) => {
    const r = await axios.post(`${API}/api/auth/register`, { email, password, full_name })
    localStorage.setItem('token', r.data.token)
    setToken(r.data.token)
    setUser(r.data)
    return r.data
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
export const API_URL = API
