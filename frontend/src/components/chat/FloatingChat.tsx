'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Minimize2, Maximize2, MessageCircle, X, ChevronDown, ChevronUp, Database, GitBranch } from 'lucide-react';

interface ChatMessage {
  id: string;
  content: string;
  type: 'user' | 'assistant';
  timestamp: Date;
}

interface RAGIncident {
  title: string;
  description?: string;
  category?: string;
  resolution?: string;
  distance?: number;
}

interface RAGResults {
  vector_results?: RAGIncident[];
  graph_results?: RAGIncident[];
}

interface ChatResponse {
  response: string;
  context: {
    vector_db_count: number;
    graph_db_count: number;
  };
  rag_results?: RAGResults;
}

interface CurrentIncident {
  incident_id?: string;
  short_description?: string;
  description?: string;
  category?: string;
  priority?: string;
  state?: string;
}

interface FloatingChatProps {
  issueId?: string;
  issueTitle?: string;
  apiBase?: string;
  currentIncident?: CurrentIncident;
}

export default function FloatingChat({
  issueId,
  issueTitle,
  apiBase = 'http://localhost:8000',
  currentIncident
}: FloatingChatProps) {
  const [isMinimized, setIsMinimized] = useState(true);
  const [isMaximized, setIsMaximized] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('Ready');
  const [ragResults, setRagResults] = useState<RAGResults>({});
  const [showRagPanel, setShowRagPanel] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const vectorCount = ragResults.vector_results?.length || 0;
  const graphCount = ragResults.graph_results?.length || 0;
  const hasRagResults = vectorCount > 0 || graphCount > 0;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    const message = inputValue.trim();
    if (!message || isLoading) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: message,
      type: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setStatus('Thinking...');

    try {
      // Build enriched message with current incident context
      let enrichedMessage = message;
      if (currentIncident) {
        enrichedMessage = `[Context: Currently viewing incident ${currentIncident.incident_id || 'unknown'} - "${currentIncident.short_description || 'No description'}". Category: ${currentIncident.category || 'N/A'}, Priority: ${currentIncident.priority || 'N/A'}]\n\nUser question: ${message}`;
      }

      const response = await fetch(`${apiBase}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: enrichedMessage,
          issue_id: issueId || currentIncident?.incident_id
        })
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      const data: ChatResponse = await response.json();

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        type: 'assistant',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Update RAG results if available
      if (data.rag_results) {
        setRagResults(data.rag_results);
        setShowRagPanel(true); // Auto-show RAG panel when results arrive
      }

      setStatus('Ready');
    } catch (error) {
      console.error('Chat error:', error);

      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error. Please try again.',
        type: 'assistant',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
      setStatus('Error');

      setTimeout(() => setStatus('Ready'), 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
    setIsMaximized(false);
  };

  const toggleMaximize = () => {
    setIsMaximized(!isMaximized);
    setIsMinimized(false);
  };

  const createRagCard = (incident: RAGIncident, source: 'vector' | 'graph', index: number) => {
    const similarity = incident.distance !== undefined ? (1 - incident.distance) * 100 : 85;
    const bgColor = source === 'vector' ? 'bg-blue-900/30 border-blue-700' : 'bg-purple-900/30 border-purple-700';
    const iconColor = source === 'vector' ? 'text-blue-400' : 'text-purple-400';

    return (
      <div key={`${source}-${index}`} className={`${bgColor} border rounded-lg p-2 mb-2`}>
        <div className="flex items-start gap-2">
          {source === 'vector' ? (
            <Database className={`w-4 h-4 ${iconColor} mt-0.5 flex-shrink-0`} />
          ) : (
            <GitBranch className={`w-4 h-4 ${iconColor} mt-0.5 flex-shrink-0`} />
          )}
          <div className="flex-1 min-w-0">
            <div className="flex justify-between items-start gap-2">
              <span className="text-xs font-medium text-white truncate">
                {incident.title || 'Untitled'}
              </span>
              <span className={`text-xs ${iconColor} whitespace-nowrap`}>
                {similarity.toFixed(0)}%
              </span>
            </div>
            {incident.resolution && (
              <p className="text-xs text-gray-400 mt-1 line-clamp-1">
                ✓ {incident.resolution}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 transition-all duration-300 ${
        isMinimized
          ? 'w-72 h-14'
          : isMaximized
            ? 'w-[600px] h-[80vh]'
            : 'w-[420px] h-[650px]'
      } flex flex-col bg-gray-900 rounded-lg shadow-2xl border border-gray-700`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-gray-700 cursor-pointer bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-t-lg"
        onClick={toggleMinimize}
      >
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5" />
          <div>
            <h3 className="font-semibold text-sm">AI Assistant</h3>
            <p className="text-xs opacity-90">
              {currentIncident?.incident_id
                ? `Incident: ${currentIncident.incident_id}`
                : issueId
                  ? `Issue: ${issueTitle || issueId}`
                  : 'Ask me anything'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {hasRagResults && !isMinimized && (
            <span className="text-xs bg-white/20 px-2 py-1 rounded">
              {vectorCount}V {graphCount}G
            </span>
          )}
          {/* Minimize Button - More Visible */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleMinimize();
            }}
            className="p-1.5 hover:bg-white/20 rounded transition-colors bg-white/10"
            title={isMinimized ? "Expand chat" : "Minimize chat"}
          >
            {isMinimized ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {/* Maximize Button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleMaximize();
            }}
            className="p-1.5 hover:bg-white/20 rounded transition-colors"
            title={isMaximized ? "Restore size" : "Maximize"}
          >
            {isMaximized ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Chat Content - Hidden when minimized */}
      {!isMinimized && (
        <>
          {/* RAG Results Panel - At Top with Toggle */}
          {hasRagResults && (
            <div className="border-b border-gray-700">
              {/* Toggle Header */}
              <button
                onClick={() => setShowRagPanel(!showRagPanel)}
                className="w-full px-4 py-2 flex items-center justify-between bg-gray-800 hover:bg-gray-750 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white">📊 Similar Incidents</span>
                  <span className="text-xs text-gray-400">
                    ({vectorCount} from Vector DB, {graphCount} from Graph DB)
                  </span>
                </div>
                {showRagPanel ? (
                  <ChevronUp className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                )}
              </button>

              {/* Collapsible RAG Content */}
              {showRagPanel && (
                <div className="px-4 py-3 bg-gray-850 max-h-[200px] overflow-y-auto">
                  <div className="grid grid-cols-2 gap-3">
                    {/* Vector DB Results */}
                    <div>
                      <h4 className="text-xs font-medium text-blue-400 mb-2 flex items-center gap-1">
                        <Database className="w-3 h-3" /> Vector DB
                      </h4>
                      {ragResults.vector_results?.slice(0, 3).map((inc, i) =>
                        createRagCard(inc, 'vector', i)
                      )}
                      {vectorCount === 0 && (
                        <p className="text-xs text-gray-500">No results</p>
                      )}
                    </div>

                    {/* Graph DB Results */}
                    <div>
                      <h4 className="text-xs font-medium text-purple-400 mb-2 flex items-center gap-1">
                        <GitBranch className="w-3 h-3" /> Graph DB
                      </h4>
                      {ragResults.graph_results?.slice(0, 3).map((inc, i) =>
                        createRagCard(inc, 'graph', i)
                      )}
                      {graphCount === 0 && (
                        <p className="text-xs text-gray-500">No results</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Current Incident Context Banner */}
          {currentIncident && (
            <div className="px-4 py-2 bg-yellow-900/30 border-b border-yellow-700/50">
              <p className="text-xs text-yellow-300">
                <span className="font-medium">Context:</span> {currentIncident.incident_id} - {currentIncident.short_description?.substring(0, 50)}...
              </p>
            </div>
          )}

          {/* Status Bar */}
          <div className="px-4 py-2 bg-gray-800 border-b border-gray-700 flex justify-between items-center">
            <div className="text-xs text-gray-400">
              Status: <span className={`font-medium ${status === 'Ready' ? 'text-green-400' : status === 'Error' ? 'text-red-400' : 'text-blue-400'}`}>
                {status}
              </span>
            </div>
          </div>

          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 mt-8">
                <MessageCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Start a conversation!</p>
                <p className="text-xs mt-1">
                  {currentIncident
                    ? `Ask about incident ${currentIncident.incident_id}`
                    : 'Ask me anything about incidents or issues.'}
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-4 py-2 ${
                    msg.type === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-100'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  <p className="text-xs opacity-70 mt-1">
                    {msg.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-800 rounded-lg px-4 py-3">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-gray-700 bg-gray-800">
            <div className="flex gap-2">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={currentIncident
                  ? `Ask about ${currentIncident.incident_id}...`
                  : "Type your message..."}
                className="flex-1 px-3 py-2 border border-gray-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-700 text-white placeholder-gray-400"
                rows={2}
                disabled={isLoading}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
