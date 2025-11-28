'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface CurrentIncident {
  incident_id?: string;
  short_description?: string;
  description?: string;
  category?: string;
  priority?: string;
  state?: string;
}

interface ChatContextType {
  currentIncident: CurrentIncident | null;
  setCurrentIncident: (incident: CurrentIncident | null) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [currentIncident, setCurrentIncident] = useState<CurrentIncident | null>(null);

  return (
    <ChatContext.Provider value={{ currentIncident, setCurrentIncident }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}
