import { useEffect } from 'react'

export function useSSE(url, onMessage) {
  useEffect(() => {
    const es = new EventSource(url)
    es.onmessage = (e) => {
      try {
        onMessage(JSON.parse(e.data))
      } catch {}
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [url])
}
