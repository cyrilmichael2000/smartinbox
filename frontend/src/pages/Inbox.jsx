import { useEffect, useState } from 'react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { API_URL } from '../context/AuthContext'
import { RefreshCw, Mail, Star, Trash2 } from 'lucide-react'

export default function Inbox() {
  const { token } = useAuth()
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('all')

  const headers = { Authorization: `Bearer ${token}` }

  const loadLogs = async () => {
    setLoading(true)
    try {
      const r = await axios.get(`${API_URL}/api/emails/logs`, { headers })
      setLogs(r.data.logs || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadLogs() }, [])

  const filtered = filter === 'all' ? logs
    : filter === 'important' ? logs.filter(l => l.important)
    : filter === 'deleted' ? logs.filter(l => l.action_taken === 'deleted')
    : logs.filter(l => l.category === filter)

  const filters = [
    { key: 'all', label: 'All' },
    { key: 'important', label: '⭐ Important' },
    { key: 'job', label: '💼 Job' },
    { key: 'immigration', label: '🛂 Immigration' },
    { key: 'finance', label: '💰 Finance' },
    { key: 'university', label: '🎓 University' },
    { key: 'spam', label: '🚫 Spam' },
    { key: 'deleted', label: '🗑 Deleted' },
  ]

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: '700' }}>Inbox</h1>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '2px' }}>All processed emails</p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadLogs} disabled={loading}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        {filters.map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className="btn btn-sm"
            style={{
              background: filter === f.key ? 'var(--accent-dim)' : 'var(--bg-card)',
              color: filter === f.key ? 'var(--accent-light)' : 'var(--text-secondary)',
              border: `1px solid ${filter === f.key ? 'var(--accent)' : 'var(--border)'}`,
            }}>
            {f.label}
          </button>
        ))}
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <span className="spinner" style={{ borderTopColor: 'var(--accent)' }} />
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>
            No emails found
          </div>
        ) : filtered.map((log, i) => (
          <div key={log.id} style={{
            display: 'flex', alignItems: 'flex-start', gap: '1rem',
            padding: '1rem 1.5rem',
            borderBottom: i < filtered.length - 1 ? '1px solid var(--border)' : 'none',
          }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '8px', flexShrink: 0,
              background: log.important ? 'rgba(245,158,11,0.15)' : 'var(--bg-hover)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              {log.important ? <Star size={16} color="var(--warning)" /> : <Mail size={16} color="var(--text-muted)" />}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
                <span style={{ fontSize: '14px', fontWeight: '500', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {log.subject || 'No subject'}
                </span>
                <span className={`badge badge-${log.category}`} style={{ flexShrink: 0 }}>{log.category}</span>
                {log.action_taken === 'deleted' && (
                  <span style={{ fontSize: '12px', color: 'var(--danger)', flexShrink: 0, display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <Trash2 size={11} /> deleted
                  </span>
                )}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {log.sender}
              </div>
              {log.summary && (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {log.summary}
                </div>
              )}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', flexShrink: 0 }}>
              {new Date(log.created_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
