import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Line, getElementAtEvent } from 'react-chartjs-2'
import { Bot, Youtube, Activity, Send, Search, AlertTriangle, User, X, Clock, ExternalLink } from 'lucide-react'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const API_URL = 'http://localhost:8000/api'

function App() {
  const [activeTab, setActiveTab] = useState('videos') // 'videos' | 'users'
  const [videos, setVideos] = useState([])
  const [selectedVideo, setSelectedVideo] = useState(null)
  const [chartData, setChartData] = useState(null)

  const [riskyUsers, setRiskyUsers] = useState([])
  const [userSearch, setUserSearch] = useState('')

  // Drill Down / Modal States
  const [selectedUser, setSelectedUser] = useState(null) // For User Details Modal
  const [selectedHour, setSelectedHour] = useState(null) // For Activity Drill-down
  const [showAbout, setShowAbout] = useState(false)
  const [hourlyActivity, setHourlyActivity] = useState([])
  const [loadingActivity, setLoadingActivity] = useState(false)

  const [messages, setMessages] = useState([
    { role: 'agent', text: 'Social Media Fraud Detection Agent Online. How can I help?' }
  ])
  const [input, setInput] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const messagesEndRef = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    // Fetch videos on mount
    axios.get(`${API_URL}/videos`).then(res => {
      setVideos(res.data)
      const v20 = res.data.find(v => v.id == 20)
      if (v20) handleSelectVideo(20)
      else if (res.data.length > 0) handleSelectVideo(res.data[0].id)
    }).catch(err => console.error(err))

    fetchRiskyUsers()
  }, [])

  const fetchRiskyUsers = (search = null) => {
    let url = `${API_URL}/users/risk?limit=50`
    if (search) url += `&search=${search}`
    axios.get(url).then(res => setRiskyUsers(res.data))
  }

  const fetchUserDetails = (username) => {
    axios.get(`${API_URL}/users/${username}`).then(res => {
      setSelectedUser(res.data)
    }).catch(err => alert("User not found"))
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSelectVideo = (id) => {
    const v = videos.find(v => v.id == id)
    setSelectedVideo(v)

    axios.get(`${API_URL}/likes/${id}`).then(res => {
      setChartData({
        labels: res.data.labels,
        datasets: [
          {
            label: 'Likes Activity',
            data: res.data.data,
            borderColor: '#22d3ee',
            backgroundColor: 'rgba(34, 211, 238, 0.1)',
            tension: 0.3,
            fill: true,
            pointRadius: 4,
            pointHoverRadius: 6
          }
        ]
      })
    })
  }

  const handleChartClick = (event) => {
    if (!chartRef.current) return
    const points = getElementAtEvent(chartRef.current, event)
    if (points.length > 0) {
      const index = points[0].index
      const hourLabel = chartData.labels[index] // "YYYY-MM-DD HH:00"

      // Convert label "2025-12-06 14:00" -> format "YYYY-MM-DD HH" for API
      const apiHour = hourLabel.substring(0, 13)

      setSelectedHour(hourLabel)
      setLoadingActivity(true)

      axios.get(`${API_URL}/activity?video_id=${selectedVideo.id}&hour=${apiHour}`)
        .then(res => {
          setHourlyActivity(res.data)
          setLoadingActivity(false)
        })
        .catch(err => {
          console.error(err)
          setLoadingActivity(false)
        })
    }
  }

  const sendMessage = async () => {
    if (!input.trim()) return
    const msg = input
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: msg }])
    setAnalyzing(true)

    try {
      const res = await axios.post(`${API_URL}/chat`, { message: msg })
      setMessages(prev => [...prev, { role: 'agent', text: res.data.response }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'agent', text: 'Connection Error.' }])
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="layout">
      {/* Sidebar */}
      <div className="sidebar" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
          <img src="/logo.png" style={{ width: '40px', height: '40px', borderRadius: '8px', border: '1px solid var(--accent-cyan)' }} alt="Logo" />
          <div>
            <h2 style={{ fontSize: '1rem', lineHeight: '1.2', margin: 0, color: '#e2e8f0' }}>Social Media<br /><span style={{ color: 'var(--accent-cyan)' }}>Fraud Agent</span></h2>
          </div>
        </div>

        <div className="nav-tabs" style={{ display: 'flex', gap: '5px', marginBottom: '1rem' }}>
          <button
            style={{
              flex: 1,
              background: activeTab === 'videos' ? 'var(--accent-cyan)' : 'transparent',
              color: activeTab === 'videos' ? '#0f172a' : 'white',
              border: '1px solid var(--accent-cyan)',
              fontWeight: 'bold'
            }}
            onClick={() => setActiveTab('videos')}
          >
            Videos
          </button>
          <button
            style={{
              flex: 1,
              background: activeTab === 'users' ? 'var(--accent-cyan)' : 'transparent',
              color: activeTab === 'users' ? '#0f172a' : 'white',
              border: '1px solid var(--accent-cyan)',
              fontWeight: 'bold'
            }}
            onClick={() => setActiveTab('users')}
          >
            Users
          </button>
        </div>

        {activeTab === 'videos' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', overflowY: 'auto', flex: 1 }}>
            <h3 style={{ fontSize: '0.8rem', opacity: 0.7, textTransform: 'uppercase' }}>Recent Uploads</h3>
            {videos.map(v => (
              <button
                key={v.id}
                onClick={() => handleSelectVideo(v.id)}
                style={{
                  textAlign: 'left', fontSize: '0.9rem',
                  backgroundColor: selectedVideo?.id === v.id ? 'rgba(34, 211, 238, 0.2)' : 'transparent',
                  border: selectedVideo?.id === v.id ? '1px solid var(--accent-cyan)' : '1px solid transparent',
                  padding: '10px'
                }}
              >
                <Youtube size={14} style={{ marginRight: '5px', verticalAlign: 'middle' }} />
                {v.title}
                {v.id === 20 && <Activity size={12} color="#f43f5e" style={{ float: 'right' }} />}
              </button>
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', overflowY: 'auto', flex: 1 }}>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: '#94a3b8' }} />
              <input
                placeholder="Search User..."
                value={userSearch}
                onChange={e => { setUserSearch(e.target.value); fetchRiskyUsers(e.target.value) }}
                style={{ marginBottom: '0.5rem', width: '100%', paddingLeft: '30px' }}
              />
            </div>

            <h3 style={{ fontSize: '0.8rem', opacity: 0.7, textTransform: 'uppercase' }}>Flagged Accounts</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {riskyUsers.map(u => (
                <div key={u.id}
                  onClick={() => fetchUserDetails(u.username)}
                  style={{
                    padding: '10px', border: '1px solid #334155', borderRadius: '4px',
                    background: u.risk_score > 40 ? 'rgba(244, 63, 94, 0.1)' : 'transparent',
                    cursor: 'pointer', transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent-cyan)'}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = '#334155'}
                >
                  <div style={{ fontWeight: 'bold', fontSize: '0.9rem', display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    {u.username}
                    {u.risk_score > 40 && <AlertTriangle size={14} color="#f43f5e" />}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: u.risk_score > 40 ? '#f43f5e' : '#94a3b8' }}>
                    Alert: {u.alert_reason}
                  </div>
                  <div style={{ fontSize: '0.7rem', opacity: 0.7, marginTop: '4px' }}>
                    Risk Score: {u.risk_score} | Likes: {u.total_likes}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer Link to About */}
        <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid #334155' }}>
          <button onClick={() => setShowAbout(true)} style={{ background: 'transparent', color: '#94a3b8', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer', border: 'none' }}>
            <AlertTriangle size={14} /> About Developer
          </button>
        </div>
      </div>

      {/* Main Stats */}
      <div className="main-content">
        {activeTab === 'videos' && selectedVideo ? (
          <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2><Activity size={24} style={{ marginRight: '10px', verticalAlign: 'middle', color: 'var(--accent-cyan)' }} />
                Analysis: {selectedVideo.title}
              </h2>
              <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
                <span style={{ marginRight: '15px' }}>ID: {selectedVideo.id}</span>
                <span>Archetype: {selectedVideo.archetype}</span>
              </div>
            </div>
            <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
              <span style={{ color: 'var(--accent-cyan)' }}>Tip:</span> Click on data points to drill down into activity for that hour.
            </p>
            <div className="chart-container" style={{ flex: 1, minHeight: 0 }}>
              {chartData && <Line
                ref={chartRef}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  onClick: handleChartClick,
                  scales: {
                    y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                    x: { grid: { display: false }, ticks: { color: '#94a3b8', maxTicksLimit: 12 } }
                  },
                  plugins: { legend: { display: false } },
                  interaction: { mode: 'index', intersect: false },
                  onHover: (event, chartElement) => {
                    event.native.target.style.cursor = chartElement[0] ? 'pointer' : 'default';
                  }
                }}
                data={chartData}
              />}
            </div>
          </div>
        ) : activeTab === 'users' && (
          <div className="card" style={{ height: '100%', overflowY: 'auto' }}>
            <h2>User Risk Explorer</h2>
            <p>Detected {riskyUsers.length} users with anomalous behavior.</p>

            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155', textAlign: 'left' }}>
                  <th style={{ padding: '10px' }}>Username</th>
                  <th style={{ padding: '10px' }}>Alert</th>
                  <th style={{ padding: '10px' }}>Risk Score</th>
                  <th style={{ padding: '10px' }}>Joined</th>
                  <th style={{ padding: '10px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {riskyUsers.map(u => (
                  <tr key={u.id} style={{ borderBottom: '1px solid #1e293b' }}>
                    <td style={{ padding: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <User size={16} color={u.is_bot ? '#f43f5e' : '#94a3b8'} />
                        {u.username}
                      </div>
                    </td>
                    <td style={{ padding: '10px' }}>
                      <span style={{
                        background: u.alert_reason === 'Normal' ? '#0f172a' : 'rgba(244,63,94,0.2)',
                        color: u.alert_reason === 'Normal' ? '#94a3b8' : '#f43f5e',
                        padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem'
                      }}>
                        {u.alert_reason}
                      </span>
                    </td>
                    <td style={{ padding: '10px', color: u.risk_score > 50 ? '#f43f5e' : 'white', fontWeight: 'bold' }}>{u.risk_score}</td>
                    <td style={{ padding: '10px', color: '#94a3b8' }}>{u.created_at.substring(0, 10)}</td>
                    <td style={{ padding: '10px' }}>
                      <button
                        onClick={() => fetchUserDetails(u.username)}
                        style={{ fontSize: '0.8rem', padding: '4px 10px', background: 'transparent', border: '1px solid var(--accent-cyan)', color: 'var(--accent-cyan)' }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Chat Panel */}
      <div className="chat-panel">
        <h3><Bot size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }} /> Security Ops</h3>
        <div className="chat-messages">
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              {m.text}
            </div>
          ))}
          {analyzing && <div className="spinner">Analyst is typing...</div>}
          <div ref={messagesEndRef} />
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder="Ask anything (e.g. 'Who liked video 5?')"
            style={{ flex: 1 }}
          />
          <button onClick={sendMessage}><Send size={16} /></button>
        </div>
      </div>

      {/* MODAL: User Details */}
      {selectedUser && (
        <div className="modal-overlay" onClick={() => setSelectedUser(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2>User Analysis</h2>
              <button onClick={() => setSelectedUser(null)} style={{ background: 'transparent', color: 'white', fontSize: '1.2rem' }}><X /></button>
            </div>

            <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1.5rem' }}>
              <img
                src={selectedUser.profile?.avatar || `https://api.dicebear.com/7.x/identicon/svg?seed=${selectedUser.username}`}
                style={{ width: '80px', height: '80px', borderRadius: '12px', border: '2px solid #334155' }}
              />
              <div style={{ flex: 1 }}>
                <h2 style={{ margin: 0, fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {selectedUser.username}
                  {selectedUser.is_bot && <span style={{ fontSize: '0.7rem', background: '#f43f5e', padding: '2px 8px', borderRadius: '12px', verticalAlign: 'middle' }}>FLAGGED</span>}
                </h2>
                <div style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '5px' }}>{selectedUser.profile?.bio || "Social Media User"}</div>

                <div style={{ display: 'flex', gap: '15px', marginTop: '10px', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <span><b>{selectedUser.profile?.followers?.toLocaleString() || 0}</b> Followers</span>
                  <span><b>{selectedUser.profile?.following?.toLocaleString() || 0}</b> Following</span>
                  <span>{selectedUser.profile?.location || "Unknown"}</span>
                </div>
              </div>
            </div>

            <div style={{ background: 'rgba(244, 63, 94, 0.1)', borderLeft: '3px solid #f43f5e', padding: '1rem', marginBottom: '1.5rem', borderRadius: '0 4px 4px 0' }}>
              <h3 style={{ margin: '0 0 5px 0', fontSize: '1rem', color: '#f43f5e', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertTriangle size={16} /> Risk Analysis Narrative
              </h3>
              <p style={{ margin: 0, fontSize: '0.9rem', color: '#e2e8f0', lineHeight: '1.5' }}>
                {selectedUser.risk_narrative || "No specific anomalies detected."}
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div style={{ background: '#0f172a', padding: '10px', borderRadius: '6px' }}>
                <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Account Created</div>
                <div>{selectedUser.created_at.replace('T', ' ')}</div>
              </div>
              <div style={{ background: '#0f172a', padding: '10px', borderRadius: '6px' }}>
                <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Total Engagement</div>
                <div>{selectedUser.total_likes} Likes</div>
              </div>
            </div>

            <h3>Recent Activity Trace</h3>
            <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid #334155', borderRadius: '6px' }}>
              <table style={{ width: '100%', fontSize: '0.85rem' }}>
                <tbody style={{ background: '#0f172a' }}>
                  {selectedUser.recent_activity.map((act, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #1e293b' }}>
                      <td style={{ padding: '8px' }}><Activity size={14} style={{ marginRight: '5px', verticalAlign: 'middle' }} /> {act.title}</td>
                      <td style={{ padding: '8px', textAlign: 'right', color: '#94a3b8', fontFamily: 'monospace' }}>{act.timestamp.substring(5, 16).replace('T', ' ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ marginTop: '1.5rem', textAlign: 'right' }}>
              <button onClick={() => setSelectedUser(null)} style={{ background: '#334155', color: 'white', padding: '8px 16px', borderRadius: '4px', marginRight: '10px' }}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Activity Drill Down */}
      {selectedHour && (
        <div className="modal-overlay" onClick={() => setSelectedHour(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ width: '600px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2><Clock size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }} />Activity Log: {selectedHour}</h2>
              <button onClick={() => setSelectedHour(null)} style={{ background: 'transparent', color: 'white' }}><X /></button>
            </div>

            {loadingActivity ? (
              <div style={{ padding: '2rem', textAlign: 'center' }}>Loading forensics data...</div>
            ) : (
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                <p style={{ marginBottom: '1rem', color: '#94a3b8' }}>
                  Traffic breakdown for <b>{selectedVideo?.title}</b> during this hour.
                </p>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                  <thead style={{ position: 'sticky', top: 0, background: '#1e293b' }}>
                    <tr style={{ textAlign: 'left' }}>
                      <th style={{ padding: '8px' }}>User</th>
                      <th style={{ padding: '8px' }}>Analysis</th>
                      <th style={{ padding: '8px', textAlign: 'right' }}>Exact Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hourlyActivity.map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #334155' }}>
                        <td style={{ padding: '8px' }}>
                          <span
                            onClick={() => { setSelectedHour(null); fetchUserDetails(r.username); }}
                            style={{ cursor: 'pointer', color: 'var(--accent-cyan)', textDecoration: 'underline' }}
                          >
                            {r.username}
                          </span>
                        </td>
                        <td style={{ padding: '8px' }}>
                          {r.risk_label !== 'Normal' ? (
                            <span style={{ color: '#f43f5e', background: 'rgba(244,63,94,0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                              {r.risk_label}
                            </span>
                          ) : <span style={{ color: '#94a3b8' }}>Normal</span>}
                        </td>
                        <td style={{ padding: '8px', textAlign: 'right', fontFamily: 'monospace' }}>
                          {r.timestamp.substring(11, 19)}
                        </td>
                      </tr>
                    ))}
                    {hourlyActivity.length === 0 && (
                      <tr><td colSpan="3" style={{ padding: '20px', textAlign: 'center' }}>No activity recorded for this hour.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL: About */}
      {showAbout && (
        <div className="modal-overlay" onClick={() => setShowAbout(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <img src="/logo.png" style={{ width: '80px', height: '80px', borderRadius: '12px', marginBottom: '10px' }} />
              <h2 style={{ color: 'var(--accent-cyan)' }}>Social Media Fraud Detection Agent</h2>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Advanced Forensics & Bot Detection POC</p>
            </div>

            <div style={{ background: '#0f172a', padding: '1.5rem', borderRadius: '8px', border: '1px solid #334155' }}>
              <h3 style={{ marginTop: 0, fontSize: '1.1rem' }}>Developer: Patrick Siu</h3>
              <p style={{ fontSize: '0.9rem', color: '#cbd5e1', lineHeight: '1.5', margin: '0.5rem 0' }}>
                AI Product Developer <br />
                Specializing in Product Management, Data Engineering, Analytics, and Auditable AI
              </p>
              <div style={{ marginTop: '1rem' }}>
                <a href="https://www.linkedin.com/in/patrick-siu-65086a25/" target="_blank" rel="noreferrer"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', color: 'var(--accent-cyan)', textDecoration: 'none', fontWeight: 'bold' }}>
                  <ExternalLink size={16} /> Connect on LinkedIn
                </a>
              </div>
            </div>

            <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', color: '#64748b', textAlign: 'center' }}>
              Project built for demonstration purposes. <br />
              Utilizes Gemini Flash 2.5, FastAPI, and React.
            </div>

            <div style={{ marginTop: '1rem', textAlign: 'center' }}>
              <button onClick={() => setShowAbout(false)} style={{ background: '#334155', color: 'white', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer' }}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
