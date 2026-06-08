import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { API_URL } from '../context/AuthContext'
import { Save, Mail, Bell, User } from 'lucide-react'

export default function Settings() {
  const { token, user } = useAuth()
  const [config, setConfig] = useState({ gmail_address: '', gmail_app_password: '', telegram_chat_id: '' })
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    axios.get(`${API_URL}/api/auth/config/email`, { headers })
      .then(r => setConfig(c => ({ ...c, ...r.data })))
      .catch(() => {})
  }, [])

  const saveConfig = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMsg('')
    try {
      await axios.post(`${API_URL}/api/auth/config/email`, config, { headers })
      setMsg('✓ Settings saved')
    } catch (e) {
      setMsg('✗ ' + (e.response?.data?.detail || 'Save failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '22px', fontWeight: '700' }}>Settings</h1>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '2px' }}>Configure your email and notification settings</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1.25rem' }}>
            <User size={16} color="var(--accent-light)" />
            <span style={{ fontSize: '14px', fontWeight: '600' }}>Account</span>
          </div>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input className="form-input" value={user?.full_name || ''} readOnly style={{ opacity: 0.7 }} />
          </div>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input className="form-input" value={user?.email || ''} readOnly style={{ opacity: 0.7 }} />
          </div>
        </div>

        <form onSubmit={saveConfig}>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1.25rem' }}>
              <Mail size={16} color="var(--accent-light)" />
              <span style={{ fontSize: '14px', fontWeight: '600' }}>Gmail Configuration</span>
            </div>
            <div className="form-group">
              <label className="form-label">Gmail Address</label>
              <input className="form-input" type="email" placeholder="your@gmail.com"
                value={config.gmail_address}
                onChange={e => setConfig({ ...config, gmail_address: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Gmail App Password</label>
              <input className="form-input" type="password" placeholder="xxxx xxxx xxxx xxxx"
                value={config.gmail_app_password}
                onChange={e => setConfig({ ...config, gmail_app_password: e.target.value })} />
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Generate at myaccount.google.com → Security → App Passwords
              </p>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1.25rem' }}>
              <Bell size={16} color="var(--accent-light)" />
              <span style={{ fontSize: '14px', fontWeight: '600' }}>Telegram Notifications</span>
            </div>
            <div className="form-group">
              <label className="form-label">Telegram Chat ID</label>
              <input className="form-input" placeholder="Your Telegram chat ID"
                value={config.telegram_chat_id}
                onChange={e => setConfig({ ...config, telegram_chat_id: e.target.value })} />
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Message @userinfobot on Telegram to get your chat ID
              </p>
            </div>

            {msg && <div className={`alert ${msg.startsWith('✓') ? 'alert-success' : 'alert-error'}`}>{msg}</div>}

            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? <span className="spinner" /> : <Save size={15} />}
              {loading ? 'Saving...' : 'Save settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
