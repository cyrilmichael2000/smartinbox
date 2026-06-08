import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Inbox from './pages/Inbox'
import Settings from './pages/Settings'
import Sidebar from './components/Sidebar'
import Navbar from './components/Navbar'

function PrivateLayout({ children }) {
  const { token } = useAuth()
  if (!token) return <Navigate to="/login" />
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-area">
        <Navbar />
        <div className="page-content">{children}</div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<PrivateLayout><Dashboard /></PrivateLayout>} />
          <Route path="/inbox" element={<PrivateLayout><Inbox /></PrivateLayout>} />
          <Route path="/settings" element={<PrivateLayout><Settings /></PrivateLayout>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
