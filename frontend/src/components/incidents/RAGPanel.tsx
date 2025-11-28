'use client'

import { useState } from 'react'
import { Brain, TrendingUp, Clock, CheckCircle, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'

export interface SimilarIncident {
  incident_id: string
  short_description: string
  description: string
  category: string
  root_cause: string
  solution: string
  agent_used: string
  resolution_time: number
  priority: string
  similarity_score: number
  distance?: number
}

interface RAGPanelProps {
  similarIncidents: SimilarIncident[]
  isLoading?: boolean
}

export function RAGPanel({ similarIncidents, isLoading }: RAGPanelProps) {
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Brain className="w-5 h-5 text-purple-600 animate-pulse" />
          <h3 className="text-lg font-semibold text-gray-900">RAG Context Loading...</h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse bg-gray-100 rounded-lg h-24" />
          ))}
        </div>
      </div>
    )
  }

  if (!similarIncidents || similarIncidents.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Brain className="w-5 h-5 text-purple-600" />
          <h3 className="text-lg font-semibold text-gray-900">RAG Context</h3>
        </div>
        <p className="text-gray-500 text-center py-8">
          No similar incidents found in knowledge base
        </p>
      </div>
    )
  }

  const getSimilarityColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-100 text-green-800 border-green-200'
    if (score >= 0.6) return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    return 'bg-orange-100 text-orange-800 border-orange-200'
  }

  const getSimilarityLabel = (score: number) => {
    if (score >= 0.8) return 'High Match'
    if (score >= 0.6) return 'Medium Match'
    return 'Low Match'
  }

  return (
    <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg border-2 border-purple-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
            <Brain className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">RAG Context</h3>
            <p className="text-sm text-gray-600">
              Top {similarIncidents.length} similar incidents from vector database
            </p>
          </div>
        </div>
        <Badge className="bg-purple-100 text-purple-800 border-purple-200">
          Vector Search
        </Badge>
      </div>

      {/* Similar Incidents */}
      <div className="space-y-4">
        {similarIncidents.map((incident, index) => {
          const isExpanded = expandedIncident === incident.incident_id

          return (
            <div
              key={incident.incident_id}
              className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
            >
              {/* Incident Header */}
              <div className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
                      <span className="text-sm font-bold text-purple-600">{index + 1}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Link
                          href={`/incidents/${incident.incident_id}`}
                          className="font-medium text-gray-900 hover:text-purple-600 flex items-center gap-1"
                        >
                          {incident.incident_id}
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                        <Badge className={getSimilarityColor(incident.similarity_score)}>
                          {getSimilarityLabel(incident.similarity_score)}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600 line-clamp-2">
                        {incident.short_description}
                      </p>
                    </div>
                  </div>

                  {/* Similarity Score */}
                  <div className="flex-shrink-0 ml-4 text-right">
                    <div className="text-2xl font-bold text-purple-600">
                      {(incident.similarity_score * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-500">similarity</div>
                  </div>
                </div>

                {/* Quick Stats */}
                <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    <span>{incident.resolution_time}min</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <CheckCircle className="w-4 h-4" />
                    <span>{incident.agent_used}</span>
                  </div>
                  <Badge className="bg-gray-100 text-gray-700">
                    {incident.category}
                  </Badge>
                </div>

                {/* Expand/Collapse */}
                <button
                  onClick={() => setExpandedIncident(isExpanded ? null : incident.incident_id)}
                  className="w-full flex items-center justify-center gap-2 text-purple-600 hover:text-purple-700 font-medium py-2 border-t border-gray-100"
                >
                  {isExpanded ? (
                    <>
                      <ChevronUp className="w-4 h-4" />
                      Hide Details
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-4 h-4" />
                      View Solution
                    </>
                  )}
                </button>
              </div>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="border-t border-gray-200 bg-gray-50 p-4 space-y-4">
                  {/* Description */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">Full Description</h4>
                    <p className="text-sm text-gray-600">{incident.description}</p>
                  </div>

                  {/* Root Cause */}
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                    <h4 className="text-sm font-semibold text-orange-900 mb-2 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      Root Cause
                    </h4>
                    <p className="text-sm text-orange-800">{incident.root_cause}</p>
                  </div>

                  {/* Solution */}
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <h4 className="text-sm font-semibold text-green-900 mb-2 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      Solution Applied
                    </h4>
                    <p className="text-sm text-green-800">{incident.solution}</p>
                  </div>

                  {/* Metadata */}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                      <div className="text-gray-500 mb-1">Agent Used</div>
                      <div className="font-medium text-gray-900">{incident.agent_used}</div>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                      <div className="text-gray-500 mb-1">Resolution Time</div>
                      <div className="font-medium text-gray-900">{incident.resolution_time} minutes</div>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                      <div className="text-gray-500 mb-1">Priority</div>
                      <div className="font-medium text-gray-900">{incident.priority}</div>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                      <div className="text-gray-500 mb-1">Category</div>
                      <div className="font-medium text-gray-900">{incident.category}</div>
                    </div>
                  </div>

                  {/* Apply Similar Solution Button */}
                  <button className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    Apply Similar Solution
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Summary */}
      <div className="mt-6 pt-6 border-t border-purple-200">
        <div className="bg-white rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-3">Pattern Insights</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Average Resolution Time:</span>
              <span className="font-medium text-gray-900">
                {Math.round(
                  similarIncidents.reduce((sum, inc) => sum + inc.resolution_time, 0) /
                  similarIncidents.length
                )} minutes
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Most Common Agent:</span>
              <span className="font-medium text-gray-900">
                {similarIncidents[0]?.agent_used || 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Similarity Confidence:</span>
              <span className="font-medium text-gray-900">
                {(
                  (similarIncidents.reduce((sum, inc) => sum + inc.similarity_score, 0) /
                  similarIncidents.length) * 100
                ).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
