# AI Agent Platform for Enterprise Incident Remediation
## Comprehensive Architecture & Implementation Guide

---

# 🎨 Design

## Design Philosophy
- **Event-Driven Architecture**: Kafka-based streaming for real-time incident processing
- **MCP-First Approach**: Model Context Protocol for standardized AI-tool communication
- **LangGraph Orchestration**: 18-node workflow for structured incident resolution
- **Human-in-the-Loop (HITL)**: Critical decisions require human approval

## Key Design Decisions
| Decision | Rationale |
|----------|-----------|
| Microservices | Independent scaling, fault isolation |
| MCP Servers | Standardized tool interfaces |
| LangGraph | Stateful, debuggable AI workflows |
| GitHub Actions | Secure, auditable script execution |

---

# 📜 Compliance

## Compliance Framework
```
┌─────────────────────────────────────────────────────────────┐
│                    COMPLIANCE LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  ✓ Audit Logging      │  All actions logged to Kafka        │
│  ✓ RBAC               │  Role-based access control          │
│  ✓ Data Encryption    │  TLS in transit, encrypted at rest  │
│  ✓ Script Validation  │  Security scan before execution     │
│  ✓ Approval Workflow  │  HITL for high-risk operations      │
└─────────────────────────────────────────────────────────────┘
```

## Implementation
- **File**: `backend/orchestrator/enterprise_executor.py`
- **Security Scan**: Shellcheck + dangerous pattern detection
- **Audit Trail**: All executions logged with user, timestamp, inputs

---

# 🧭 Architecture

## High-Level Architecture
```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js)                           │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│   │  Incidents  │  │  Workflows  │  │  Graph View │  │  Approvals  │     │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
└──────────┼────────────────┼────────────────┼────────────────┼────────────┘
           │                │                │                │
           ▼                ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY (FastAPI)                             │
│   ┌─────────────────────────────────────────────────────────────────┐    │
│   │  /api/incidents  │  /api/langgraph  │  /api/execute  │  /api/mcp│    │
│   └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
           │                │                │                │
           ▼                ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                               │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                │
│   │  LangGraph    │  │  LLM Intel    │  │  Enterprise   │                │
│   │  Orchestrator │  │  (GPT-4)      │  │  Executor     │                │
│   └───────────────┘  └───────────────┘  └───────────────┘                │
└──────────────────────────────────────────────────────────────────────────┘
           │                │                │                │
           ▼                ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           MCP SERVERS                                     │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│   │ServiceNow│  │   GCP   │  │ GitHub  │  │  Jira   │  │  Slack  │       │
│   │   MCP   │  │   MCP   │  │   MCP   │  │   MCP   │  │   MCP   │       │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
└──────────────────────────────────────────────────────────────────────────┘
           │                │                │                │
           ▼                ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         STREAMING LAYER (Kafka)                           │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│   │ servicenow.     │  │   gcp.alerts    │  │  agent.events   │          │
│   │   incidents     │  │                 │  │                 │          │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘          │
└──────────────────────────────────────────────────────────────────────────┘
           │                │                │                │
           ▼                ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                       │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│   │  PostgreSQL │  │    Redis    │  │  Weaviate   │  │   Neo4j     │     │
│   │  (Primary)  │  │   (Cache)   │  │   (Vector)  │  │   (Graph)   │     │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

# 💰 Cost Planning

## Infrastructure Costs (Monthly Estimate)
| Component | Specification | Est. Cost |
|-----------|--------------|-----------|
| GCP Compute | e2-standard-4 | $120/mo |
| Cloud SQL (PostgreSQL) | db-standard-2 | $80/mo |
| Redis (Memorystore) | 1GB | $35/mo |
| Kafka (Confluent) | Basic | $150/mo |
| OpenAI API | GPT-4 Turbo | $200-500/mo |
| GitHub Actions | 3000 min/mo | $40/mo |
| **Total** | | **$625-925/mo** |

## Cost Optimization Strategies
- Use GPT-3.5 for classification, GPT-4 for complex analysis
- Cache LLM responses in Redis
- Batch Kafka messages
- Auto-scaling based on incident volume

---

# 🧱 Layers

## Application Layers
```
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: PRESENTATION                                   │
│ - Next.js Frontend                                      │
│ - React Components                                      │
│ - TailwindCSS Styling                                   │
├─────────────────────────────────────────────────────────┤
│ LAYER 2: API                                            │
│ - FastAPI REST Endpoints                                │
│ - WebSocket for real-time updates                       │
│ - CORS & Authentication middleware                      │
├─────────────────────────────────────────────────────────┤
│ LAYER 3: ORCHESTRATION                                  │
│ - LangGraph State Machine                               │
│ - LLM Intelligence Module                               │
│ - Enterprise Executor                                   │
├─────────────────────────────────────────────────────────┤
│ LAYER 4: INTEGRATION                                    │
│ - MCP Servers (ServiceNow, GCP, GitHub, Jira)           │
│ - Kafka Producers/Consumers                             │
│ - External API Clients                                  │
├─────────────────────────────────────────────────────────┤
│ LAYER 5: DATA                                           │
│ - PostgreSQL (Relational)                               │
│ - Redis (Cache/Session)                                 │
│ - Weaviate (Vector Store)                               │
│ - Neo4j (Knowledge Graph)                               │
└─────────────────────────────────────────────────────────┘
```

---

# 🎯 Patterns

## Design Patterns Used

### 1. Event Sourcing
```python
# Kafka event publishing
kafka_client.publish_event(
    topic="agent.events",
    event={
        "event_type": "incident_created",
        "incident_id": incident_id,
        "timestamp": datetime.now().isoformat()
    }
)
```

### 2. State Machine (LangGraph)
```python
# 18-node workflow state machine
WORKFLOW_STEPS = [
    {"id": 1, "name": "Ingest Incident", "phase": "ingestion"},
    {"id": 2, "name": "Parse Context", "phase": "ingestion"},
    # ... 18 nodes total
]
```

### 3. Registry Pattern
```json
// registry.json - Script definitions
{
  "scripts": [
    {
      "id": "script-start-gcp-instance",
      "type": "shell",
      "path": "scripts/start_gcp_instance.sh",
      "workflow": "shell-execute.yml"
    }
  ]
}
```

### 4. Strategy Pattern (Script Execution)
```python
# Different execution strategies based on script type
if script_type == "ansible":
    return self._prepare_ansible_inputs(script, inputs)
elif script_type == "terraform":
    return self._prepare_terraform_inputs(script, inputs)
elif script_type == "shell":
    return self._prepare_shell_inputs(script, inputs)
```

---

# 📊 Data Model

## Core Entities
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Incident     │────▶│   Execution     │────▶│    Script       │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ incident_id     │     │ execution_id    │     │ script_id       │
│ short_description│    │ incident_id     │     │ name            │
│ description     │     │ script_id       │     │ type            │
│ category        │     │ status          │     │ path            │
│ priority        │     │ started_at      │     │ workflow        │
│ status          │     │ completed_at    │     │ risk_level      │
│ assigned_to     │     │ github_run_id   │     │ auto_approve    │
│ created_at      │     │ outputs         │     │ required_inputs │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                      │
         │                      │
         ▼                      ▼
┌─────────────────┐     ┌─────────────────┐
│   Approval      │     │  WorkflowState  │
├─────────────────┤     ├─────────────────┤
│ approval_id     │     │ workflow_id     │
│ execution_id    │     │ current_node    │
│ approver        │     │ status          │
│ decision        │     │ node_outputs    │
│ timestamp       │     │ created_at      │
│ comments        │     │ updated_at      │
└─────────────────┘     └─────────────────┘
```

---

# 🗄️ Database

## PostgreSQL Schema
```sql
-- Incidents table
CREATE TABLE incidents (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) UNIQUE NOT NULL,
    sys_id VARCHAR(100),
    short_description TEXT,
    description TEXT,
    category VARCHAR(100),
    priority VARCHAR(10),
    status VARCHAR(20),
    assigned_to VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Executions table
CREATE TABLE executions (
    id SERIAL PRIMARY KEY,
    execution_id UUID UNIQUE NOT NULL,
    incident_id VARCHAR(50) REFERENCES incidents(incident_id),
    script_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    environment VARCHAR(50),
    inputs JSONB,
    outputs JSONB,
    github_run_id BIGINT,
    github_run_url TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Approvals table
CREATE TABLE approvals (
    id SERIAL PRIMARY KEY,
    approval_id UUID UNIQUE NOT NULL,
    execution_id UUID REFERENCES executions(execution_id),
    approver VARCHAR(100) NOT NULL,
    decision VARCHAR(20) NOT NULL,
    comments TEXT,
    decided_at TIMESTAMP DEFAULT NOW()
);
```

## Redis Cache Structure
```
# Incident cache (TTL: 5 min)
incident:{incident_id} -> JSON

# Workflow state (TTL: 1 hour)
workflow:{workflow_id} -> JSON

# Script registry (TTL: 10 min)
registry:scripts -> JSON

# Rate limiting
ratelimit:{user_id}:{endpoint} -> count
```

---

# 🌐 API Design

## RESTful Endpoints
```yaml
# Incidents API
GET    /api/incidents              # List all incidents
GET    /api/incidents/{id}         # Get single incident
POST   /api/incidents              # Create incident
PATCH  /api/incidents/{id}         # Update incident

# LangGraph API
GET    /api/langgraph/definition   # Get workflow graph
POST   /api/langgraph/node/{id}    # Execute specific node
GET    /api/langgraph/workflow/{id} # Get workflow state

# Execution API
POST   /api/scripts/match          # Match scripts to incident
POST   /api/enterprise/execute     # Execute script via GitHub
GET    /api/executions/{id}        # Get execution status

# Approval API
POST   /api/approvals/{id}/approve # Approve execution
POST   /api/approvals/{id}/reject  # Reject execution

# MCP API
POST   /api/mcp/{server}/call      # Call MCP tool
GET    /api/mcp/{server}/tools     # List available tools
```

## API Response Format
```json
{
  "status": "success",
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid",
    "version": "3.0.0"
  }
}
```

---

# ⚙️ Config

## Environment Configuration
```bash
# .env file structure
# ============================================
# ServiceNow Configuration
SNOW_INSTANCE_URL=https://dev275804.service-now.com
SNOW_USERNAME=admin
SNOW_PASSWORD=***

# GitHub Configuration
GITHUB_TOKEN=ghp_***
GITHUB_REPO_OWNER=sam2881
GITHUB_REPO_NAME=test_01

# OpenAI Configuration
OPENAI_API_KEY=sk-***
OPENAI_MODEL=gpt-4-turbo-preview

# GCP Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
GCP_PROJECT=your-project-id

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:29092

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/ai_agent
```

## Configuration Management
- **File**: `backend/orchestrator/main.py`
- Uses `python-dotenv` for loading
- Supports multiple `.env` files (`.env`, `.env.local`)

---

# 🧠 Memory

## Memory Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    MEMORY LAYERS                        │
├─────────────────────────────────────────────────────────┤
│  SHORT-TERM (Redis)                                     │
│  - Workflow state during execution                      │
│  - Recent incident context                              │
│  - Session data                                         │
├─────────────────────────────────────────────────────────┤
│  LONG-TERM (PostgreSQL + Weaviate)                      │
│  - Historical incidents                                 │
│  - Execution history                                    │
│  - Embedded incident vectors                            │
├─────────────────────────────────────────────────────────┤
│  KNOWLEDGE (Neo4j)                                      │
│  - Service dependencies                                 │
│  - Team ownership mappings                              │
│  - Runbook relationships                                │
└─────────────────────────────────────────────────────────┘
```

## Workflow State Management
```python
# Redis-based workflow state
WORKFLOW_STATES = {}  # In-memory fallback

async def get_workflow_state(workflow_id: str) -> Dict:
    # Try Redis first
    cached = redis_client.get(f"workflow:{workflow_id}")
    if cached:
        return json.loads(cached)
    return WORKFLOW_STATES.get(workflow_id, {"steps": {}})
```

---

# 📚 RAG (Retrieval Augmented Generation)

## RAG Pipeline
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Incident   │────▶│   Embed     │────▶│  Weaviate   │
│  Description│     │  (OpenAI)   │     │   Store     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Results   │◀────│   Rank &    │◀────│   Search    │
│   (Top K)   │     │   Filter    │     │   Query     │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Node 6: RAG Search Implementation
```python
# LangGraph Node 6: RAG Search
async def rag_search(incident: Dict) -> Dict:
    # Generate embedding for incident
    embedding = await generate_embedding(incident["description"])

    # Search Weaviate
    results = weaviate_client.query(
        query_embeddings=[embedding],
        n_results=5,
        where={"category": incident["category"]}
    )

    return {
        "similar_incidents": results,
        "similarity_scores": results["distances"]
    }
```

---

# 📝 Prompts

## Prompt Templates

### Incident Classification Prompt
```python
CLASSIFICATION_PROMPT = """
Analyze this incident and classify it:

Incident: {short_description}
Description: {description}

Respond in JSON format:
{
  "platform": "gcp|aws|azure|kubernetes|other",
  "incident_type": "outage|performance|security|configuration",
  "severity": "critical|high|medium|low",
  "remediation_type": "restart|scale|config|investigate",
  "confidence": 0.0-1.0
}
"""
```

### Script Matching Prompt
```python
SCRIPT_MATCHING_PROMPT = """
Match the best remediation script for this incident:

Incident: {description}

Available Scripts:
{scripts_list}

Return the best match with extracted parameters:
{
  "script_id": "...",
  "confidence": 0.0-1.0,
  "extracted_params": {...}
}
"""
```

### Plan Safety Validation Prompt
```python
SAFETY_VALIDATION_PROMPT = """
Evaluate the safety of this execution plan:

Script: {script_name}
Action: {action}
Target: {target}
Environment: {environment}

Assess risks and provide:
{
  "is_safe": true/false,
  "risk_level": "low|medium|high|critical",
  "concerns": [...],
  "requires_approval": true/false
}
"""
```

---

# ⚖️ LLM Judge

## Judge Nodes in LangGraph
```
┌─────────────────────────────────────────────────────────┐
│                   LLM JUDGE NODES                        │
├─────────────────────────────────────────────────────────┤
│ Node 3:  Judge Log Quality                              │
│          - Evaluates incident information completeness  │
│          - Confidence score for primary error           │
├─────────────────────────────────────────────────────────┤
│ Node 5:  Judge Classification                           │
│          - Validates platform/type classification       │
│          - Cross-checks with historical data            │
├─────────────────────────────────────────────────────────┤
│ Node 7:  Judge RAG Results                              │
│          - Filters irrelevant search results            │
│          - Ranks by relevance and recency               │
├─────────────────────────────────────────────────────────┤
│ Node 11: Judge Script Selection                         │
│          - Validates script-incident match              │
│          - Checks parameter extraction                  │
├─────────────────────────────────────────────────────────┤
│ Node 13: Judge Plan Safety                              │
│          - Risk assessment                              │
│          - Approval requirements                        │
└─────────────────────────────────────────────────────────┘
```

## Judge Implementation
```python
# Node 13: Plan Safety Judge
async def judge_plan_safety(plan: Dict, script: Dict) -> Dict:
    prompt = SAFETY_VALIDATION_PROMPT.format(
        script_name=script["name"],
        action=script["action"],
        target=plan.get("target"),
        environment=plan.get("environment")
    )

    response = await llm_client.chat(prompt)

    return {
        "is_safe": response["is_safe"],
        "risk_level": response["risk_level"],
        "requires_approval": not script.get("auto_approve", False)
    }
```

---

# 🔌 MCP (Model Context Protocol)

## MCP Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    MCP CLIENT                            │
│            (backend/orchestrator/services/mcp_client.py) │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ ServiceNow  │  │    GCP      │  │   GitHub    │
│ MCP Server  │  │ MCP Server  │  │ MCP Server  │
│  Port 5001  │  │  Port 5002  │  │  Port 5003  │
└─────────────┘  └─────────────┘  └─────────────┘
      │               │               │
      ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  ServiceNow │  │  GCP APIs   │  │ GitHub API  │
│    REST API │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
```

## MCP Server Structure
```python
# mcp-servers/servicenow-mcp/server.py
@mcp.tool()
async def list_incidents(
    limit: int = 50,
    status: str = None
) -> List[Dict]:
    """List incidents from ServiceNow"""
    return await servicenow_client.get_incidents(limit, status)

@mcp.tool()
async def update_incident(
    incident_id: str,
    state: str,
    work_notes: str
) -> Dict:
    """Update incident status in ServiceNow"""
    return await servicenow_client.update(incident_id, state, work_notes)
```

---

# 🔗 Protocols

## Communication Protocols
```
┌─────────────────────────────────────────────────────────┐
│                    PROTOCOLS                             │
├─────────────────────────────────────────────────────────┤
│  HTTP/REST                                               │
│  - Frontend ↔ Backend API                               │
│  - Backend ↔ ServiceNow                                 │
│  - Backend ↔ GitHub API                                 │
├─────────────────────────────────────────────────────────┤
│  WebSocket                                               │
│  - Real-time workflow updates                           │
│  - Live log streaming                                   │
├─────────────────────────────────────────────────────────┤
│  Kafka Protocol                                          │
│  - Event streaming                                      │
│  - Incident ingestion                                   │
│  - Audit logging                                        │
├─────────────────────────────────────────────────────────┤
│  MCP (stdio/SSE)                                         │
│  - Tool communication                                   │
│  - Structured tool calls                                │
├─────────────────────────────────────────────────────────┤
│  gRPC (Optional)                                         │
│  - High-performance inter-service                       │
└─────────────────────────────────────────────────────────┘
```

---

# 🛠️ Tools

## Available Tools via MCP

### ServiceNow Tools
| Tool | Description |
|------|-------------|
| `list_incidents` | List all incidents |
| `get_incident` | Get incident details |
| `update_incident` | Update incident status |
| `add_work_notes` | Add work notes |
| `close_incident` | Close resolved incident |

### GCP Tools
| Tool | Description |
|------|-------------|
| `list_instances` | List compute instances |
| `start_instance` | Start VM instance |
| `stop_instance` | Stop VM instance |
| `get_instance_status` | Get instance status |
| `list_alerts` | List monitoring alerts |

### GitHub Tools
| Tool | Description |
|------|-------------|
| `trigger_workflow` | Dispatch GitHub Actions |
| `get_workflow_status` | Get run status |
| `list_runs` | List workflow runs |

---

# 🤖 Agents

## Agent Types
```
┌─────────────────────────────────────────────────────────┐
│                    AGENT TYPES                           │
├─────────────────────────────────────────────────────────┤
│  CLASSIFIER AGENT                                        │
│  - Analyzes incident description                        │
│  - Determines platform, type, severity                  │
│  - Uses GPT-4 for complex classification                │
├─────────────────────────────────────────────────────────┤
│  RETRIEVAL AGENT                                         │
│  - Searches historical incidents (RAG)                  │
│  - Queries knowledge graph                              │
│  - Merges context from multiple sources                 │
├─────────────────────────────────────────────────────────┤
│  REMEDIATION AGENT                                       │
│  - Matches scripts to incidents                         │
│  - Extracts required parameters                         │
│  - Generates execution plan                             │
├─────────────────────────────────────────────────────────┤
│  EXECUTOR AGENT                                          │
│  - Triggers GitHub Actions                              │
│  - Monitors execution                                   │
│  - Validates results                                    │
└─────────────────────────────────────────────────────────┘
```

---

# 🤝 Collaboration

## Multi-Agent Collaboration
```
           ┌─────────────────┐
           │   Orchestrator  │
           │    (LangGraph)  │
           └────────┬────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌────────┐    ┌────────┐    ┌────────┐
│Classify│───▶│Retrieve│───▶│Execute │
│ Agent  │    │ Agent  │    │ Agent  │
└────────┘    └────────┘    └────────┘
    │               │               │
    └───────────────┴───────────────┘
                    │
                    ▼
           ┌─────────────────┐
           │  Human Approver │
           │     (HITL)      │
           └─────────────────┘
```

## Handoff Protocol
```python
# Agent handoff in LangGraph
async def execute_node(node_id: int, state: Dict) -> Dict:
    # Get output from previous node
    prev_output = state["steps"].get(node_id - 1, {}).get("output", {})

    # Execute current node with context
    result = await node_handlers[node_id](prev_output, state)

    # Pass to next node
    state["steps"][node_id] = {"output": result}
    return state
```

---

# 🔄 Workflows

## 18-Node LangGraph Workflow
```
PHASE 1: INGESTION (Nodes 1-3)
┌────────┐    ┌────────┐    ┌────────┐
│ Ingest │───▶│ Parse  │───▶│ Judge  │
│Incident│    │Context │    │Quality │
└────────┘    └────────┘    └────────┘

PHASE 2: CLASSIFICATION (Nodes 4-5)
┌────────┐    ┌────────┐
│Classify│───▶│ Judge  │
│Incident│    │ Class  │
└────────┘    └────────┘

PHASE 3: RETRIEVAL (Nodes 6-9)
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│  RAG   │───▶│ Judge  │───▶│ Graph  │───▶│ Merge  │
│ Search │    │  RAG   │    │ Search │    │Context │
└────────┘    └────────┘    └────────┘    └────────┘

PHASE 4: SELECTION (Nodes 10-11)
┌────────┐    ┌────────┐
│ Match  │───▶│ Judge  │
│Scripts │    │ Select │
└────────┘    └────────┘

PHASE 5: PLANNING (Nodes 12-13)
┌────────┐    ┌────────┐
│Generate│───▶│ Judge  │
│  Plan  │    │ Safety │
└────────┘    └────────┘

PHASE 6: EXECUTION (Nodes 14-15)
┌────────┐    ┌────────┐
│ Human  │───▶│Execute │
│Approval│    │Pipeline│
└────────┘    └────────┘

PHASE 7: VALIDATION (Nodes 16-17)
┌────────┐    ┌────────┐
│Validate│───▶│ Close  │
│  Fix   │    │ Ticket │
└────────┘    └────────┘

PHASE 8: LEARNING (Node 18)
┌────────┐
│ Update │
│Knowledge│
└────────┘
```

---

# 🎼 Orchestration

## LangGraph Orchestrator
```python
# backend/orchestrator/main.py

LANGGRAPH_DEFINITION = {
    "nodes": [
        {"id": 1, "name": "Ingest Incident", "phase": "Ingestion", "type": "processor"},
        {"id": 2, "name": "Parse Context", "phase": "Ingestion", "type": "llm"},
        # ... 18 nodes
    ],
    "edges": [
        {"from": 1, "to": 2},
        {"from": 2, "to": 3},
        # ... sequential flow
    ],
    "phases": [
        {"name": "Ingestion", "nodes": [1, 2, 3], "color": "#3B82F6"},
        {"name": "Classification", "nodes": [4, 5], "color": "#8B5CF6"},
        # ... 8 phases
    ]
}

@app.post("/api/langgraph/node/{node_id}")
async def execute_langgraph_node(node_id: int, request: WorkflowNodeRequest):
    """Execute a specific LangGraph node with real LLM calls"""
    return await _execute_node(node_id, request.workflow_id, request.incident_id)
```

---

# 🔒 Security

## Security Architecture
```
┌─────────────────────────────────────────────────────────┐
│                  SECURITY LAYERS                         │
├─────────────────────────────────────────────────────────┤
│  NETWORK SECURITY                                        │
│  - VPC isolation                                        │
│  - Firewall rules                                       │
│  - TLS 1.3 encryption                                   │
├─────────────────────────────────────────────────────────┤
│  APPLICATION SECURITY                                    │
│  - CORS configuration                                   │
│  - Rate limiting                                        │
│  - Input validation                                     │
├─────────────────────────────────────────────────────────┤
│  SCRIPT SECURITY                                         │
│  - ShellCheck linting                                   │
│  - Dangerous pattern detection                          │
│  - Sandbox execution (GitHub Actions)                   │
├─────────────────────────────────────────────────────────┤
│  DATA SECURITY                                           │
│  - Encrypted secrets                                    │
│  - Audit logging                                        │
│  - Access control                                       │
└─────────────────────────────────────────────────────────┘
```

---

# 🔐 Auth

## Authentication Flow
```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  User   │───▶│  Login  │───▶│  Token  │───▶│ Access  │
│         │    │   Page  │    │  Issue  │    │Granted  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                    │
                    ▼
           ┌─────────────────┐
           │   OAuth/OIDC    │
           │   (Optional)    │
           └─────────────────┘
```

## Service Authentication
```python
# API key authentication for MCP servers
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/mcp"):
        api_key = request.headers.get("X-API-Key")
        if not validate_api_key(api_key):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    return await call_next(request)
```

---

# 🛡️ Guardrails

## Safety Guardrails
```python
# Dangerous patterns blocked in scripts
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "dd if=/dev/zero",
    ":(){ :|:& };:",  # Fork bomb
    "mkfs.",
    "> /dev/sd",
    "chmod 777 /"
]

# Script validation
async def validate_script_safety(script_path: str) -> Dict:
    content = open(script_path).read()

    for pattern in DANGEROUS_PATTERNS:
        if pattern in content:
            return {"safe": False, "reason": f"Dangerous pattern: {pattern}"}

    return {"safe": True}
```

## Execution Guardrails
- **Timeout**: 5-minute max execution time
- **Environment**: Sandboxed GitHub Actions runner
- **Approval**: Required for high-risk operations
- **Rollback**: Automatic rollback on failure

---

# 🔐 Secrets

## Secrets Management
```
┌─────────────────────────────────────────────────────────┐
│                 SECRETS MANAGEMENT                       │
├─────────────────────────────────────────────────────────┤
│  LOCAL DEVELOPMENT                                       │
│  - .env files (gitignored)                              │
│  - python-dotenv loading                                │
├─────────────────────────────────────────────────────────┤
│  GITHUB ACTIONS                                          │
│  - Repository secrets                                   │
│  - Environment secrets                                  │
│  - OIDC for GCP authentication                          │
├─────────────────────────────────────────────────────────┤
│  PRODUCTION                                              │
│  - Google Secret Manager (recommended)                  │
│  - HashiCorp Vault (alternative)                        │
│  - Environment variables in GKE                         │
└─────────────────────────────────────────────────────────┘
```

## GitHub Secrets Configuration
```yaml
# Required secrets in GitHub repository
SNOWINSTANCEURL: ServiceNow instance URL
SNOWUSERNAME: ServiceNow username
SNOWPASSWORD: ServiceNow password
GCPSERVICEACCOUNTKEY: GCP service account JSON
```

---

# 📊 Data Gov (Data Governance)

## Data Governance Framework
```
┌─────────────────────────────────────────────────────────┐
│               DATA GOVERNANCE                            │
├─────────────────────────────────────────────────────────┤
│  DATA CLASSIFICATION                                     │
│  - Public: System metrics, logs                         │
│  - Internal: Incident details, execution logs           │
│  - Confidential: Credentials, PII                       │
│  - Restricted: API keys, tokens                         │
├─────────────────────────────────────────────────────────┤
│  DATA LINEAGE                                            │
│  - Kafka event sourcing                                 │
│  - Execution audit trail                                │
│  - Workflow state history                               │
├─────────────────────────────────────────────────────────┤
│  DATA RETENTION                                          │
│  - Incidents: 2 years                                   │
│  - Executions: 1 year                                   │
│  - Logs: 90 days                                        │
│  - Metrics: 30 days                                     │
└─────────────────────────────────────────────────────────┘
```

---

# 🔌 API Gov (API Governance)

## API Standards
```yaml
# API versioning
/api/v1/incidents     # Version 1
/api/v2/incidents     # Version 2 (future)

# Response format
{
  "status": "success|error",
  "data": {},
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "version": "3.0.0"
  },
  "errors": []  # Only if status=error
}

# Rate limiting
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1609459200
```

## API Documentation
- **OpenAPI/Swagger**: Auto-generated from FastAPI
- **Access**: `http://localhost:8000/docs`

---

# 🏗️ System

## System Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Storage | 20 GB SSD | 50 GB SSD |
| Network | 100 Mbps | 1 Gbps |

## System Components
```
┌─────────────────────────────────────────────────────────┐
│                 SYSTEM COMPONENTS                        │
├─────────────────────────────────────────────────────────┤
│  APPLICATION SERVERS                                     │
│  - Backend Orchestrator (Python/FastAPI)                │
│  - Frontend (Next.js/Node.js)                           │
│  - MCP Servers (Python)                                 │
├─────────────────────────────────────────────────────────┤
│  DATA SERVICES                                           │
│  - PostgreSQL 15                                        │
│  - Redis 7                                              │
│  - Kafka (Confluent)                                    │
├─────────────────────────────────────────────────────────┤
│  EXTERNAL SERVICES                                       │
│  - OpenAI API                                           │
│  - ServiceNow                                           │
│  - GitHub Actions                                       │
│  - GCP                                                  │
└─────────────────────────────────────────────────────────┘
```

---

# 🚀 Deploy

## Deployment Architecture
```
┌─────────────────────────────────────────────────────────┐
│                GCP DEPLOYMENT                            │
├─────────────────────────────────────────────────────────┤
│  COMPUTE                                                 │
│  - GCE: Backend + Frontend                              │
│  - Cloud Run (alternative): Containerized               │
│  - GKE (production): Kubernetes cluster                 │
├─────────────────────────────────────────────────────────┤
│  DATA                                                    │
│  - Cloud SQL: PostgreSQL                                │
│  - Memorystore: Redis                                   │
│  - Confluent Cloud: Kafka                               │
├─────────────────────────────────────────────────────────┤
│  NETWORKING                                              │
│  - VPC: Private network                                 │
│  - Cloud Load Balancer                                  │
│  - Cloud CDN (static assets)                            │
└─────────────────────────────────────────────────────────┘
```

## Docker Deployment
```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...

  frontend:
    build: ./frontend
    ports:
      - "3002:3002"

  kafka:
    image: confluentinc/cp-kafka:latest
    ports:
      - "29092:29092"

  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

---

# ✅ Deploy Checklist

## Pre-Deployment Checklist
- [ ] All environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificates installed
- [ ] GitHub secrets configured
- [ ] GCP service account created
- [ ] Kafka topics created
- [ ] Redis connection tested
- [ ] OpenAI API key valid
- [ ] ServiceNow credentials tested

## Post-Deployment Checklist
- [ ] Health endpoints responding
- [ ] Frontend accessible
- [ ] API endpoints working
- [ ] Kafka producing/consuming
- [ ] GitHub Actions triggering
- [ ] Monitoring dashboards configured
- [ ] Alerting rules set up
- [ ] Backup jobs scheduled

---

# 🕸️ Service Mesh

## Service Mesh Architecture (Optional)
```
┌─────────────────────────────────────────────────────────┐
│                 ISTIO SERVICE MESH                       │
├─────────────────────────────────────────────────────────┤
│  TRAFFIC MANAGEMENT                                      │
│  - Load balancing                                       │
│  - Traffic splitting                                    │
│  - Canary deployments                                   │
├─────────────────────────────────────────────────────────┤
│  SECURITY                                                │
│  - mTLS between services                                │
│  - Authorization policies                               │
├─────────────────────────────────────────────────────────┤
│  OBSERVABILITY                                           │
│  - Distributed tracing (Jaeger)                         │
│  - Metrics (Prometheus)                                 │
│  - Access logging                                       │
└─────────────────────────────────────────────────────────┘
```

---

# 🛡️ DR (Disaster Recovery)

## Disaster Recovery Plan
```
┌─────────────────────────────────────────────────────────┐
│                DISASTER RECOVERY                         │
├─────────────────────────────────────────────────────────┤
│  RPO (Recovery Point Objective): 1 hour                 │
│  RTO (Recovery Time Objective): 4 hours                 │
├─────────────────────────────────────────────────────────┤
│  BACKUP STRATEGY                                         │
│  - Database: Daily snapshots, hourly WAL               │
│  - Redis: RDB snapshots every 6 hours                  │
│  - Kafka: Multi-zone replication                       │
├─────────────────────────────────────────────────────────┤
│  FAILOVER STRATEGY                                       │
│  - Multi-region deployment                              │
│  - Automated health checks                              │
│  - DNS failover                                         │
└─────────────────────────────────────────────────────────┘
```

---

# 📊 Capacity

## Capacity Planning
| Metric | Current | Target | Max |
|--------|---------|--------|-----|
| Incidents/day | 50 | 200 | 1000 |
| Concurrent workflows | 5 | 20 | 100 |
| API requests/min | 100 | 500 | 2000 |
| Storage/month | 5 GB | 20 GB | 100 GB |

## Scaling Strategy
- **Horizontal**: Add more backend instances
- **Vertical**: Increase instance size
- **Auto-scaling**: Based on CPU/memory metrics

---

# 💰 FinOps

## Cost Monitoring
```
┌─────────────────────────────────────────────────────────┐
│                    FINOPS                                │
├─────────────────────────────────────────────────────────┤
│  COST TRACKING                                           │
│  - GCP Billing Dashboard                                │
│  - OpenAI Usage Dashboard                               │
│  - Budget alerts at 50%, 80%, 100%                      │
├─────────────────────────────────────────────────────────┤
│  COST OPTIMIZATION                                       │
│  - Committed use discounts (GCP)                        │
│  - Preemptible VMs for dev/test                         │
│  - LLM response caching                                 │
│  - Right-sizing instances                               │
├─────────────────────────────────────────────────────────┤
│  COST ALLOCATION                                         │
│  - Labels by environment (dev/staging/prod)             │
│  - Labels by team                                       │
│  - Monthly cost reports                                 │
└─────────────────────────────────────────────────────────┘
```

---

# ⚡ CI/CD

## CI/CD Pipeline
```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Code   │───▶│  Build  │───▶│  Test   │───▶│ Deploy  │
│  Push   │    │         │    │         │    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ GitHub  │    │ Docker  │    │  Unit   │    │ Staging │
│  Push   │    │  Build  │    │  Tests  │    │   Env   │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

## GitHub Actions Workflows
```yaml
# .github/workflows/ci.yml
name: CI Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest
      - name: Build Docker
        run: docker build -t ai-agent .
```

---

# 🔨 Build

## Build Process
```bash
# Backend build
cd backend
pip install -r requirements.txt
python -m pytest

# Frontend build
cd frontend
npm install
npm run build
npm run test
```

## Docker Build
```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0"]
```

---

# 🔄 LLMOps

## LLM Operations
```
┌─────────────────────────────────────────────────────────┐
│                     LLMOPS                               │
├─────────────────────────────────────────────────────────┤
│  MODEL MANAGEMENT                                        │
│  - Primary: GPT-4-turbo-preview                         │
│  - Fallback: GPT-3.5-turbo                              │
│  - Local: Ollama (optional)                             │
├─────────────────────────────────────────────────────────┤
│  PROMPT MANAGEMENT                                       │
│  - Version-controlled prompts                           │
│  - A/B testing capability                               │
│  - Prompt performance metrics                           │
├─────────────────────────────────────────────────────────┤
│  COST MANAGEMENT                                         │
│  - Token usage tracking                                 │
│  - Response caching                                     │
│  - Model selection by complexity                        │
├─────────────────────────────────────────────────────────┤
│  QUALITY MANAGEMENT                                      │
│  - Response validation                                  │
│  - Hallucination detection                              │
│  - Human feedback loop                                  │
└─────────────────────────────────────────────────────────┘
```

---

# 📈 Observe (Observability)

## Observability Stack
```
┌─────────────────────────────────────────────────────────┐
│                  OBSERVABILITY                           │
├─────────────────────────────────────────────────────────┤
│  METRICS (Prometheus + Grafana)                          │
│  - API latency                                          │
│  - Workflow duration                                    │
│  - LLM token usage                                      │
│  - Error rates                                          │
├─────────────────────────────────────────────────────────┤
│  LOGGING (Structured Logs)                               │
│  - JSON structured logs                                 │
│  - Correlation IDs                                      │
│  - Log aggregation                                      │
├─────────────────────────────────────────────────────────┤
│  TRACING (Distributed Tracing)                           │
│  - Request tracing                                      │
│  - Workflow step timing                                 │
│  - External API calls                                   │
└─────────────────────────────────────────────────────────┘
```

## Prometheus Metrics
```python
# backend/orchestrator/metrics.py
from prometheus_client import Counter, Histogram, Gauge

workflow_executions = Counter(
    'workflow_executions_total',
    'Total workflow executions',
    ['status', 'incident_type']
)

node_duration = Histogram(
    'langgraph_node_duration_seconds',
    'LangGraph node execution duration',
    ['node_id', 'node_name']
)
```

---

# 📊 Analytics

## Analytics Dashboard
```
┌─────────────────────────────────────────────────────────┐
│                  ANALYTICS                               │
├─────────────────────────────────────────────────────────┤
│  INCIDENT ANALYTICS                                      │
│  - Incidents by category/priority                       │
│  - Resolution time trends                               │
│  - Auto-resolution rate                                 │
├─────────────────────────────────────────────────────────┤
│  WORKFLOW ANALYTICS                                      │
│  - Success/failure rates                                │
│  - Average workflow duration                            │
│  - Node-level performance                               │
├─────────────────────────────────────────────────────────┤
│  SCRIPT ANALYTICS                                        │
│  - Most used scripts                                    │
│  - Script success rates                                 │
│  - Execution time trends                                │
├─────────────────────────────────────────────────────────┤
│  LLM ANALYTICS                                           │
│  - Classification accuracy                              │
│  - Script matching precision                            │
│  - Token usage trends                                   │
└─────────────────────────────────────────────────────────┘
```

---

# 🚦 Features

## Feature Flags
```python
# Feature flag configuration
FEATURES = {
    "llm_classification": True,      # Use LLM for classification
    "auto_approve_low_risk": True,   # Auto-approve low-risk scripts
    "graph_visualization": True,     # Enable graph view
    "real_time_updates": True,       # WebSocket updates
    "rag_search": True,              # RAG for similar incidents
    "multi_agent": False,            # Multi-agent collaboration (beta)
}
```

## Feature Rollout Strategy
- **Development**: All features enabled
- **Staging**: Production parity + beta features
- **Production**: Gradual rollout with monitoring

---

# 🚨 Incidents

## Incident Management
```
┌─────────────────────────────────────────────────────────┐
│               INCIDENT WORKFLOW                          │
├─────────────────────────────────────────────────────────┤
│  1. DETECTION                                            │
│     - ServiceNow integration                            │
│     - GCP monitoring alerts                             │
│     - Manual creation                                   │
├─────────────────────────────────────────────────────────┤
│  2. TRIAGE                                               │
│     - LLM classification                                │
│     - Priority assignment                               │
│     - Team routing                                      │
├─────────────────────────────────────────────────────────┤
│  3. REMEDIATION                                          │
│     - Script matching                                   │
│     - Execution planning                                │
│     - GitHub Actions execution                          │
├─────────────────────────────────────────────────────────┤
│  4. RESOLUTION                                           │
│     - Validation                                        │
│     - Ticket closure                                    │
│     - Knowledge update                                  │
└─────────────────────────────────────────────────────────┘
```

---

# 📋 SLA/SLO

## Service Level Objectives
| Metric | Target | Critical |
|--------|--------|----------|
| API Availability | 99.9% | 99.5% |
| API Latency (p95) | < 500ms | < 2s |
| Workflow Success Rate | > 95% | > 90% |
| Incident Resolution Time | < 30min | < 2hr |
| LLM Response Time | < 3s | < 10s |

## SLA Monitoring
```yaml
# Alerting rules
- alert: HighAPILatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
  for: 5m
  labels:
    severity: warning

- alert: LowWorkflowSuccessRate
  expr: rate(workflow_executions_total{status="success"}[1h]) / rate(workflow_executions_total[1h]) < 0.90
  for: 15m
  labels:
    severity: critical
```

---

# 🧪 Testing

## Testing Strategy
```
┌─────────────────────────────────────────────────────────┐
│                  TESTING PYRAMID                         │
├─────────────────────────────────────────────────────────┤
│  UNIT TESTS (70%)                                        │
│  - Function-level tests                                 │
│  - Mocked dependencies                                  │
│  - Fast execution                                       │
├─────────────────────────────────────────────────────────┤
│  INTEGRATION TESTS (20%)                                 │
│  - API endpoint tests                                   │
│  - Database integration                                 │
│  - Kafka integration                                    │
├─────────────────────────────────────────────────────────┤
│  E2E TESTS (10%)                                         │
│  - Full workflow tests                                  │
│  - UI interaction tests                                 │
│  - Cross-service tests                                  │
└─────────────────────────────────────────────────────────┘
```

## Test Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_orchestrator.py
```

---

# ⚡ Performance

## Performance Optimization
```
┌─────────────────────────────────────────────────────────┐
│              PERFORMANCE OPTIMIZATIONS                   │
├─────────────────────────────────────────────────────────┤
│  CACHING                                                 │
│  - Redis for frequent queries                           │
│  - LLM response caching                                 │
│  - Registry caching                                     │
├─────────────────────────────────────────────────────────┤
│  ASYNC PROCESSING                                        │
│  - Async/await throughout                               │
│  - Non-blocking I/O                                     │
│  - Parallel node execution (where possible)             │
├─────────────────────────────────────────────────────────┤
│  DATABASE OPTIMIZATION                                   │
│  - Connection pooling                                   │
│  - Query optimization                                   │
│  - Proper indexing                                      │
└─────────────────────────────────────────────────────────┘
```

## Performance Benchmarks
| Operation | Average | P95 | P99 |
|-----------|---------|-----|-----|
| API Request | 50ms | 150ms | 300ms |
| LLM Call | 1.5s | 3s | 5s |
| Workflow (18 nodes) | 30s | 60s | 120s |
| Script Execution | 45s | 90s | 180s |

---

# 🎲 LLM Eval

## LLM Evaluation Framework
```
┌─────────────────────────────────────────────────────────┐
│                  LLM EVALUATION                          │
├─────────────────────────────────────────────────────────┤
│  CLASSIFICATION ACCURACY                                 │
│  - Platform detection: 92%                              │
│  - Incident type: 88%                                   │
│  - Severity: 85%                                        │
├─────────────────────────────────────────────────────────┤
│  SCRIPT MATCHING                                         │
│  - Precision: 90%                                       │
│  - Recall: 85%                                          │
│  - F1 Score: 87%                                        │
├─────────────────────────────────────────────────────────┤
│  PARAMETER EXTRACTION                                    │
│  - Accuracy: 95%                                        │
│  - Missing rate: 3%                                     │
├─────────────────────────────────────────────────────────┤
│  SAFETY ASSESSMENT                                       │
│  - False positive rate: 5%                              │
│  - False negative rate: 1%                              │
└─────────────────────────────────────────────────────────┘
```

## Evaluation Dataset
```python
# test_cases/classification.json
[
    {
        "incident": "GCP VM terminated unexpectedly",
        "expected": {
            "platform": "gcp",
            "type": "outage",
            "severity": "high"
        }
    },
    ...
]
```

---

# 🤝 HITL (Human-in-the-Loop)

## HITL Workflow
```
┌─────────────────────────────────────────────────────────┐
│                 HUMAN-IN-THE-LOOP                        │
├─────────────────────────────────────────────────────────┤
│  APPROVAL TRIGGERS                                       │
│  - High-risk scripts                                    │
│  - Production environment                               │
│  - Low confidence matches                               │
│  - New/unknown incident types                           │
├─────────────────────────────────────────────────────────┤
│  APPROVAL INTERFACE                                      │
│  - Script details                                       │
│  - Risk assessment                                      │
│  - Extracted parameters                                 │
│  - Approve/Reject buttons                               │
├─────────────────────────────────────────────────────────┤
│  APPROVAL WORKFLOW                                       │
│  1. System pauses at Node 14                            │
│  2. Notification sent to approver                       │
│  3. Approver reviews details                            │
│  4. Approve → Continue to Node 15                       │
│  5. Reject → Workflow ends                              │
└─────────────────────────────────────────────────────────┘
```

## Frontend Approval UI
```typescript
// EnterpriseIncidentDetail.tsx
{awaitingApproval && (
  <div className="bg-yellow-50 border p-4">
    <h3>Human Approval Required</h3>
    <p>Script: {selectedScript.name}</p>
    <p>Risk Level: {selectedScript.risk_level}</p>
    <Button onClick={handleApprove}>Approve</Button>
    <Button onClick={handleReject}>Reject</Button>
  </div>
)}
```

---

# 🔬 Analysis

## Incident Analysis Pipeline
```
┌─────────────────────────────────────────────────────────┐
│                INCIDENT ANALYSIS                         │
├─────────────────────────────────────────────────────────┤
│  1. TEXT ANALYSIS                                        │
│     - NLP processing                                    │
│     - Entity extraction                                 │
│     - Keyword identification                            │
├─────────────────────────────────────────────────────────┤
│  2. PATTERN MATCHING                                     │
│     - Regex patterns                                    │
│     - Error code extraction                             │
│     - Service identification                            │
├─────────────────────────────────────────────────────────┤
│  3. LLM ANALYSIS                                         │
│     - Context understanding                             │
│     - Root cause inference                              │
│     - Remediation suggestion                            │
├─────────────────────────────────────────────────────────┤
│  4. HISTORICAL ANALYSIS                                  │
│     - Similar incident search                           │
│     - Resolution patterns                               │
│     - Success rate by approach                          │
└─────────────────────────────────────────────────────────┘
```

---

# 🎨 UI Builder

## Frontend Components
```
┌─────────────────────────────────────────────────────────┐
│                  UI COMPONENTS                           │
├─────────────────────────────────────────────────────────┤
│  PAGES                                                   │
│  - /incidents          - Incident list                  │
│  - /incidents/[id]     - Incident detail                │
│  - /graph/[id]         - Workflow visualization         │
│  - /approvals          - Approval queue                 │
│  - /workflows          - Workflow history               │
├─────────────────────────────────────────────────────────┤
│  COMPONENTS                                              │
│  - EnterpriseIncidentDetail                             │
│  - GraphView                                            │
│  - WorkflowSteps                                        │
│  - ApprovalPanel                                        │
│  - ScriptMatchList                                      │
├─────────────────────────────────────────────────────────┤
│  DESIGN SYSTEM                                           │
│  - TailwindCSS                                          │
│  - Lucide React Icons                                   │
│  - Custom Badge/Button components                       │
└─────────────────────────────────────────────────────────┘
```

## Graph Visualization
```typescript
// GraphView component features
- Interactive SVG-based visualization
- 18 nodes in flowchart layout
- Color-coded phases
- Real-time status updates
- Zoom controls
- Node tooltips
- Phase progress bars
```

---

# Summary

## Key Implementation Files
| Area | File |
|------|------|
| Orchestrator | `backend/orchestrator/main.py` |
| LLM Intelligence | `backend/orchestrator/llm_intelligence.py` |
| Enterprise Executor | `backend/orchestrator/enterprise_executor.py` |
| MCP Client | `backend/orchestrator/services/mcp_client.py` |
| Frontend | `frontend/src/components/incidents/EnterpriseIncidentDetail.tsx` |
| Graph View | `frontend/src/app/graph/[id]/page.tsx` |
| Script Registry | `registry.json` |
| GitHub Workflows | `.github/workflows/shell-execute.yml` |

## Technology Stack
- **Backend**: Python 3.11, FastAPI, LangGraph
- **Frontend**: Next.js 14, React 18, TailwindCSS
- **LLM**: OpenAI GPT-4-turbo
- **Database**: PostgreSQL, Redis, Weaviate
- **Streaming**: Apache Kafka
- **Execution**: GitHub Actions
- **Cloud**: Google Cloud Platform

---

*Document Generated: December 2024*
*Version: 3.0.0*
