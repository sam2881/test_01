'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import {
  Zap, FileText, Activity, Clock, Play, CheckCircle, XCircle, Loader2,
  ChevronDown, ChevronUp, Terminal, Check, Settings, ExternalLink,
  ThumbsUp, ThumbsDown, AlertTriangle, Sparkles, GitBranch, Eye,
  ZoomIn, ZoomOut, RefreshCw
} from 'lucide-react'
import toast from 'react-hot-toast'

// ============================================================================
// API CONFIGURATION
// ============================================================================
// Dynamic API URL - works from any hostname
const getApiBase = () => {
  if (typeof window === 'undefined') return 'http://localhost:8000'
  // If accessing from non-localhost, use same hostname with port 8000
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return `http://${window.location.hostname}:8000`
  }
  return 'http://localhost:8000'
}
const API_BASE = getApiBase()

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================
interface WorkflowStep {
  id: number
  name: string
  phase: string
  node: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'awaiting_approval'
  output?: any
  error?: string
}

interface ScriptMatch {
  script_id: string
  name: string
  description: string
  type: string
  confidence: number
  risk_level: string
  auto_approve: boolean
  required_inputs: string[]
  extracted_inputs: Record<string, any>
}

interface EnterpriseIncidentDetailProps {
  incident: any
}

// ============================================================================
// 18-NODE LANGGRAPH WORKFLOW STEPS
// ============================================================================
const WORKFLOW_STEPS = [
  // Phase 1: Ingest/Parse
  { id: 1, name: 'Ingest Incident', phase: 'ingestion', node: 'ingest' },
  { id: 2, name: 'Parse Context', phase: 'ingestion', node: 'parse_context' },
  { id: 3, name: 'Judge Log Quality', phase: 'ingestion', node: 'judge_log_quality' },
  // Phase 2: Classification
  { id: 4, name: 'Classify Incident', phase: 'classification', node: 'classify_incident' },
  { id: 5, name: 'Judge Classification', phase: 'classification', node: 'judge_classification' },
  // Phase 3: Retrieval
  { id: 6, name: 'RAG Search', phase: 'retrieval', node: 'rag_search' },
  { id: 7, name: 'Judge RAG Results', phase: 'retrieval', node: 'judge_rag' },
  { id: 8, name: 'Graph Search', phase: 'retrieval', node: 'graph_search' },
  { id: 9, name: 'Merge Context', phase: 'retrieval', node: 'merge_context' },
  // Phase 4: Script Selection
  { id: 10, name: 'Match Scripts', phase: 'selection', node: 'match_scripts' },
  { id: 11, name: 'Judge Script Selection', phase: 'selection', node: 'judge_script_selection' },
  // Phase 5: Planning
  { id: 12, name: 'Generate Plan', phase: 'planning', node: 'generate_plan' },
  { id: 13, name: 'Judge Plan Safety', phase: 'planning', node: 'judge_plan_safety' },
  // Phase 6: Execution
  { id: 14, name: 'Human Approval', phase: 'execution', node: 'approval_workflow' },
  { id: 15, name: 'Execute Pipeline', phase: 'execution', node: 'execute_pipeline' },
  // Phase 7: Validation
  { id: 16, name: 'Validate Fix', phase: 'validation', node: 'validate_fix' },
  { id: 17, name: 'Close Ticket', phase: 'validation', node: 'close_ticket' },
  // Phase 8: Learning
  { id: 18, name: 'Update Knowledge Base', phase: 'learning', node: 'learn' },
]

const PHASES = [
  { id: 'ingestion', name: 'Ingestion', color: 'bg-blue-500' },
  { id: 'classification', name: 'Classification', color: 'bg-purple-500' },
  { id: 'retrieval', name: 'Retrieval', color: 'bg-cyan-500' },
  { id: 'selection', name: 'Selection', color: 'bg-orange-500' },
  { id: 'planning', name: 'Planning', color: 'bg-yellow-500' },
  { id: 'execution', name: 'Execution', color: 'bg-red-500' },
  { id: 'validation', name: 'Validation', color: 'bg-green-500' },
  { id: 'learning', name: 'Learning', color: 'bg-indigo-500' },
]

// ============================================================================
// GRAPH VIEW TYPES
// ============================================================================
interface GraphNode {
  id: number
  name: string
  phase: string
  type: string
  description: string
}

interface GraphEdge {
  from: number
  to: number
}

interface GraphPhase {
  name: string
  nodes: number[]
  color: string
}

interface GraphDefinition {
  nodes: GraphNode[]
  edges: GraphEdge[]
  phases: GraphPhase[]
}

// ============================================================================
// GRAPH VIEW COMPONENT (SVG-based visualization)
// ============================================================================
interface GraphViewProps {
  steps: WorkflowStep[]
  onNodeClick: (nodeId: number) => void
}

function GraphView({ steps, onNodeClick }: GraphViewProps) {
  const [graphDef, setGraphDef] = useState<GraphDefinition | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const [hoveredNode, setHoveredNode] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  // Fetch graph definition from API
  useEffect(() => {
    const fetchGraph = async () => {
      try {
        setLoading(true)
        const res = await fetch(`${getApiBase()}/api/langgraph/definition`)
        if (!res.ok) throw new Error('Failed to fetch graph')
        const data = await res.json()
        setGraphDef(data)
        setError(null)
      } catch (err: any) {
        console.error('Graph fetch error:', err)
        setError(err.message)
        // Fallback to local definition
        setGraphDef({
          nodes: WORKFLOW_STEPS.map(s => ({
            id: s.id,
            name: s.name,
            phase: s.phase,
            type: s.id === 14 ? 'human' : s.id % 3 === 0 ? 'llm' : 'processor',
            description: `Node ${s.id}: ${s.name}`
          })),
          edges: Array.from({ length: 17 }, (_, i) => ({ from: i + 1, to: i + 2 })),
          phases: PHASES.map(p => ({
            name: p.name,
            nodes: WORKFLOW_STEPS.filter(s => s.phase === p.id).map(s => s.id),
            color: p.color.replace('bg-', '#').replace('-500', '')
          }))
        })
      } finally {
        setLoading(false)
      }
    }
    fetchGraph()
  }, [])

  // Get status color for node
  const getNodeStatusColor = (nodeId: number) => {
    const step = steps.find(s => s.id === nodeId)
    if (!step) return '#9CA3AF' // gray
    switch (step.status) {
      case 'completed': return '#22C55E' // green
      case 'running': return '#3B82F6' // blue
      case 'failed': return '#EF4444' // red
      case 'awaiting_approval': return '#F59E0B' // yellow
      default: return '#D1D5DB' // light gray
    }
  }

  // Get phase color
  const getPhaseColor = (phase: string) => {
    const colors: Record<string, string> = {
      'Ingestion': '#3B82F6',
      'Classification': '#8B5CF6',
      'Retrieval': '#06B6D4',
      'Selection': '#F97316',
      'Planning': '#EAB308',
      'Execution': '#EF4444',
      'Validation': '#22C55E',
      'Learning': '#6366F1'
    }
    return colors[phase] || '#6B7280'
  }

  // Calculate node positions in a flowchart layout
  const getNodePosition = (nodeId: number, totalNodes: number) => {
    const nodesPerRow = 6
    const row = Math.floor((nodeId - 1) / nodesPerRow)
    const col = (nodeId - 1) % nodesPerRow
    const isReversedRow = row % 2 === 1
    const actualCol = isReversedRow ? (nodesPerRow - 1 - col) : col

    return {
      x: 100 + actualCol * 160,
      y: 80 + row * 150
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-900 rounded-lg">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        <span className="ml-2 text-white">Loading graph...</span>
      </div>
    )
  }

  if (error && !graphDef) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-900 rounded-lg">
        <AlertTriangle className="w-8 h-8 text-red-500" />
        <span className="ml-2 text-white">Error loading graph: {error}</span>
      </div>
    )
  }

  const nodes = graphDef?.nodes || []
  const edges = graphDef?.edges || []

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      {/* Controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-indigo-400" />
          <span className="text-white font-semibold">LangGraph Workflow Visualization</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}
            className="bg-gray-800 border-gray-700 text-white hover:bg-gray-700"
          >
            <ZoomOut className="w-4 h-4" />
          </Button>
          <span className="text-gray-400 text-sm">{Math.round(zoom * 100)}%</span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setZoom(z => Math.min(2, z + 0.1))}
            className="bg-gray-800 border-gray-700 text-white hover:bg-gray-700"
          >
            <ZoomIn className="w-4 h-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setZoom(1)}
            className="bg-gray-800 border-gray-700 text-white hover:bg-gray-700"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-4">
        {PHASES.map(phase => (
          <div key={phase.id} className="flex items-center gap-1.5">
            <div className={`w-3 h-3 rounded ${phase.color}`} />
            <span className="text-xs text-gray-400">{phase.name}</span>
          </div>
        ))}
        <div className="border-l border-gray-700 mx-2" />
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-green-500" />
          <span className="text-xs text-gray-400">Completed</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-blue-500 animate-pulse" />
          <span className="text-xs text-gray-400">Running</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-yellow-500" />
          <span className="text-xs text-gray-400">Awaiting</span>
        </div>
      </div>

      {/* SVG Graph */}
      <div className="overflow-auto bg-gray-950 rounded-lg" style={{ maxHeight: '550px' }}>
        <svg
          ref={svgRef}
          width={1100 * zoom}
          height={550 * zoom}
          viewBox="0 0 1100 550"
          className="mx-auto"
        >
          {/* Defs for gradients and markers */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#6B7280" />
            </marker>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background grid */}
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1F2937" strokeWidth="1" />
          </pattern>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Edges (connections) */}
          {edges.map((edge, idx) => {
            const fromPos = getNodePosition(edge.from, nodes.length)
            const toPos = getNodePosition(edge.to, nodes.length)

            // Calculate control points for curved lines
            const midX = (fromPos.x + toPos.x) / 2
            const midY = (fromPos.y + toPos.y) / 2
            const dx = toPos.x - fromPos.x
            const dy = toPos.y - fromPos.y

            let path = ''
            if (Math.abs(dy) > 50) {
              // Different rows - use curved path
              const controlOffset = 40
              path = `M ${fromPos.x + 60} ${fromPos.y + 25}
                      Q ${fromPos.x + 60 + controlOffset} ${fromPos.y + 25 + dy/2}
                        ${toPos.x + 60} ${toPos.y - 10}`
            } else {
              // Same row - straight line
              path = `M ${fromPos.x + 120} ${fromPos.y + 25}
                      L ${toPos.x} ${toPos.y + 25}`
            }

            return (
              <path
                key={idx}
                d={path}
                fill="none"
                stroke="#4B5563"
                strokeWidth="2"
                markerEnd="url(#arrowhead)"
                className="transition-all duration-300"
              />
            )
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const pos = getNodePosition(node.id, nodes.length)
            const step = steps.find(s => s.id === node.id)
            const statusColor = getNodeStatusColor(node.id)
            const phaseColor = getPhaseColor(node.phase)
            const isHovered = hoveredNode === node.id
            const isRunning = step?.status === 'running'

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => onNodeClick(node.id)}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                className="cursor-pointer"
                filter={isRunning ? 'url(#glow)' : undefined}
              >
                {/* Node background */}
                <rect
                  x="0"
                  y="0"
                  width="120"
                  height="50"
                  rx="8"
                  fill={isHovered ? '#374151' : '#1F2937'}
                  stroke={statusColor}
                  strokeWidth={isRunning ? "3" : "2"}
                  className="transition-all duration-200"
                />

                {/* Phase indicator bar */}
                <rect
                  x="0"
                  y="0"
                  width="120"
                  height="6"
                  rx="8"
                  ry="0"
                  fill={phaseColor}
                  clipPath="inset(0 0 50% 0 round 8px)"
                />

                {/* Node ID badge */}
                <circle
                  cx="15"
                  cy="28"
                  r="12"
                  fill={statusColor}
                  className={isRunning ? 'animate-pulse' : ''}
                />
                <text
                  x="15"
                  y="32"
                  textAnchor="middle"
                  fill="white"
                  fontSize="10"
                  fontWeight="bold"
                >
                  {node.id}
                </text>

                {/* Node name */}
                <text
                  x="35"
                  y="24"
                  fill="white"
                  fontSize="9"
                  fontWeight="500"
                >
                  {node.name.length > 12 ? node.name.slice(0, 12) + '...' : node.name}
                </text>

                {/* Node type */}
                <text
                  x="35"
                  y="38"
                  fill="#9CA3AF"
                  fontSize="8"
                >
                  {node.type}
                </text>

                {/* Status icon */}
                {step?.status === 'completed' && (
                  <circle cx="105" cy="25" r="8" fill="#22C55E" />
                )}
                {step?.status === 'running' && (
                  <circle cx="105" cy="25" r="8" fill="#3B82F6" className="animate-pulse" />
                )}
                {step?.status === 'failed' && (
                  <circle cx="105" cy="25" r="8" fill="#EF4444" />
                )}
                {step?.status === 'awaiting_approval' && (
                  <circle cx="105" cy="25" r="8" fill="#F59E0B" />
                )}

                {/* Hover tooltip */}
                {isHovered && (
                  <g transform="translate(0, 55)">
                    <rect
                      x="-10"
                      y="0"
                      width="180"
                      height="40"
                      rx="4"
                      fill="#111827"
                      stroke="#374151"
                    />
                    <text x="0" y="15" fill="#D1D5DB" fontSize="9">
                      {node.description || node.name}
                    </text>
                    <text x="0" y="30" fill="#6B7280" fontSize="8">
                      Phase: {node.phase} | Type: {node.type}
                    </text>
                  </g>
                )}
              </g>
            )
          })}
        </svg>
      </div>

      {/* Phase summary */}
      <div className="mt-4 grid grid-cols-4 gap-2">
        {PHASES.map(phase => {
          const phaseSteps = steps.filter(s => s.phase === phase.id)
          const completed = phaseSteps.filter(s => s.status === 'completed').length
          const total = phaseSteps.length
          const progress = total > 0 ? (completed / total) * 100 : 0

          return (
            <div key={phase.id} className="bg-gray-800 rounded p-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400">{phase.name}</span>
                <span className="text-xs text-white">{completed}/{total}</span>
              </div>
              <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${phase.color} transition-all duration-500`}
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export function EnterpriseIncidentDetail({ incident }: EnterpriseIncidentDetailProps) {
  const [steps, setSteps] = useState<WorkflowStep[]>(
    WORKFLOW_STEPS.map(s => ({ ...s, status: 'pending' as const }))
  )
  const [currentStep, setCurrentStep] = useState(0)
  const [isRunning, setIsRunning] = useState(false)
  const [expandedStep, setExpandedStep] = useState<number | null>(null)
  const [matchedScripts, setMatchedScripts] = useState<ScriptMatch[]>([])
  const [selectedScript, setSelectedScript] = useState<ScriptMatch | null>(null)
  const [executionId, setExecutionId] = useState<string | null>(null)
  const [awaitingApproval, setAwaitingApproval] = useState(false)
  const [githubRunUrl, setGithubRunUrl] = useState<string | null>(null)

  const incidentId = incident?.incident_id || incident?.number || 'Unknown'
  const description = `${incident?.short_description || ''} ${incident?.description || ''}`

  // Update step status helper
  const updateStep = (stepId: number, status: WorkflowStep['status'], output?: any, error?: string) => {
    setSteps(prev => prev.map(s =>
      s.id === stepId ? { ...s, status, output, error } : s
    ))
    if (status === 'completed' || status === 'failed') {
      setExpandedStep(stepId)
    }
  }

  // Generate unique workflow ID
  const generateWorkflowId = () => `WF-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

  // Execute a single LangGraph node via API
  const executeNode = async (nodeId: number, workflowId: string): Promise<any> => {
    console.log(`[Node ${nodeId}] Executing via API...`)

    const response = await fetch(`${API_BASE}/api/langgraph/node/${nodeId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow_id: workflowId,
        incident_id: incidentId,
        node_id: nodeId,
        input_data: {}
      })
    })

    if (!response.ok) {
      throw new Error(`Node ${nodeId} failed: ${response.status}`)
    }

    const result = await response.json()
    console.log(`[Node ${nodeId}] Response:`, result)
    return result
  }

  // Run the full 18-node LangGraph workflow with REAL API calls
  const runWorkflow = async () => {
    if (isRunning) return
    setIsRunning(true)

    const workflowId = generateWorkflowId()
    console.log(`[Workflow] Starting ${workflowId} for incident ${incidentId}`)

    try {
      // Execute all 18 nodes sequentially with real API calls
      for (let nodeId = 1; nodeId <= 18; nodeId++) {
        updateStep(nodeId, 'running')

        try {
          const result = await executeNode(nodeId, workflowId)

          if (result.status === 'completed') {
            updateStep(nodeId, 'completed', result.output)

            // Handle special nodes
            if (nodeId === 10 && result.output?.matches) {
              // Script matching - store matched scripts
              const matches = result.output.matches
              setMatchedScripts(matches)
              if (matches.length > 0) {
                setSelectedScript(matches[0])
              }
            }

            if (nodeId === 14 && result.output?.approval_required && !result.output?.auto_approved) {
              // Human approval required - pause workflow
              updateStep(14, 'awaiting_approval', result.output)
              setAwaitingApproval(true)
              // Set execution_id from node 14 for approval tracking
              if (result.output?.execution_id) {
                setExecutionId(result.output.execution_id)
              }
              // Set selected script from approval info
              if (result.output?.script) {
                setSelectedScript({
                  script_id: result.output.script.script_id,
                  name: result.output.script.name,
                  description: result.output.script.description || '',
                  type: result.output.script.type || 'shell',
                  confidence: 0.8,
                  risk_level: result.output.script.risk_level || 'medium',
                  auto_approve: false,
                  required_inputs: [],
                  extracted_inputs: result.output.script.extracted_inputs || {}
                })
              }
              toast.success('Workflow paused - awaiting human approval')
              return
            }

            if (nodeId === 15 && result.output?.github_run) {
              // Execution triggered
              setExecutionId(result.output.execution_id)
              if (result.output.github_run.html_url) {
                setGithubRunUrl(result.output.github_run.html_url)
              }
            }

          } else if (result.status === 'awaiting_approval') {
            updateStep(nodeId, 'awaiting_approval', result.output)
            setAwaitingApproval(true)
            toast.success('Workflow paused - awaiting approval')
            return

          } else if (result.status === 'failed' || result.status === 'error') {
            updateStep(nodeId, 'failed', null, result.error || result.output?.error || 'Unknown error')
            toast.error(`Node ${nodeId} failed: ${result.error || 'Unknown error'}`)
            setIsRunning(false)
            return

          } else if (result.status === 'blocked') {
            updateStep(nodeId, 'failed', result.output, result.output?.reason || 'Blocked')
            toast.error(`Node ${nodeId} blocked: ${result.output?.reason}`)
            setIsRunning(false)
            return
          }

        } catch (nodeError: any) {
          console.error(`[Node ${nodeId}] Error:`, nodeError)
          updateStep(nodeId, 'failed', null, nodeError.message)
          toast.error(`Node ${nodeId} failed: ${nodeError.message}`)
          setIsRunning(false)
          return
        }
      }

      // Workflow completed successfully
      toast.success('Workflow completed successfully!')
      setIsRunning(false)

    } catch (error: any) {
      console.error('[Workflow] Error:', error)
      toast.error(`Workflow error: ${error.message}`)
      setIsRunning(false)
    }
  }

  // Legacy runWorkflow for backward compatibility (commented out)
  const runWorkflowLegacy = async () => {
    if (isRunning) return
    setIsRunning(true)

    try {
      // Phase 1: Ingestion (Steps 1-3)
      // Step 1: Ingest Incident
      updateStep(1, 'running')
      await new Promise(r => setTimeout(r, 300))
      updateStep(1, 'completed', { incident_id: incidentId, raw_incident: description })

      // Step 2: Parse Context
      updateStep(2, 'running')
      await new Promise(r => setTimeout(r, 400))
      updateStep(2, 'completed', {
        parsed_context: { service: incident?.category, error_type: 'unknown', keywords: description.split(' ').slice(0, 5) }
      })

      // Step 3: Judge Log Quality
      updateStep(3, 'running')
      await new Promise(r => setTimeout(r, 300))
      updateStep(3, 'completed', { log_quality_confidence: 0.85, primary_error: incident?.short_description })

      // Phase 2: Classification (Steps 4-5)
      // Step 4: Classify Incident
      updateStep(4, 'running')
      await new Promise(r => setTimeout(r, 400))
      const classification = description.toLowerCase().includes('gcp') ? 'gcp' :
                            description.toLowerCase().includes('kubernetes') ? 'kubernetes' : 'platform'
      updateStep(4, 'completed', { classification })

      // Step 5: Judge Classification
      updateStep(5, 'running')
      await new Promise(r => setTimeout(r, 300))
      updateStep(5, 'completed', { validated_classification: classification, confidence: 0.9 })

      // Phase 3: Retrieval (Steps 6-9)
      // Step 6: RAG Search
      updateStep(6, 'running')
      await new Promise(r => setTimeout(r, 500))
      updateStep(6, 'completed', { rag_results: [{ id: 'rag_1', similarity: 0.85 }, { id: 'rag_2', similarity: 0.72 }] })

      // Step 7: Judge RAG Results
      updateStep(7, 'running')
      await new Promise(r => setTimeout(r, 300))
      updateStep(7, 'completed', { filtered_rag: [{ id: 'rag_1', similarity: 0.85 }] })

      // Step 8: Graph Search
      updateStep(8, 'running')
      await new Promise(r => setTimeout(r, 400))
      updateStep(8, 'completed', { graph_context: { service_dependencies: [], owner_team: 'platform-team' } })

      // Step 9: Merge Context
      updateStep(9, 'running')
      await new Promise(r => setTimeout(r, 300))
      updateStep(9, 'completed', { merged_context: { classification, rag_count: 1, has_graph: true } })

      // Phase 4: Script Selection (Steps 10-11)
      // Step 10: Match Scripts - REAL API CALL with POST body
      updateStep(10, 'running')

      // Build request body with all incident details
      const matchRequestBody = {
        incident_id: incidentId,
        short_description: incident?.short_description || '',
        description: incident?.description || '',
        category: incident?.category || ''
      }

      console.log('[Step 10] Sending match request:', matchRequestBody)

      let scriptsMatched: ScriptMatch[] = []

      try {
        const matchRes = await fetch(`${API_BASE}/api/scripts/match`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(matchRequestBody)
        })

        if (!matchRes.ok) {
          const errorText = await matchRes.text()
          console.error('[Step 10] API error:', matchRes.status, errorText)
          throw new Error(`API error: ${matchRes.status}`)
        }

        const matchData = await matchRes.json()
        console.log('[Step 10] Match response:', matchData)

        if (matchData.matches && matchData.matches.length > 0) {
          scriptsMatched = matchData.matches
          setMatchedScripts(matchData.matches)
          setSelectedScript(matchData.matches[0])
          updateStep(10, 'completed', {
            candidates: matchData.matches,
            method: matchData.method,
            count: matchData.count
          })
        } else {
          console.warn('[Step 10] No matches found in response:', matchData)
          updateStep(10, 'failed', null, 'No matching scripts found')
          setIsRunning(false)
          return
        }
      } catch (fetchError: any) {
        console.error('[Step 10] Fetch error:', fetchError)
        updateStep(10, 'failed', null, `Error: ${fetchError.message}`)
        setIsRunning(false)
        return
      }

      // Step 11: Judge Script Selection
      updateStep(11, 'running')
      await new Promise(r => setTimeout(r, 400))

      const topScript = scriptsMatched[0]
      if (!topScript) {
        updateStep(11, 'failed', null, 'No script selected')
        setIsRunning(false)
        return
      }

      updateStep(11, 'completed', {
        selected_script: topScript,
        hybrid_score: topScript.confidence,
        approval_required: !topScript.auto_approve
      })

      // Phase 5: Planning (Steps 12-13)
      // Step 12: Generate Plan
      updateStep(12, 'running')
      await new Promise(r => setTimeout(r, 400))
      updateStep(12, 'completed', {
        plan: { script_id: topScript.script_id, execution_steps: ['Validate', 'Execute', 'Verify'] }
      })

      // Step 13: Judge Plan Safety
      updateStep(13, 'running')
      await new Promise(r => setTimeout(r, 300))
      updateStep(13, 'completed', {
        plan_safe: true,
        risk_level: topScript.risk_level,
        approval_required: !topScript.auto_approve
      })

      // Phase 6: Execution (Steps 14-15)
      // Step 14: Human Approval
      if (!topScript.auto_approve) {
        updateStep(14, 'awaiting_approval', { requires_approval: true, risk_level: topScript.risk_level })
        setAwaitingApproval(true)
        // Workflow pauses here - continues in handleApprove()
        return
      } else {
        updateStep(14, 'completed', { auto_approved: true })
        await executeScript()
      }

    } catch (error: any) {
      toast.error(`Workflow error: ${error.message}`)
      setIsRunning(false)
    }
  }

  // Execute the script via GitHub Actions (Steps 15-18)
  const executeScript = async () => {
    if (!selectedScript) return

    try {
      // Step 15: Execute Pipeline
      updateStep(15, 'running')

      const execRes = await fetch(`${API_BASE}/api/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          incident_id: incidentId,
          script_id: selectedScript.script_id,
          inputs: selectedScript.extracted_inputs || {},
          environment: 'development',
          dry_run: false
        })
      })
      const execData = await execRes.json()

      if (execData.execution_id) {
        setExecutionId(execData.execution_id)
      }

      if (execData.status === 'pending_approval') {
        setExecutionId(execData.execution_id)
        setAwaitingApproval(true)
        updateStep(14, 'awaiting_approval', execData)
        updateStep(15, 'pending')
        return
      }

      if (execData.github_run?.html_url) {
        setGithubRunUrl(execData.github_run.html_url)
      }

      updateStep(15, 'completed', execData)

      // Step 16: Validate Fix
      updateStep(16, 'running')
      await new Promise(r => setTimeout(r, 800))
      updateStep(16, 'completed', { fix_valid: true, validation_confidence: 0.92 })

      // Step 17: Close Ticket
      updateStep(17, 'running')
      const closeRes = await fetch(`${API_BASE}/api/incidents/${incidentId}/close?resolution=Resolved by AI Agent`, {
        method: 'POST'
      })
      const closeData = await closeRes.json()
      updateStep(17, 'completed', closeData)

      // Step 18: Update Knowledge Base
      updateStep(18, 'running')
      await new Promise(r => setTimeout(r, 500))
      updateStep(18, 'completed', { kb_update: 'completed', learned: true })

      toast.success('Workflow completed successfully!')
      setIsRunning(false)

    } catch (error: any) {
      updateStep(15, 'failed', null, error.message)
      toast.error(`Execution error: ${error.message}`)
      setIsRunning(false)
    }
  }

  // Handle human approval (Step 14) - Continue workflow after approval
  const handleApprove = async () => {
    try {
      updateStep(14, 'completed', { approved: true, by: 'admin', timestamp: new Date().toISOString() })
      setAwaitingApproval(false)
      toast.success('Execution approved! Continuing workflow...')

      // Continue workflow from node 15 onwards
      const workflowId = generateWorkflowId()

      for (let nodeId = 15; nodeId <= 18; nodeId++) {
        updateStep(nodeId, 'running')

        try {
          // For node 15, pass the script info and approved flag
          let inputData: any = { approved: true }
          if (nodeId === 15 && selectedScript) {
            inputData = {
              approved: true,
              script_id: selectedScript.script_id,
              inputs: selectedScript.extracted_inputs || {}
            }
          }

          const response = await fetch(`${API_BASE}/api/langgraph/node/${nodeId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              workflow_id: workflowId,
              incident_id: incidentId,
              node_id: nodeId,
              input_data: inputData
            })
          })

          if (!response.ok) throw new Error(`Node ${nodeId} failed`)

          const result = await response.json()
          console.log(`[Node ${nodeId}] Post-approval result:`, result)

          if (result.status === 'completed') {
            updateStep(nodeId, 'completed', result.output)

            // Capture GitHub run URL from node 15
            if (nodeId === 15 && result.output?.github_run?.html_url) {
              setGithubRunUrl(result.output.github_run.html_url)
              setExecutionId(result.output.execution_id)
            }
          } else if (result.status === 'failed' || result.status === 'error') {
            updateStep(nodeId, 'failed', null, result.error || 'Unknown error')
            toast.error(`Node ${nodeId} failed: ${result.error}`)
            setIsRunning(false)
            return
          }

        } catch (nodeError: any) {
          console.error(`[Node ${nodeId}] Error:`, nodeError)
          updateStep(nodeId, 'failed', null, nodeError.message)
          toast.error(`Node ${nodeId} failed: ${nodeError.message}`)
          setIsRunning(false)
          return
        }
      }

      toast.success('Workflow completed successfully!')
      setIsRunning(false)

    } catch (error: any) {
      console.error('Approval error:', error)
      toast.error(`Approval failed: ${error.message}`)
    }
  }

  // Handle rejection (Step 14)
  const handleReject = async () => {
    updateStep(14, 'failed', null, 'Rejected by user')
    setAwaitingApproval(false)
    setIsRunning(false)
    toast.success('Execution rejected')
  }

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'running': return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      case 'failed': return <XCircle className="w-5 h-5 text-red-500" />
      case 'awaiting_approval': return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      default: return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
    }
  }

  // Get status badge color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'running': return 'bg-blue-100 text-blue-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'awaiting_approval': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <Zap className="w-6 h-6 text-indigo-600" />
                Incident Resolution: {incidentId}
              </h1>
              <p className="text-gray-600 mt-1">{incident?.short_description || 'No description'}</p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={incident?.priority === '1' ? 'error' : incident?.priority === '2' ? 'warning' : 'default'}>
                Priority {incident?.priority || '3'}
              </Badge>
              <Badge variant={incident?.status === '6' ? 'success' : 'default'}>
                {incident?.status === '6' ? 'Resolved' : 'Open'}
              </Badge>
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Progress:</span>
              <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium">
                {steps.filter(s => s.status === 'completed').length} / 18 nodes completed
              </span>
            </div>
            <button
              onClick={() => window.open(`/graph/${incidentId}`, '_blank')}
              className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
            >
              <GitBranch className="w-4 h-4" />
              Open Graph View
              <ExternalLink className="w-3 h-3 ml-1" />
            </button>
          </div>
        </div>

        {/* Main Content - Workflow */}
        <div className="grid grid-cols-12 gap-6">
          {/* Left Panel - 18-Node Workflow Steps */}
          <div className="col-span-4">
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="p-4 border-b bg-gradient-to-r from-indigo-50 to-purple-50">
                <h2 className="font-bold text-gray-900 flex items-center gap-2 text-lg">
                  <Activity className="w-6 h-6 text-indigo-600" />
                  LangGraph Workflow
                </h2>
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-bold bg-indigo-600 text-white">
                      18 Nodes
                    </span>
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                      8 Phases
                    </span>
                  </div>
                  <span className="text-sm font-medium text-gray-600">
                    {steps.filter(s => s.status === 'completed').length}/18 done
                  </span>
                </div>
              </div>
              <div className="p-3 space-y-2 max-h-[650px] overflow-y-auto">
                {PHASES.map(phase => {
                  const phaseSteps = steps.filter(s => s.phase === phase.id)
                  const completedCount = phaseSteps.filter(s => s.status === 'completed').length
                  const isPhaseActive = phaseSteps.some(s => s.status === 'running' || s.status === 'awaiting_approval')

                  return (
                    <div key={phase.id} className="mb-2">
                      {/* Phase Header */}
                      <div className={`flex items-center gap-2 px-3 py-2 rounded-t-lg text-sm font-semibold ${phase.color} text-white`}>
                        <span>{phase.name}</span>
                        <span className="ml-auto bg-white/20 px-2 py-0.5 rounded text-xs">{completedCount}/{phaseSteps.length}</span>
                      </div>
                      {/* Individual Nodes */}
                      <div className="border-l-4 border-gray-200 ml-1 space-y-1 py-1">
                        {phaseSteps.map(step => (
                          <div
                            key={step.id}
                            className={`p-3 rounded-r-lg border-l-4 cursor-pointer transition-all ml-0 mr-1 ${
                              expandedStep === step.id ? 'border-l-indigo-500 bg-indigo-50 shadow-sm' :
                              step.status === 'running' ? 'border-l-blue-500 bg-blue-50' :
                              step.status === 'completed' ? 'border-l-green-500 bg-green-50' :
                              step.status === 'awaiting_approval' ? 'border-l-yellow-500 bg-yellow-50' :
                              step.status === 'failed' ? 'border-l-red-500 bg-red-50' :
                              'border-l-gray-300 bg-gray-50 hover:bg-gray-100'
                            }`}
                            onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-white text-xs font-bold text-gray-600 shadow-sm border">
                                  {step.id}
                                </span>
                                {getStatusIcon(step.status)}
                                <span className={`text-sm font-medium ${
                                  step.status === 'running' ? 'text-blue-700' :
                                  step.status === 'completed' ? 'text-green-700' :
                                  step.status === 'failed' ? 'text-red-700' :
                                  'text-gray-700'
                                }`}>
                                  {step.name}
                                </span>
                              </div>
                            </div>

                            {expandedStep === step.id && step.output && (
                              <div className="mt-3 pt-2 border-t border-gray-200">
                                <pre className="text-xs bg-gray-900 text-green-400 p-3 rounded overflow-auto max-h-40 font-mono">
                                  {JSON.stringify(step.output, null, 2)}
                                </pre>
                              </div>
                            )}

                            {expandedStep === step.id && step.error && (
                              <div className="mt-3 pt-2 border-t border-red-200">
                                <p className="text-xs text-red-600 bg-red-50 p-2 rounded">{step.error}</p>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Center Panel - Main Content */}
          <div className="col-span-8 space-y-6">
            {/* Action Panel */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-600" />
                  AI-Powered Remediation
                </h2>
                <Button
                  onClick={runWorkflow}
                  disabled={isRunning && !awaitingApproval}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  {isRunning ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Start Workflow
                    </>
                  )}
                </Button>
              </div>

              {/* Approval Panel */}
              {awaitingApproval && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-600" />
                    <span className="font-medium text-yellow-800">Human Approval Required</span>
                  </div>

                  {selectedScript && (
                    <div className="bg-white rounded p-3 mb-4">
                      <p className="text-sm text-gray-600 mb-2">
                        <strong>Script:</strong> {selectedScript.name}
                      </p>
                      <p className="text-sm text-gray-600 mb-2">
                        <strong>Risk Level:</strong> {selectedScript.risk_level}
                      </p>
                      <p className="text-sm text-gray-600">
                        <strong>Type:</strong> {selectedScript.type}
                      </p>
                    </div>
                  )}

                  <div className="flex gap-3">
                    <Button
                      onClick={handleApprove}
                      className="bg-green-600 hover:bg-green-700 text-white flex-1"
                    >
                      <ThumbsUp className="w-4 h-4 mr-2" />
                      Approve Execution
                    </Button>
                    <Button
                      onClick={handleReject}
                      variant="outline"
                      className="flex-1 border-red-300 text-red-600 hover:bg-red-50"
                    >
                      <ThumbsDown className="w-4 h-4 mr-2" />
                      Reject
                    </Button>
                  </div>
                </div>
              )}

              {/* Matched Scripts */}
              {matchedScripts.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <div className="bg-gray-50 px-4 py-2 border-b">
                    <h3 className="font-medium text-gray-700">Matched Scripts</h3>
                  </div>
                  <div className="divide-y">
                    {matchedScripts.map((script, index) => (
                      <div
                        key={script.script_id}
                        className={`p-4 hover:bg-gray-50 cursor-pointer ${
                          selectedScript?.script_id === script.script_id ? 'bg-indigo-50' : ''
                        }`}
                        onClick={() => setSelectedScript(script)}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900">{script.name}</p>
                            <p className="text-sm text-gray-600">{script.description}</p>
                          </div>
                          <div className="text-right">
                            <Badge variant={script.confidence > 0.7 ? 'success' : 'warning'}>
                              {Math.round(script.confidence * 100)}% match
                            </Badge>
                            <p className="text-xs text-gray-500 mt-1">{script.type}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* GitHub Run Link */}
              {githubRunUrl && (
                <div className="mt-4 p-4 bg-gray-900 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-white">
                      <Terminal className="w-5 h-5" />
                      <span>GitHub Actions Execution</span>
                    </div>
                    <a
                      href={githubRunUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                    >
                      View Run <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              )}
            </div>

            {/* Incident Details */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-600" />
                Incident Details
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-500">Category</label>
                  <p className="font-medium">{incident?.category || 'Unknown'}</p>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Priority</label>
                  <p className="font-medium">P{incident?.priority || '3'}</p>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Created</label>
                  <p className="font-medium">{incident?.created_at || 'Unknown'}</p>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Assigned To</label>
                  <p className="font-medium">{incident?.assigned_to || 'Unassigned'}</p>
                </div>
              </div>
              <div className="mt-4">
                <label className="text-sm text-gray-500">Description</label>
                <p className="mt-1 text-gray-700 whitespace-pre-wrap">
                  {incident?.description || 'No description provided'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
