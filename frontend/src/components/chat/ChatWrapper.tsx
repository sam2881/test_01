'use client';

import { useChatContext } from '@/contexts/ChatContext';
import FloatingChat from './FloatingChat';

interface ChatWrapperProps {
  apiBase?: string;
}

export default function ChatWrapper({ apiBase = 'http://136.119.70.195:8000' }: ChatWrapperProps) {
  const { currentIncident } = useChatContext();

  return (
    <FloatingChat
      apiBase={apiBase}
      currentIncident={currentIncident || undefined}
    />
  );
}
