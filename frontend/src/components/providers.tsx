'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode, useEffect, useState } from 'react'
import { wsClient } from '@/lib/websocket'
import { ChatProvider } from '@/contexts/ChatContext'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
})

export function Providers({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    // Connect WebSocket on mount
    wsClient.connect()

    return () => {
      // Disconnect WebSocket on unmount
      wsClient.disconnect()
    }
  }, [])

  if (!mounted) {
    return null
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ChatProvider>
        {children}
      </ChatProvider>
    </QueryClientProvider>
  )
}
