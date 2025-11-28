# AI Agent Platform - Enterprise Incident Remediation

> Intelligent, Event-Driven AI Agent for Automated Incident Management with Human-in-the-Loop Workflows

**Version:** 2.0.0
**Last Updated:** 2025-11-28

---

## Overview

Enterprise-grade AI platform that automatically detects, analyzes, and remediates IT incidents using machine learning and runbook automation.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **Event-Driven Architecture** | Kafka-based real-time incident processing |
| **AI-Powered Analysis** | GPT-4 LLM for incident understanding and root cause detection |
| **Hybrid RAG Matching** | Vector + Graph + Metadata runbook matching (Weaviate + Neo4j) |
| **Real Execution** | Execute Ansible, Terraform, Shell, K8s on actual infrastructure |
| **Auto-Fill Parameters** | AI extracts VM names, zones, namespaces from incident text |
| **Human-in-the-Loop** | Risk-based approval workflows for medium/high/critical actions |
| **Continuous Learning** | Successful remediations saved to RAG for future recommendations |

---

## 8-Step Remediation Workflow

```
DETECT → ANALYZE → MATCH → PLAN → APPROVE → EXECUTE → VALIDATE → LEARN
```

| Step | Description | Technology |
|------|-------------|------------|
| 1. **Detect** | Incident ingested from ServiceNow/GCP | Kafka Events |
| 2. **Analyze** | AI extracts service, component, root cause | GPT-4 LLM |
| 3. **Match** | Find relevant runbooks | Weaviate + Neo4j |
| 4. **Plan** | Generate execution plan with rollback steps | LLM + Registry |
| 5. **Approve** | Human approval for medium/high risk | HITL API |
| 6. **Execute** | Run script on infrastructure | subprocess, GCP API |
| 7. **Validate** | Verify fix worked | Post-execution checks |
| 8. **Learn** | Save to RAG for future use | Weaviate indexing |

---

## Architecture

```
                           AI AGENT PLATFORM
                      Enterprise Incident Remediation

+---------------+            +---------------------+            +---------------+
|  ServiceNow   |----------->|  Backend Orchestrator|<----------|   GCP         |
|   Incidents   |   API/Kafka |  http://localhost   |  Alerts   |   Monitoring  |
+---------------+            |       :8000         |            +---------------+
                             +---------+-----------+
                                       |
          +----------------------------+----------------------------+
          |                            |                            |
          v                            v                            v
+------------------+         +------------------+         +------------------+
|     KAFKA        |         |   AI/ML Layer    |         |   Databases      |
|                  |         |                  |         |                  |
| servicenow.      |         | - GPT-4 LLM      |         | - Weaviate (RAG) |
|   incidents      |         | - Embeddings     |         | - Neo4j (Graph)  |
| gcp.alerts       |         | - RAG Search     |         | - Postgres       |
| agent.events     |         |                  |         | - Redis (Cache)  |
+------------------+         +------------------+         +------------------+
          |
          v
+--------------------------------------------------------------------------+
|                KAFKA CONSUMER (incident_consumer.py)                      |
|                                                                           |
|  - Subscribes to: servicenow.incidents, gcp.alerts                       |
|  - Auto-processes incidents with LLM analysis                             |
|  - Matches runbooks using hybrid RAG                                      |
|  - Publishes results to agent.events                                      |
|  - Auto-remediates LOW risk incidents (optional)                          |
+--------------------------------------------------------------------------+
          |
          v
+------------------+
|    Frontend      |
|  React Dashboard |
|  localhost:3002  |
+------------------+
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.9+
- Node.js 18+
- GCP Service Account (for GCP operations)
- ServiceNow Developer Instance
- OpenAI API Key

### 1. Clone and Setup

```bash
cd /home/samrattidke600/ai_agent_app

# Install Python dependencies
pip3 install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Start Infrastructure (Docker)

```bash
cd deployment
sudo docker compose up -d

# Services started: Kafka, Postgres, Neo4j, Weaviate, Redis, Grafana
```

### 3. Start Backend

```bash
cd backend

# Set environment variables
export KAFKA_BOOTSTRAP_SERVERS=localhost:29092
export SNOW_INSTANCE_URL="https://your-instance.service-now.com"
export SNOW_USERNAME="admin"
export SNOW_PASSWORD="your-password"
export OPENAI_API_KEY="your-openai-key"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/gcp-key.json"
export GITHUB_TOKEN="your-github-token"
export NEO4J_PASSWORD="adminadmin"
export USE_ENTERPRISE_MATCHER=true

# Start API server
python3 orchestrator/main.py
```

### 4. Start Kafka Consumer (Continuous Processing)

```bash
cd backend
python3 streaming/incident_consumer.py
```

### 5. Start Frontend

```bash
cd frontend
npm run start
```

---

## Service URLs

| Service | Local URL | External URL (GCP) |
|---------|-----------|-------------------|
| **Frontend Dashboard** | http://localhost:3002 | http://34.171.221.200:3002 |
| **Backend API** | http://localhost:8000 | http://34.171.221.200:8000 |
| **API Documentation** | http://localhost:8000/docs | - |
| **Kafka UI** | http://localhost:8085 | http://34.171.221.200:8085 |
| **Grafana** | http://localhost:3000 | http://34.171.221.200:3000 |
| **Neo4j Browser** | http://localhost:7474 | http://34.171.221.200:7474 |

---

## API Endpoints

### Incidents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/incidents` | List incidents (publishes to Kafka) |
| GET | `/api/incidents/{id}` | Get incident details |

### Remediation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/remediation/full` | Run full AI remediation analysis |
| GET | `/api/remediation/runbooks` | List available runbooks |
| POST | `/api/runbooks/{id}/execute-real` | Execute runbook on infrastructure |
| POST | `/api/runbooks/sync-from-github` | Sync runbooks from GitHub |

### HITL Approvals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/hitl/approvals/pending` | Get pending approvals |
| POST | `/api/hitl/approvals/{id}/approve-plan` | Approve remediation |
| POST | `/api/hitl/approvals/{id}/reject-plan` | Reject remediation |

---

## Enterprise Runbook Registry

Pre-built runbooks for common incident types:

| ID | Name | Type | Risk | Auto-Approve |
|----|------|------|------|--------------|
| script-start-gcp-instance | Start GCP VM Instance | Shell | Low | Yes |
| ansible-restart-kubernetes-pod | Restart K8s Pod | Ansible | Low | Yes |
| k8s-restart-deployment | Restart K8s Deployment | K8s | Low | Yes |
| ansible-restart-nginx | Restart Nginx | Ansible | Low | Yes |
| script-clear-disk-space | Clear Disk Space | Shell | Low | Yes |
| ansible-restart-airflow-scheduler | Restart Airflow Scheduler | Ansible | Medium | No |
| ansible-fix-database-cpu | Fix Database CPU | Ansible | Medium | No |
| ansible-flush-redis-cache | Flush Redis Cache | Ansible | Medium | No |
| ansible-scale-gcp-instance | Scale GCP VM | Ansible | High | No |
| terraform-create-firewall-rule | Create Firewall Rule | Terraform | Critical | No |

---

## Kafka Topics

| Topic | Purpose | Producer | Consumer |
|-------|---------|----------|----------|
| `servicenow.incidents` | ServiceNow incident events | Backend API | Incident Consumer |
| `gcp.alerts` | GCP monitoring alerts | GCP Monitor | Incident Consumer |
| `agent.events` | AI agent decisions & actions | Consumer | Dashboard, Logging |
| `hitl.approvals` | Human approval requests | Backend | Approval Service |

---

## Technology Stack

### Backend
- **Python 3.9+** - Core language
- **FastAPI** - API framework
- **OpenAI GPT-4** - LLM for analysis
- **Apache Kafka** - Event streaming
- **Weaviate** - Vector DB for RAG
- **Neo4j** - Graph DB for relationships
- **PostgreSQL** - State storage
- **Redis** - Caching

### Frontend
- **React 18** - UI framework
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **TailwindCSS** - Styling
- **TanStack Query** - Data fetching

### Execution
- **Ansible** - Playbook execution
- **Terraform** - Infrastructure as Code
- **Shell Scripts** - Direct commands
- **GCP SDK** - Cloud operations

---

## Project Structure

```
ai_agent_app/
├── backend/
│   ├── orchestrator/
│   │   └── main.py              # FastAPI server
│   ├── agents/
│   │   └── remediation/
│   │       └── agent.py         # AI remediation engine
│   ├── streaming/
│   │   ├── incident_consumer.py # Kafka consumer
│   │   └── servicenow_producer.py
│   ├── runbooks/
│   │   ├── registry.json        # Runbook catalog
│   │   ├── scripts/             # Shell scripts
│   │   ├── ansible/             # Ansible playbooks
│   │   └── terraform/           # Terraform configs
│   └── utils/
│       ├── kafka_client.py
│       ├── redis_client.py
│       └── weaviate_client.py
├── frontend/
│   └── src/
│       ├── components/
│       │   └── incidents/
│       │       └── RemediationPanel.tsx
│       └── lib/
│           └── api.ts
├── deployment/
│   └── docker-compose.yml
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
└── docs/
    └── ARCHITECTURE.md
```

---

## Security & Governance

### Risk-Based Approval Matrix

| Risk Level | Auto-Approve | Approvers Required |
|------------|--------------|-------------------|
| Low | Yes | None |
| Medium | No | 1 approver |
| High | No | 2 approvers |
| Critical | No | 2 approvers + manager |

### Authentication

| Service | Auth Method |
|---------|-------------|
| ServiceNow | HTTP Basic Auth |
| GCP | Service Account JSON |
| GitHub | Personal Access Token |
| OpenAI | API Key |

---

## Integrations

### ServiceNow
- Incident synchronization
- Automated ticket updates
- Resolution tracking

### GCP
- VM instance management (start/stop/scale)
- Firewall rule creation
- Service account authentication

### GitHub
- Runbook repository sync
- PR creation for code changes
- Branch management

### Jira
- Story/ticket tracking
- Code generation workflow
- PR linking

---

## Testing

```bash
# Test API health
curl http://localhost:8000/health

# Test remediation flow
curl -X POST "http://localhost:8000/api/remediation/full" \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "INC0010001", "mode": "analyze"}'

# Check Kafka topics
sudo docker exec deployment-kafka-1 kafka-topics --list --bootstrap-server localhost:9092
```

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Detailed system design, data flows, and components

---

## License

Proprietary - Internal Use Only
