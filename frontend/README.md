# AI Agent Platform - Frontend

Production-ready Next.js 14 frontend for the AI Agent Platform with TypeScript, Tailwind CSS, and real-time WebSocket updates.

## Features

- **Dashboard**: Real-time system overview with stats, agent status, and activity charts
- **Incidents Management**: Create, view, filter incidents with AI analysis and similar incident suggestions
- **HITL Approvals**: Human-in-the-loop workflows for routing override and plan approval
- **Agent Monitoring**: Agent grid, detailed metrics, and logs
- **Real-Time Events**: Live event stream with WebSocket integration
- **Settings**: System configuration and agent control

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + CSS Variables
- **State Management**: Zustand + React Query
- **Charts**: Recharts
- **Icons**: Lucide React
- **WebSocket**: Socket.io Client
- **HTTP**: Axios
- **Toast Notifications**: React Hot Toast

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Open browser
open http://localhost:3001
```

### Production Build

```bash
# Build
npm run build

# Start production server
npm start
```

### Docker

```bash
# Build image
docker build -t ai-agent-frontend .

# Run container
docker run -p 3002:3001 \
  -e NEXT_PUBLIC_API_URL=http://orchestrator:8000 \
  -e NEXT_PUBLIC_WS_URL=ws://orchestrator:8000 \
  ai-agent-frontend
```

### Docker Compose

```bash
# Start all services including frontend
cd deployment
docker-compose up frontend
```

## Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js pages
│   │   ├── page.tsx            # Dashboard
│   │   ├── incidents/          # Incidents pages
│   │   ├── approvals/          # HITL approvals pages
│   │   ├── agents/             # Agents pages
│   │   ├── events/             # Events page
│   │   └── settings/           # Settings page
│   ├── components/
│   │   ├── ui/                 # Base UI components
│   │   ├── layout/             # Layout components
│   │   ├── dashboard/          # Dashboard components
│   │   ├── incidents/          # Incident components
│   │   ├── approvals/          # Approval components
│   │   ├── agents/             # Agent components
│   │   └── events/             # Event components
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   ├── websocket.ts        # WebSocket client
│   │   ├── utils.ts            # Utility functions
│   │   └── constants.ts        # Constants
│   ├── hooks/                  # Custom hooks
│   ├── store/                  # State management
│   └── types/                  # TypeScript types
├── public/                     # Static assets
├── Dockerfile                  # Docker configuration
└── next.config.js              # Next.js configuration
```

## Key Features

### 1. Dashboard
- Real-time stats cards (active incidents, agents running, pending approvals, success rate)
- 7-agent status grid with health indicators
- Recent incidents table
- Activity timeline chart (24h)
- System health panel (Kafka, Weaviate, Neo4j, etc.)

### 2. Incidents Management
- Filterable incidents table (priority, status, category)
- Create new incident modal
- Incident detail page with tabs:
  - Overview: Full incident information
  - AI Analysis: AI-generated routing suggestion, confidence, reasoning
  - Similar Incidents: RAG-powered similar incident recommendations

### 3. HITL Approvals (Critical Feature)
- **Routing Override** (STEP 3):
  - View AI-selected agent with confidence score
  - See reasoning and alternative agents
  - Override selection with custom agent
  - Similar incidents for context

- **Plan Approval** (STEP 5):
  - View execution plan steps
  - Risk level indicator (Low/Medium/High/Critical)
  - Commands to execute
  - Files to modify
  - Rollback plan
  - Approve/Reject/Edit actions

### 4. Agent Monitoring
- Agent grid with real-time status
- Per-agent metrics:
  - Success rate
  - Total tasks / tasks (24h)
  - Average response time
  - Current load
- Agent logs with filtering
- Health check status

### 5. Real-Time Events
- Live event stream via WebSocket
- Filter by event type and search
- Event types:
  - incident_created
  - incident_updated
  - approval_required
  - approval_resolved
  - agent_status_changed
  - ticket_created
  - task_completed

### 6. Settings
- Approval timeout configuration
- Notification preferences
- Auto-refresh toggle
- API keys (masked)
- Agent enable/disable

## API Integration

### REST API

```typescript
import { api } from '@/lib/api'

// Incidents
const incidents = await api.getIncidents()
const incident = await api.getIncidentById('INC001')
const newIncident = await api.createIncident({ description: '...', priority: 'P1' })

// Approvals
const approvals = await api.getPendingApprovals()
await api.approveRouting(approvalId, { approved_by: 'Admin', selected_agent: 'servicenow' })
await api.approvePlan(approvalId, { approved_by: 'Admin' })
await api.rejectPlan(approvalId, { rejected_by: 'Admin', rejection_reason: '...' })

// Agents
const agents = await api.getAgents()
const metrics = await api.getAgentMetrics('servicenow')
const logs = await api.getAgentLogs('servicenow', 100)
```

### WebSocket

```typescript
import { wsClient } from '@/lib/websocket'

// Connect
wsClient.connect()

// Listen to events
wsClient.on('incident_created', (data) => {
  console.log('New incident:', data)
})

wsClient.on('approval_required', (data) => {
  console.log('Approval needed:', data)
})
```

## Development

### Adding a New Page

1. Create page in `src/app/[page-name]/page.tsx`
2. Add route to sidebar in `src/components/layout/Sidebar.tsx`
3. Add any page-specific components in `src/components/[page-name]/`

### Adding a New API Endpoint

1. Add function to `src/lib/api.ts`
2. Add types to `src/types/`
3. Use with React Query in components

### Adding a New WebSocket Event

1. Add event constant to `src/lib/constants.ts`
2. Listen in components using `wsClient.on(event, callback)`

## Production Deployment

The frontend is production-ready with:
- ✅ Next.js standalone output for Docker
- ✅ Multi-stage Docker build
- ✅ Static optimization
- ✅ Code splitting
- ✅ Real-time updates via WebSocket
- ✅ Error boundaries
- ✅ Loading states
- ✅ Responsive design
- ✅ TypeScript strict mode
- ✅ ESLint + Prettier

## Port Configuration

- **Development**: http://localhost:3001
- **Production (Docker)**: http://localhost:3002 → container:3001
- **Backend API**: http://localhost:8000
- **WebSocket**: ws://localhost:8000

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT
