import { useState, useEffect } from 'react'
import useStore from '../store'

const GATEWAY = 'http://localhost:8000'

export default function StatusBar() {
  const incidents = useStore((s) => s.incidents)
  const [health, setHealth] = useState(null)

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${GATEWAY}/health`)
        setHealth(await r.json())
      } catch {
        setHealth(null)
      }
    }
    poll()
    const i = setInterval(poll, 5000)
    return () => clearInterval(i)
  }, [])

  const resolved  = incidents.filter(i => i.status === 'RESOLVED').length
  const active    = incidents.filter(i => !['RESOLVED','ROLLED_BACK','FAILED'].includes(i.status)).length
  const failed    = incidents.filter(i => i.status === 'FAILED').length

  return (
    <div className="border border-border rounded p-3 space-y-2">
      <div className="text-xs text-muted tracking-widest uppercase mb-2">▸ System status</div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-bg rounded p-2">
          <div className="text-green text-lg font-display">{resolved}</div>
          <div className="text-muted text-xs">RESOLVED</div>
        </div>
        <div className="bg-bg rounded p-2">
          <div className={`text-lg font-display ${active > 0 ? 'text-amber' : 'text-muted'}`}>
            {active}
          </div>
          <div className="text-muted text-xs">ACTIVE</div>
        </div>
        <div className="bg-bg rounded p-2">
          <div className={`text-lg font-display ${failed > 0 ? 'text-red' : 'text-muted'}`}>
            {failed}
          </div>
          <div className="text-muted text-xs">FAILED</div>
        </div>
      </div>
      <div className="text-xs text-muted pt-1 border-t border-border">
        GATEWAY {health ? <span className="text-green">● ONLINE</span> : <span className="text-red">● OFFLINE</span>}
      </div>
    </div>
  )
}
