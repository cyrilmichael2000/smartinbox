import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { API_URL } from '../context/AuthContext'
import { Wifi, WifiOff } from 'lucide-react'

export default function Navbar() {
  const { token } = useAuth()
  const [queues, setQueues] = useState(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    if (!token) return
    const ws = new WebSocket(`ws://localhost:8000/ws/${token}`)
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.event === 'queue_update') setQueues(data)
    }
    return () => ws.close()
  }, [token])

  return (
    <div style={{
      height: '60px', background: 'var(--bg-secondary)',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 2rem'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: connected ? 'var(--success)' : 'var(--text-muted)' }}>
        {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
        {connected ? 'Live' : 'Connecting...'}
        {connected && <span className="live-dot" style={{ marginLeft: '2px' }} />}
      </div>

      {queues && (
        <div style={{ display: 'flex', gap: '1.5rem', fontSize: '12px', color: 'var(--text-secondary)' }}>
          <span>Email queue: <strong style={{ color: 'var(--text-primary)' }}>{queues.email_queue}</strong></span>
          <span>Action queue: <strong style={{ color: 'var(--text-primary)' }}>{queues.action_queue}</strong></span>
          <span>Notification queue: <strong style={{ color: 'var(--text-primary)' }}>{queues.notification_queue}</strong></span>
        </div>
      )}
    </div>
  )
}
