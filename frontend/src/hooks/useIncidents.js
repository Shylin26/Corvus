import { useEffect } from 'react'
import useStore from '../store'
import { useSSE } from './useSSE'

const GATEWAY = 'http://localhost:8000'

export function useIncidents() {
  const { setIncidents, setPendingApprovals } = useStore()

  useSSE(`${GATEWAY}/stream/incidents`, (data) => {
    setIncidents(data)
  })

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${GATEWAY}/approvals/pending`)
        const data = await r.json()
        setPendingApprovals(data)
      } catch {}
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => clearInterval(interval)
  }, [])
}
