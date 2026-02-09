import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, Database, MessageSquare, User, Bot, History, Trash2, ArrowLeft, Copy, Check, Download, Sun, Moon, Code, LogOut, Mail, Lock, UserPlus, Shield, Users } from 'lucide-react'
import './App.css'

// En dev : localhost:8000 | En Docker : Nginx proxy sur /api
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

interface AuthUser {
  id: number
  username: string
  email: string
  role: string
  allowed_tables: string[]
}

interface AdminUser {
  id: number
  username: string
  email: string
  role: string
  allowed_tables: string[]
  created_at: string
}

interface Message {
  id: number
  role: 'user' | 'bot'
  content: string
  error?: boolean
  timestamp: Date
  sql_query?: string | null
}

interface HistoryItem {
  id: number
  session_id: string
  question: string
  response: string
  created_at: string
}

const SUGGESTIONS = [
  { label: 'Clients', text: 'Combien de clients actifs sont dans chaque ville ?' },
  { label: 'Chiffre d\'affaires', text: 'Quel est le chiffre d\'affaires total ?' },
  { label: 'Top produits', text: 'Quels sont les 5 produits les plus vendus ?' },
  { label: 'Commandes', text: 'Quelles sont les commandes de Marie Dupont ?' },
]

function generateSessionId(): string {
  return crypto.randomUUID()
}

function App() {
  // ── Auth state ──
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [authUser, setAuthUser] = useState<AuthUser | null>(() => {
    const stored = localStorage.getItem('user')
    return stored ? JSON.parse(stored) : null
  })
  const [view, setView] = useState<'login' | 'register' | 'chat' | 'history' | 'admin'>(() => {
    return localStorage.getItem('token') ? 'chat' : 'login'
  })
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)

  // ── Chat state ──
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [online, setOnline] = useState(true)
  const [sessionId] = useState(() => generateSessionId())
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const [showSqlId, setShowSqlId] = useState<number | null>(null)
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('theme') as 'dark' | 'light') || 'dark'
  })
  // ── Admin state ──
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([])
  const [adminLoading, setAdminLoading] = useState(false)
  const [adminError, setAdminError] = useState('')
  const [adminSuccess, setAdminSuccess] = useState('')

  const chatEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // ── Auth helpers ──
  const authHeaders = (): HeadersInit => ({
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  })

  const handleAuthError = (status: number) => {
    if (status === 401) {
      logout()
    }
  }

  const logout = () => {
    setToken(null)
    setAuthUser(null)
    setMessages([])
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setView('login')
  }

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault()
    setAuthError('')
    setAuthLoading(true)
    const form = e.target as HTMLFormElement
    const email = (form.elements.namedItem('email') as HTMLInputElement).value
    const password = (form.elements.namedItem('password') as HTMLInputElement).value

    try {
      const res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        setAuthError(data.detail || 'Erreur de connexion.')
        return
      }
      setToken(data.token)
      setAuthUser(data.user)
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
      setView('chat')
    } catch {
      setAuthError('Impossible de contacter le serveur.')
    } finally {
      setAuthLoading(false)
    }
  }

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault()
    setAuthError('')
    setAuthLoading(true)
    const form = e.target as HTMLFormElement
    const username = (form.elements.namedItem('username') as HTMLInputElement).value
    const email = (form.elements.namedItem('email') as HTMLInputElement).value
    const password = (form.elements.namedItem('password') as HTMLInputElement).value

    try {
      const res = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        setAuthError(data.detail || 'Erreur lors de l\'inscription.')
        return
      }
      setToken(data.token)
      setAuthUser(data.user)
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
      setView('chat')
    } catch {
      setAuthError('Impossible de contacter le serveur.')
    } finally {
      setAuthLoading(false)
    }
  }

  // ── Effects ──
  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Health check
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API_URL}/api/health`)
        setOnline(res.ok)
      } catch {
        setOnline(false)
      }
    }
    check()
    const interval = setInterval(check, 30000)
    return () => clearInterval(interval)
  }, [])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
    }
  }, [input])

  // Load history
  useEffect(() => {
    if (view === 'history' && token) {
      loadHistory()
    }
  }, [view])

  // Load admin users
  useEffect(() => {
    if (view === 'admin' && token) {
      loadAdminUsers()
    }
  }, [view])

  // ── API calls ──
  const loadHistory = async () => {
    setHistoryLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/history?limit=50`, { headers: authHeaders() })
      if (res.ok) {
        const data = await res.json()
        setHistory(data)
      } else {
        handleAuthError(res.status)
      }
    } catch {
      console.error('Erreur chargement historique')
    } finally {
      setHistoryLoading(false)
    }
  }

  const clearHistory = async () => {
    if (!confirm('Supprimer tout l\'historique ?')) return
    try {
      const res = await fetch(`${API_URL}/api/history`, { method: 'DELETE', headers: authHeaders() })
      if (res.ok) {
        setHistory([])
      } else {
        handleAuthError(res.status)
      }
    } catch {
      console.error('Erreur suppression historique')
    }
  }

  // ── Admin API calls ──
  const loadAdminUsers = async () => {
    setAdminLoading(true)
    setAdminError('')
    try {
      const res = await fetch(`${API_URL}/api/admin/users`, { headers: authHeaders() })
      if (res.ok) {
        const data = await res.json()
        setAdminUsers(data)
      } else if (res.status === 403) {
        setAdminError('Accès réservé aux administrateurs.')
      } else {
        handleAuthError(res.status)
      }
    } catch {
      setAdminError('Impossible de charger les utilisateurs.')
    } finally {
      setAdminLoading(false)
    }
  }

  const updateUserRole = async (userId: number, role: string) => {
    setAdminError('')
    setAdminSuccess('')
    try {
      const res = await fetch(`${API_URL}/api/admin/users/${userId}/role`, {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify({ role }),
      })
      if (res.ok) {
        setAdminSuccess('Rôle mis à jour avec succès.')
        setAdminUsers(prev => prev.map(u => u.id === userId ? { ...u, role } : u))
        setTimeout(() => setAdminSuccess(''), 3000)
      } else {
        const data = await res.json()
        setAdminError(data.detail || 'Erreur lors de la mise à jour du rôle.')
        setTimeout(() => setAdminError(''), 4000)
      }
    } catch {
      setAdminError('Impossible de mettre à jour le rôle.')
    }
  }

  const updateUserTables = async (userId: number, tables: string[]) => {
    setAdminError('')
    setAdminSuccess('')
    try {
      const res = await fetch(`${API_URL}/api/admin/users/${userId}/tables`, {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify({ allowed_tables: tables }),
      })
      if (res.ok) {
        setAdminSuccess('Tables autorisées mises à jour.')
        setAdminUsers(prev => prev.map(u => u.id === userId ? { ...u, allowed_tables: tables } : u))
        setTimeout(() => setAdminSuccess(''), 3000)
      } else {
        const data = await res.json()
        setAdminError(data.detail || 'Erreur lors de la mise à jour des tables.')
        setTimeout(() => setAdminError(''), 4000)
      }
    } catch {
      setAdminError('Impossible de mettre à jour les tables.')
    }
  }

  const toggleTable = (user: AdminUser, table: string) => {
    const current = user.allowed_tables || []
    const updated = current.includes(table)
      ? current.filter(t => t !== table)
      : [...current, table]
    if (updated.length === 0) {
      setAdminError('Au moins une table doit être autorisée.')
      setTimeout(() => setAdminError(''), 3000)
      return
    }
    updateUserTables(user.id, updated)
  }

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/api/ask`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ question: text.trim(), session_id: sessionId }),
      })

      if (res.status === 401) {
        handleAuthError(401)
        return
      }

      const data = await res.json()

      const botMsg: Message = {
        id: Date.now() + 1,
        role: 'bot',
        content: data.response || data.error || 'Pas de réponse.',
        error: !res.ok || !!data.error,
        timestamp: new Date(),
        sql_query: data.sql_query || null,
      }

      setMessages(prev => [...prev, botMsg])
    } catch {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'bot',
          content: 'Impossible de contacter le serveur. Vérifiez que le backend est démarré sur le port 8000.',
          error: true,
          timestamp: new Date(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const hasTable = (text: string) => text.includes('|') && text.includes('---')

  const exportCSV = (text: string) => {
    const lines = text.split('\n').filter(l => l.trim().startsWith('|'))
    if (lines.length < 2) return

    const csvRows = lines
      .filter(l => !l.includes('---'))
      .map(l =>
        l.split('|')
          .filter(cell => cell.trim() !== '')
          .map(cell => `"${cell.trim()}"`)
          .join(',')
      )

    const csv = csvRows.join('\n')
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `export_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const copyMessage = async (id: number, text: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr)
    return d.toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  }

  // ══════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════

  // ── VUE LOGIN ──
  if (view === 'login') {
    return (
      <div className="app">
        <div className="auth-container">
          <div className="auth-card">
            <div className="auth-header">
              <div className="auth-icon">
                <Database size={28} />
              </div>
              <h1 className="auth-title">AI Data Assistant</h1>
              <p className="auth-subtitle">Connectez-vous pour continuer</p>
            </div>
            <form onSubmit={handleLogin}>
              {authError && <div className="auth-error">{authError}</div>}
              <div className="auth-field">
                <Mail size={16} />
                <input name="email" type="email" placeholder="Email" required />
              </div>
              <div className="auth-field">
                <Lock size={16} />
                <input name="password" type="password" placeholder="Mot de passe" required />
              </div>
              <button type="submit" className="auth-btn" disabled={authLoading}>
                {authLoading ? 'Connexion...' : 'Se connecter'}
              </button>
            </form>
            <p className="auth-switch">
              Pas encore de compte ?{' '}
              <button onClick={() => { setView('register'); setAuthError('') }}>Créer un compte</button>
            </p>
          </div>
          <button className="auth-theme-toggle" onClick={toggleTheme} title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}>
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </div>
    )
  }

  // ── VUE REGISTER ──
  if (view === 'register') {
    return (
      <div className="app">
        <div className="auth-container">
          <div className="auth-card">
            <div className="auth-header">
              <div className="auth-icon">
                <UserPlus size={28} />
              </div>
              <h1 className="auth-title">Créer un compte</h1>
              <p className="auth-subtitle">Inscrivez-vous pour accéder au chatbot</p>
            </div>
            <form onSubmit={handleRegister}>
              {authError && <div className="auth-error">{authError}</div>}
              <div className="auth-field">
                <User size={16} />
                <input name="username" type="text" placeholder="Nom d'utilisateur (min. 3 car.)" required minLength={3} maxLength={50} />
              </div>
              <div className="auth-field">
                <Mail size={16} />
                <input name="email" type="email" placeholder="Email (ex: nom@domaine.com)" required maxLength={200} />
              </div>
              <div className="auth-field">
                <Lock size={16} />
                <input name="password" type="password" placeholder="Mot de passe" required minLength={8} maxLength={72} />
              </div>
              <div className="auth-password-rules">
                <span>Min. 8 car.</span>
                <span>1 majuscule</span>
                <span>1 minuscule</span>
                <span>1 chiffre</span>
                <span>1 spécial (!@#...)</span>
              </div>
              <button type="submit" className="auth-btn" disabled={authLoading}>
                {authLoading ? 'Inscription...' : 'S\'inscrire'}
              </button>
            </form>
            <p className="auth-switch">
              Déjà un compte ?{' '}
              <button onClick={() => { setView('login'); setAuthError('') }}>Se connecter</button>
            </p>
          </div>
          <button className="auth-theme-toggle" onClick={toggleTheme} title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}>
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </div>
    )
  }

  // ── VUE PRINCIPALE (CHAT + HISTORY) ──
  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          {view === 'history' || view === 'admin' ? (
            <button className="header-back-btn" onClick={() => setView('chat')} title="Retour au chat">
              <ArrowLeft size={20} />
            </button>
          ) : (
            <div className="header-icon">
              <Database size={22} />
            </div>
          )}
          <div>
            <div className="header-title">
              {view === 'chat' ? 'AI Data Assistant' : view === 'admin' ? 'Administration' : 'Historique'}
            </div>
            <div className="header-subtitle">
              {view === 'chat'
                ? `Connecté : ${authUser?.username || authUser?.email}`
                : view === 'admin'
                  ? `${adminUsers.length} utilisateur${adminUsers.length > 1 ? 's' : ''}`
                  : `${history.length} conversation${history.length > 1 ? 's' : ''}`
              }
            </div>
          </div>
        </div>
        <div className="header-actions">
          <button className="header-btn theme-toggle" onClick={toggleTheme} title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}>
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          {authUser?.role === 'admin' && view !== 'admin' && (
            <button className="header-btn admin-btn" onClick={() => setView('admin')} title="Administration">
              <Shield size={18} />
            </button>
          )}
          {view === 'chat' ? (
            <button className="header-btn" onClick={() => setView('history')} title="Historique">
              <History size={18} />
            </button>
          ) : view === 'history' ? (
            <button className="header-btn danger" onClick={clearHistory} title="Supprimer l'historique">
              <Trash2 size={18} />
            </button>
          ) : null}
          <button className="header-btn danger" onClick={logout} title="Déconnexion">
            <LogOut size={18} />
          </button>
          <div className="header-status">
            <span className={`status-dot ${online ? '' : 'offline'}`} />
            {online ? 'En ligne' : 'Hors ligne'}
          </div>
        </div>
      </header>

      {/* ── VUE CHAT ── */}
      {view === 'chat' && (
        <>
          <div className="chat-area">
            {messages.length === 0 ? (
              <div className="welcome">
                <div className="welcome-icon">
                  <MessageSquare size={36} />
                </div>
                <h2>Posez une question sur vos données</h2>
                <p>
                  Je transforme vos questions en requêtes SQL et vous retourne
                  les résultats en langage naturel. Essayez une suggestion ci-dessous !
                </p>
                <div className="suggestions">
                  {SUGGESTIONS.map((s, i) => (
                    <button
                      key={i}
                      className="suggestion-btn"
                      onClick={() => sendMessage(s.text)}
                    >
                      <span className="suggestion-label">{s.label}</span>
                      {s.text}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map(msg => (
                  <div key={msg.id} className={`message-wrapper ${msg.role}`}>
                    <div className={`message ${msg.role}${msg.error ? ' error' : ''}`}>
                      <div className="message-avatar">
                        {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                      </div>
                      <div className="message-content">
                        {msg.role === 'bot' ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                        ) : (
                          msg.content
                        )}
                      </div>
                      {msg.role === 'bot' && !msg.error && (
                        <div className="message-actions">
                          <button
                            className={`action-btn ${copiedId === msg.id ? 'copied' : ''}`}
                            onClick={() => copyMessage(msg.id, msg.content)}
                            title={copiedId === msg.id ? 'Copié !' : 'Copier'}
                          >
                            {copiedId === msg.id ? <Check size={14} /> : <Copy size={14} />}
                          </button>
                          {hasTable(msg.content) && (
                            <button
                              className="action-btn"
                              onClick={() => exportCSV(msg.content)}
                              title="Exporter en CSV"
                            >
                              <Download size={14} />
                            </button>
                          )}
                          {msg.sql_query && (
                            <button
                              className={`action-btn ${showSqlId === msg.id ? 'active' : ''}`}
                              onClick={() => setShowSqlId(showSqlId === msg.id ? null : msg.id)}
                              title={showSqlId === msg.id ? 'Masquer le SQL' : 'Voir le SQL'}
                            >
                              <Code size={14} />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                    {showSqlId === msg.id && msg.sql_query && (
                      <div className="sql-display">
                        <div className="sql-display-header">
                          <Code size={12} />
                          <span>Requête SQL</span>
                        </div>
                        <pre className="sql-display-code">{msg.sql_query}</pre>
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div className="message bot">
                    <div className="message-avatar">
                      <Bot size={16} />
                    </div>
                    <div className="message-content">
                      <div className="loading-dots">
                        <span />
                        <span />
                        <span />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={chatEndRef} />
          </div>

          <form className="input-area" onSubmit={handleSubmit}>
            <div className="input-container">
              <div className="input-wrapper">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Posez votre question sur les données..."
                  rows={1}
                  disabled={loading}
                />
              </div>
              <button
                type="submit"
                className="send-btn"
                disabled={!input.trim() || loading}
                title="Envoyer"
              >
                <Send size={20} />
              </button>
            </div>
            <div className="input-hint">
              Entrée pour envoyer &middot; Shift+Entrée pour un retour à la ligne
            </div>
          </form>
        </>
      )}

      {/* ── VUE HISTORIQUE ── */}
      {view === 'history' && (
        <div className="history-area">
          {historyLoading ? (
            <div className="history-loading">Chargement...</div>
          ) : history.length === 0 ? (
            <div className="history-empty">
              <History size={48} />
              <p>Aucun historique pour le moment.</p>
              <p className="history-empty-hint">Posez des questions et elles apparaîtront ici.</p>
            </div>
          ) : (
            <div className="history-list">
              {history.map(item => (
                <div key={item.id} className="history-item">
                  <div className="history-item-header">
                    <span className="history-date">{formatDate(item.created_at)}</span>
                  </div>
                  <div className="history-question">
                    <User size={14} />
                    <span>{item.question}</span>
                  </div>
                  <div className="history-response">
                    <Bot size={14} />
                    <div className="history-response-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.response}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── VUE ADMIN ── */}
      {view === 'admin' && (
        <div className="admin-area">
          {adminError && <div className="admin-alert error">{adminError}</div>}
          {adminSuccess && <div className="admin-alert success">{adminSuccess}</div>}

          {adminLoading ? (
            <div className="history-loading">Chargement des utilisateurs...</div>
          ) : adminUsers.length === 0 ? (
            <div className="history-empty">
              <Users size={48} />
              <p>Aucun utilisateur trouvé.</p>
            </div>
          ) : (
            <div className="admin-user-list">
              {adminUsers.map(u => (
                <div key={u.id} className="admin-user-card">
                  <div className="admin-user-header">
                    <div className="admin-user-info">
                      <div className="admin-user-avatar">
                        {u.username.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="admin-user-name">{u.username}</div>
                        <div className="admin-user-email">{u.email}</div>
                      </div>
                    </div>
                    <div className="admin-user-meta">
                      <span className={`admin-role-badge ${u.role}`}>
                        {u.role === 'admin' ? <Shield size={12} /> : <User size={12} />}
                        {u.role}
                      </span>
                      <span className="admin-user-date">
                        {formatDate(u.created_at)}
                      </span>
                    </div>
                  </div>

                  <div className="admin-user-controls">
                    <div className="admin-control-group">
                      <label className="admin-control-label">Rôle</label>
                      <select
                        className="admin-select"
                        value={u.role}
                        onChange={e => updateUserRole(u.id, e.target.value)}
                        disabled={u.id === authUser?.id}
                      >
                        <option value="user">Utilisateur</option>
                        <option value="admin">Administrateur</option>
                      </select>
                      {u.id === authUser?.id && (
                        <span className="admin-hint">Vous ne pouvez pas modifier votre propre rôle</span>
                      )}
                    </div>

                    <div className="admin-control-group">
                      <label className="admin-control-label">Tables autorisées</label>
                      {u.role === 'admin' ? (
                        <span className="admin-hint">Les admins ont accès à toutes les tables</span>
                      ) : (
                        <div className="admin-tables-checkboxes">
                          {['clients', 'produits', 'commandes'].map(table => (
                            <label key={table} className="admin-checkbox-label">
                              <input
                                type="checkbox"
                                checked={(u.allowed_tables || []).includes(table)}
                                onChange={() => toggleTable(u, table)}
                              />
                              <span className="admin-checkbox-text">{table}</span>
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default App
