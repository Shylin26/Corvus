import { useState } from 'react'
import useStore from '../store'

const GATEWAY = 'http://localhost:8000'

export default function ChatInterface() {
  const [input, setInput]     = useState('')
  const [messages, setMessages] = useState([
    { role: 'system', text: 'Ask me anything about incidents. Try: "why was order-service restarted?" or "what caused the last incident?"' }
  ])
  const [loading, setLoading] = useState(false)
  const selectedId = useStore((s) => s.selectedId)

  const send = async () => {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: question }])
    setLoading(true)

    try {
      const r = await fetch(`${GATEWAY}/chat`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ question, incident_id: selectedId }),
      })
      const data = await r.json()
      setMessages((m) => [...m, {
        role: 'corvus',
        text: data.answer,
        trace_steps: data.trace_steps,
      }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'corvus', text: 'Error reaching gateway.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border border-border rounded flex flex-col h-80">
      <div className="text-xs text-muted tracking-widest uppercase px-3 py-2 border-b border-border">
        ▸ Ask Corvus
        {selectedId && (
          <span className="ml-2 text-blue text-xs">— {selectedId}</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
            {m.role === 'system' && (
              <p className="text-muted text-xs italic">{m.text}</p>
            )}
            {m.role === 'user' && (
              <span className="bg-dim text-text text-xs px-2 py-1 rounded inline-block max-w-xs text-left">
                {m.text}
              </span>
            )}
            {m.role === 'corvus' && (
              <div className="bg-surface border border-border rounded p-2">
                <div className="text-xs text-green mb-1">◈ CORVUS</div>
                <p className="text-text text-xs leading-relaxed">{m.text}</p>
                {m.trace_steps > 0 && (
                  <p className="text-muted text-xs mt-1">
                    {m.trace_steps} trace steps analysed
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="text-green text-xs animate-pulse">◈ thinking...</div>
        )}
      </div>

      <div className="border-t border-border flex">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask about an incident..."
          className="flex-1 bg-transparent text-text text-xs px-3 py-2 outline-none placeholder-muted font-mono"
        />
        <button
          onClick={send}
          disabled={loading}
          className="px-3 py-2 text-green text-xs border-l border-border hover:bg-dim disabled:opacity-50"
        >
          ↵
        </button>
      </div>
    </div>
  )
}
