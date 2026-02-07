import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, Database, MessageSquare, User, Bot } from 'lucide-react'
import './App.css'

// En dev : localhost:8000 | En Docker : Nginx proxy sur /api
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

interface Message {
  id: number
  role: 'user' | 'bot'
  content: string
  error?: boolean
  timestamp: Date
}

const SUGGESTIONS = [
  { label: 'Clients', text: 'Combien de clients actifs sont dans chaque ville ?' },
  { label: 'Chiffre d\'affaires', text: 'Quel est le chiffre d\'affaires total ?' },
  { label: 'Top produits', text: 'Quels sont les 5 produits les plus vendus ?' },
  { label: 'Commandes', text: 'Quelles sont les commandes de Marie Dupont ?' },
]

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [online, setOnline] = useState(true)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll on new message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Check API health
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text.trim() }),
      })

      const data = await res.json()

      const botMsg: Message = {
        id: Date.now() + 1,
        role: 'bot',
        content: data.response || data.error || 'Pas de réponse.',
        error: !res.ok || !!data.error,
        timestamp: new Date(),
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

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="header-icon">
            <Database size={22} />
          </div>
          <div>
            <div className="header-title">AI Data Assistant</div>
            <div className="header-subtitle">Text-to-SQL avec RAG</div>
          </div>
        </div>
        <div className="header-status">
          <span className={`status-dot ${online ? '' : 'offline'}`} />
          {online ? 'En ligne' : 'Hors ligne'}
        </div>
      </header>

      {/* Chat Area */}
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
              <div
                key={msg.id}
                className={`message ${msg.role}${msg.error ? ' error' : ''}`}
              >
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

      {/* Input Area */}
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
    </div>
  )
}

export default App
