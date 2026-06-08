import { useEffect, useState } from 'react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { API_URL } from '../context/AuthContext'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { Mail, Trash2, Star, RefreshCw, Play } from 'lucide-react'

const COLORS = {
  job: '#6366f1', immigration: '#10b981', finance: '#f59e0b',
  university: '#3b82f6', spam: '#ef4444', personal: '#94a3b8'
}

export default function Dashboard() {
  const { token } = useAuth()
  const [stats, setStats] = useState([])
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [msg, setMsg] = useState('')

  const headers = { Authorization: `Bearer ${token}` }

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsR, logsR] = await Promise.all([
        axios.get(`${API_URL}/api/emails/stats`, { headers }),
        axios.get(`${API_URL}/api/emails/logs`, { headers })
      ])
      setStats(statsR.data.stats || [])
      setLogs(logsR.data.logs || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const fetchEmails = async () => {
    setFetching(true)
    setMsg('')
    try {
      const r = await axios.post(`${API_URL}/api/emails/fetch`, {}, { headers })
      setMsg(`✓ Fetched ${r.data.fetched} emails`)
      setTimeout(loadData, 2000)
    } catch (e) {
      setMsg('✗ ' + (e.response?.data?.detail || 'Fetch failed'))
    } finally {
      setFetching(false)
    }
  }

  const runScheduler = async () => {
    try {
      await axios.post(`${API_URL}/api/scheduler/run-now`, {}, { headers })
      setMsg('✓ Scheduler triggered')
    } catch (e) {
      setMsg('✗ Scheduler failed')
    }
  }

  useEffect(() => { loadData() }, [])

  const total = logs.length
  const important = logs.filter(l => l.important).length
  const deleted = logs.filter(l => l.action_taken === 'deleted').length

  const pieData = stats.map(s => ({ name: s.category, value: Number(s.count) }))
  const barData = ['job','immigration','finance','university','spam','personal'].map(cat => ({
    category: cat, count: logs.filter(l => l.category === cat).length
  })).filter(d => d.count > 0)

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: '700' }}>Dashboard</h1>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '2px' }}>Your inbox intelligence overview</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {msg && <span style={{ fontSize: '13px', color: msg.startsWith('✓') ? 'var(--success)' : 'var(--danger)' }}>{msg}</span>}
          <button className="btn btn-secondary btn-sm" onClick={runScheduler}><Play size={14} /> Run scheduler</button>
          <button className="btn btn-secondary btn-sm" onClick={loadData} disabled={loading}><RefreshCw size={14} /></button>
          <button className="btn btn-primary" onClick={fetchEmails} disabled={fetching}>
            {fetching ? <span className="spinner" /> : <Mail size={15} />}
            {fetching ? 'Fetching...' : 'Fetch emails'}
          </button>
        </div>
      </div>

      <div className="stats-grid">
        {[
          { label: 'Total Processed', value: total, icon: <Mail size={18} />, color: 'var(--accent)', bg: 'var(--accent-dim)' },
          { label: 'Important', value: important, icon: <Star size={18} />, color: 'var(--warning)', bg: 'rgba(245,158,11,0.15)' },
          { label: 'Auto Deleted', value: deleted, icon: <Trash2 size={18} />, color: 'var(--danger)', bg: 'rgba(239,68,68,0.15)' },
          { label: 'Categories', value: stats.length, icon: <RefreshCw size={18} />, color: 'var(--success)', bg: 'rgba(16,185,129,0.15)' },
        ].map(({ label, value, icon, color, bg }) => (
          <div className="stat-card" key={label}>
            <div className="stat-icon" style={{ background: bg, color }}>{icon}</div>
            <div className="stat-value" style={{ color }}>{value}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
        <div className="card">
          <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '1rem' }}>Email Categories</div>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {pieData.map((entry) => <Cell key={entry.name} fill={COLORS[entry.name] || '#6366f1'} />)}
                </Pie>
                <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>No data yet — fetch some emails</div>}
        </div>

        <div className="card">
          <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '1rem' }}>Volume by Category</div>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="category" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '8px' }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {barData.map((entry) => <Cell key={entry.category} fill={COLORS[entry.category] || '#6366f1'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>No data yet</div>}
        </div>
      </div>

      <div className="card">
        <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '1rem' }}>Recent Activity</div>
        {logs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '14px' }}>
            No emails processed yet. Click "Fetch emails" to start.
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>From</th>
                <th>Category</th>
                <th>Action</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {logs.slice(0, 10).map(log => (
                <tr key={log.id}>
                  <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.subject}</td>
                  <td style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.sender}</td>
                  <td><span className={`badge badge-${log.category}`}>{log.category}</span></td>
                  <td style={{ fontSize: '13px', color: log.action_taken === 'deleted' ? 'var(--danger)' : 'var(--success)' }}>{log.action_taken}</td>
                  <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{new Date(log.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
