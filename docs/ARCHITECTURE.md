# AI Agent Platform - System Architecture

> Enterprise-grade, Event-Driven AI Agent Platform for Automated Incident Remediation

**Version:** 3.0.0
**Last Updated:** 2025-12-04

---

## Table of Contents

1. [Overview](#overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Event-Driven Architecture (Kafka)](#event-driven-architecture-kafka)
4. [Core Components](#core-components)
5. [Enhanced RAG Pipeline](#enhanced-rag-pipeline)
6. [Multi-Source Incidents](#multi-source-incidents)
7. [Automatic Rollback Plans](#automatic-rollback-plans)
8. [Data Flow](#data-flow)
9. [8-Step Remediation Workflow](#8-step-remediation-workflow)
10. [Enterprise Runbook Matching](#enterprise-runbook-matching)
11. [Technology Stack](#technology-stack)
12. [API Endpoints](#api-endpoints)
13. [Security & Governance](#security--governance)

---

## Overview

This platform is an enterprise AI-powered incident management system that:

- **Automatically detects** incidents from ServiceNow and GCP
- **Analyzes** incidents using GPT-4 LLM
- **Matches** appropriate runbooks using hybrid RAG (Vector + Graph + Metadata)
- **Executes** remediation scripts on real infrastructure
- **Learns** from successful remediations for future use

### Key Features

| Feature | Description |
|---------|-------------|
| **Event-Driven** | Kafka-based real-time incident processing |
| **AI Analysis** | GPT-4 powered incident understanding |
| **Enhanced Hybrid RAG** | Semantic (60%) + Keyword TF-IDF (30%) + Metadata (10%) |
| **Cross-Encoder Re-ranking** | ms-marco model for 20-30% precision improvement |
| **Local Embeddings** | SentenceTransformers - FREE, no API cost |
| **Smart Chunking** | Script-type aware chunking (Ansible, Terraform, Shell, K8s) |
| **Real Execution** | Ansible, Terraform, Shell, Kubernetes scripts |
| **Auto-Fill Parameters** | AI extracts VM names, zones from incident text |
| **HITL Approvals** | Human-in-the-Loop for high-risk actions |
| **Automatic Rollback** | Generated rollback plans for all executions |
| **Multi-Source Incidents** | Datadog, Prometheus, CloudWatch, PagerDuty connectors |
| **Continuous Learning** | ML-based weight optimization from execution outcomes |

---

## High-Level Architecture

```
                              AI AGENT PLATFORM
                         Enterprise Incident Remediation

                              +---------------------+
                              |    Frontend (React) |
                              |   http://localhost  |
                              |       :3002         |
                              +---------+-----------+
                                        |
                                        v
+---------------+             +---------------------+             +---------------+
|  ServiceNow   |------------>|  Backend Orchestrator|<-----------|   GCP         |
|   Incidents   |             |  http://localhost   |             |   Alerts      |
+---------------+             |       :8000         |             +---------------+
                              +---------+-----------+
                                        |
          +-----------------------------+-----------------------------+
          |                             |                             |
          v                             v                             v
+-----------------+           +-----------------+           +-----------------+
|     KAFKA       |           |    AI/ML Layer  |           |   Databases     |
|                 |           |                 |           |                 |
| servicenow.     |           | - GPT-4 LLM     |           | - Weaviate (RAG)|
|   incidents     |           | - Embeddings    |           | - Neo4j (Graph) |
| gcp.alerts      |           | - RAG Search    |           | - Postgres      |
| agent.events    |           |                 |           | - Redis (Cache) |
+-----------------+           +-----------------+           +-----------------+
          |
          v
+-----------------------------------------------------------------------------+
|                    KAFKA CONSUMER (incident_consumer.py)                     |
|                                                                              |
|  - Subscribes to: servicenow.incidents, gcp.alerts                          |
|  - Auto-processes incidents with LLM                                         |
|  - Matches runbooks (RAG)                                                    |
|  - Publishes results to agent.events                                         |
|  - Auto-remediates LOW risk incidents (optional)                             |
+-----------------------------------------------------------------------------+
```

---

## Event-Driven Architecture (Kafka)

The platform uses Apache Kafka for real-time, event-driven processing.

### Kafka Topics

| Topic | Purpose | Producer | Consumer |
|-------|---------|----------|----------|
| `servicenow.incidents` | ServiceNow incident events | Backend API, ServiceNow Producer | Incident Consumer |
| `gcp.alerts` | GCP monitoring alerts | GCP Monitor | Incident Consumer |
| `agent.events` | AI agent decisions & actions | Incident Consumer, Backend | Dashboard, Logging |
| `hitl.approvals` | Human approval requests | Backend | Approval Service |
| `workflow.execution` | Workflow execution events | Backend | Monitoring |

### Data Flow Through Kafka

```
1. INCIDENT INGESTION
   +-------------+         +---------------------+
   |  ServiceNow |---------| servicenow.incidents|
   +-------------+    API  +----------+----------+
                     Fetch +          |
                     Publish          |
                                      v
2. AI PROCESSING
   +-------------------------------------------------------------+
   |                    INCIDENT CONSUMER                         |
   |  +-------------+  +-------------+  +-------------+          |
   |  | Read Event  |->| LLM Analysis|->| RAG Match   |          |
   |  +-------------+  +-------------+  +-------------+          |
   |         |                                   |                |
   |         |              +--------------------+                |
   |         v              v                                     |
   |  +-----------------------------+                            |
   |  |  Publish to agent.events    |                            |
   |  +-----------------------------+                            |
   +-------------------------------------------------------------+

3. EVENT OUTPUT
   +---------------------+
   |    agent.events     |----------> Dashboard / Logging / Monitoring
   +---------------------+
```

### Sample Kafka Event

```json
{
  "event_type": "incident_analyzed",
  "source": "kafka_consumer",
  "incident_id": "INC0010001",
  "timestamp": "2025-11-28T09:14:42.000Z",
  "analysis": {
    "service": "gcp",
    "component": "compute",
    "root_cause": "VM instance stopped unexpectedly",
    "severity": "high"
  },
  "runbook_match": {
    "script_id": "script-start-gcp-instance",
    "confidence": 0.92,
    "risk_level": "low",
    "requires_approval": false
  }
}
```

---

## Core Components

### 1. Backend Orchestrator (`backend/orchestrator/main.py`)

The central API server that coordinates all operations:

- **FastAPI** application on port 8000
- Handles incident CRUD operations
- Orchestrates remediation workflow
- Publishes events to Kafka
- Manages HITL approvals

### 2. Remediation Agent (`backend/agents/remediation/agent.py`)

AI-powered remediation engine:

- **Step 1**: Understand incident (GPT-4 analysis)
- **Step 2**: Match runbooks (Enterprise Hybrid Matcher)
- **Step 3**: Make decision (risk assessment)
- **Step 4**: Create execution plan
- **Step 5**: Generate validation plan

### 3. Kafka Consumer (`backend/streaming/incident_consumer.py`)

Real-time event processor:

- Subscribes to `servicenow.incidents` and `gcp.alerts`
- Runs full remediation analysis pipeline
- Publishes results to `agent.events`
- Supports auto-remediation for LOW risk

### 4. ServiceNow Producer (`backend/streaming/servicenow_producer.py`)

Polls ServiceNow for new incidents:

- Fetches incidents every 60 seconds
- Publishes to Kafka for processing
- Tracks last poll time for efficiency

### 5. Frontend Dashboard (`frontend/`)

React-based user interface:

- Incident list and details
- Remediation panel with AI analysis
- Execute button with auto-filled parameters
- Real-time execution output

---

## Enhanced RAG Pipeline

The platform uses an enhanced RAG (Retrieval Augmented Generation) pipeline for improved script matching accuracy.

### RAG Architecture
```
Incident Query
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                  HYBRID SEARCH ENGINE                    │
│  ┌─────────────┬─────────────┬─────────────┐           │
│  │  Semantic   │   Keyword   │  Metadata   │           │
│  │    (60%)    │    (30%)    │    (10%)    │           │
│  │ all-MiniLM  │   TF-IDF    │ Exact Match │           │
│  └─────────────┴─────────────┴─────────────┘           │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              CROSS-ENCODER RE-RANKING                    │
│           ms-marco-MiniLM-L-6-v2                        │
│         (Improves precision by 20-30%)                  │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              FEEDBACK OPTIMIZER                          │
│        ML-based weight adjustment from outcomes         │
└─────────────────────────────────────────────────────────┘
```

### RAG Components

| Component | File | Purpose |
|-----------|------|---------|
| Hybrid Search | `backend/rag/hybrid_search_engine.py` | Weighted multi-strategy search |
| Cross-Encoder | `backend/rag/cross_encoder_reranker.py` | Re-rank results for precision |
| Smart Chunker | `backend/rag/smart_chunker.py` | Script-type aware chunking |
| Embeddings | `backend/rag/embedding_service.py` | Local/cloud embedding generation |
| Feedback | `backend/rag/feedback_optimizer.py` | ML-based weight optimization |

### Scoring Formula
```
Final_Score = (0.6 × Semantic) + (0.3 × Keyword) + (0.1 × Metadata)
```

---

## Multi-Source Incidents

The platform supports incident ingestion from multiple monitoring sources with a unified format.

### Supported Sources

| Source | Connector | Webhook Validation |
|--------|-----------|-------------------|
| ServiceNow | Native | HTTP Basic Auth |
| GCP Monitoring | Native | Service Account |
| Datadog | `DatadogConnector` | DD-WEBHOOK-TOKEN |
| Prometheus/AlertManager | `PrometheusConnector` | Basic Auth |
| AWS CloudWatch | `CloudWatchConnector` | SNS Signature |
| PagerDuty | `PagerDutyConnector` | HMAC-SHA256 |

### Unified Format
```
┌─────────────────────────────────────────────────────────┐
│              NORMALIZED INCIDENT                         │
├─────────────────────────────────────────────────────────┤
│ incident_id    │ source         │ title                 │
│ description    │ severity       │ status                │
│ category       │ service        │ environment           │
│ cloud_provider │ resource_type  │ region                │
└─────────────────────────────────────────────────────────┘
```

### File
- **Implementation**: `backend/streaming/incident_sources.py`

---

## Automatic Rollback Plans

Every script execution automatically generates a rollback plan for safe recovery.

### Rollback Mappings

| Action | Automatic Rollback |
|--------|-------------------|
| `gcloud instances start` | `gcloud instances stop` |
| `gcloud instances stop` | `gcloud instances start` |
| `kubectl scale --replicas=N` | `kubectl scale --replicas=original` |
| `systemctl start` | `systemctl stop` |
| `config change` | `restore from checkpoint` |

### Rollback Plan Structure
```python
RollbackPlan:
  - steps: List[RollbackStep]     # Reverse actions to execute
  - checkpoint_data: Dict          # Pre-execution state to save
  - risk_level: str               # low/medium/high
  - requires_approval: bool       # True for high-risk rollbacks
  - estimated_duration: int       # Estimated time in seconds
```

### File
- **Implementation**: `backend/orchestrator/rollback_generator.py`

---

## Data Flow

### Incident Processing Flow

```
User/Alert                     Backend                          AI Layer
    |                             |                                 |
    |  1. Incident Created        |                                 |
    |  ------------------------>  |                                 |
    |                             |                                 |
    |                             |  2. Fetch from ServiceNow       |
    |                             |  ----------------------------> |
    |                             |                                 |
    |                             |  3. Publish to Kafka            |
    |                             |  ----------------------------> |
    |                             |     servicenow.incidents        |
    |                             |                                 |
    |                             |                    +------------+------------+
    |                             |                    |  KAFKA CONSUMER         |
    |                             |                    |  - Read event           |
    |                             |                    |  - GPT-4 analysis       |
    |                             |                    |  - RAG search           |
    |                             |                    |  - Match runbooks       |
    |                             |                    +------------+------------+
    |                             |                                 |
    |                             |  4. Analysis Result             |
    |                             |  <----------------------------- |
    |                             |     agent.events                |
    |                             |                                 |
    |  5. Show Results            |                                 |
    |  <--------------------------+                                 |
    |                             |                                 |
    |  6. User clicks Execute     |                                 |
    |  ------------------------>  |                                 |
    |                             |                                 |
    |                             |  7. Execute runbook             |
    |                             |  ----------------------------> |
    |                             |     (GCP API / Ansible / etc)   |
    |                             |                                 |
    |  8. Execution Result        |                                 |
    |  <--------------------------+                                 |
```

---

## 8-Step Remediation Workflow

```
+--------+    +--------+    +--------+    +--------+
| Step 1 |--->| Step 2 |--->| Step 3 |--->| Step 4 |
| DETECT |    | ANALYZE|    | MATCH  |    | PLAN   |
|        |    |        |    |        |    |        |
|Service |    | GPT-4  |    | RAG    |    |Execution|
|Now+GCP |    | LLM    |    | Search |    | Plan   |
+--------+    +--------+    +--------+    +--------+
                                              |
                                              v
+--------+    +--------+    +--------+    +--------+
| Step 8 |<---| Step 7 |<---| Step 6 |<---| Step 5 |
| LEARN  |    |VALIDATE|    | EXECUTE|    | APPROVE|
|        |    |        |    |        |    |        |
| Save to|    | Check  |    | Run    |    | HITL   |
| RAG    |    | Success|    | Script |    | Review |
+--------+    +--------+    +--------+    +--------+
```

### Step Details

| Step | Name | Description | Technology |
|------|------|-------------|------------|
| 1 | **Detect** | Incident ingested from ServiceNow/GCP | Kafka, API |
| 2 | **Analyze** | AI extracts service, component, root cause | GPT-4 LLM |
| 3 | **Match** | Find relevant runbooks | Weaviate + Neo4j + Metadata |
| 4 | **Plan** | Generate execution plan with rollback | LLM + Registry |
| 5 | **Approve** | Human approval for medium/high risk | HITL API |
| 6 | **Execute** | Run script on infrastructure | subprocess, GCP API |
| 7 | **Validate** | Verify fix worked | Post-execution checks |
| 8 | **Learn** | Save to RAG for future | Weaviate indexing |

---

## Enterprise Runbook Matching

### Hybrid Matching Algorithm

```
Final Score = 0.50 x Vector Score
            + 0.25 x Metadata Score
            + 0.15 x Graph Score
            + 0.10 x Safety Score
```

### Matching Components

| Component | Weight | Source | Description |
|-----------|--------|--------|-------------|
| **Vector** | 50% | Weaviate | Semantic similarity using embeddings |
| **Metadata** | 25% | Registry | Exact match on service, component, action |
| **Graph** | 15% | Neo4j | Historical incident-runbook relationships |
| **Safety** | 10% | Registry | Risk level and approval requirements |

### Runbook Registry (`backend/runbooks/registry.json`)

```json
{
  "scripts": [
    {
      "id": "script-start-gcp-instance",
      "name": "Start GCP VM Instance",
      "type": "shell",
      "service": "gcp",
      "component": "compute",
      "action": "start",
      "risk": "low",
      "auto_approve": true,
      "path": "scripts/start_gcp_instance.sh"
    }
  ]
}
```

### Available Runbooks

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

## Technology Stack

### Backend

| Technology | Purpose | Version |
|------------|---------|---------|
| **Python** | Core language | 3.11+ |
| **FastAPI** | API framework | 0.100+ |
| **OpenAI** | LLM (GPT-4) | API |
| **LangChain** | LLM orchestration | 0.1+ |
| **SentenceTransformers** | Local embeddings (FREE) | 2.2+ |
| **Cross-Encoders** | Re-ranking (ms-marco) | 2.2+ |
| **Kafka** | Event streaming | Confluent 7.6 |
| **Redis** | Caching | 7.x |
| **PostgreSQL** | State storage | 15.x |
| **Weaviate** | Vector DB (RAG) | 1.23+ |
| **Neo4j** | Graph DB | 5.x |

### Frontend

| Technology | Purpose | Version |
|------------|---------|---------|
| **React** | UI framework | 18.x |
| **Next.js** | React framework | 14.x |
| **TypeScript** | Type safety | 5.x |
| **TailwindCSS** | Styling | 3.x |
| **TanStack Query** | Data fetching | 5.x |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| **Docker Compose** | Container orchestration |
| **GCP** | Cloud platform |
| **Prometheus** | Metrics |
| **Grafana** | Dashboards |

---

## API Endpoints

### Incidents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/incidents` | List incidents (publishes to Kafka) |
| GET | `/api/incidents/{id}` | Get incident details |

### Multi-Source Incident Webhooks (v3.0)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/incidents/webhook/{source}` | Receive incidents from monitoring sources |
| GET | `/api/incidents/sources` | List supported incident sources |

### Enhanced RAG API (v3.0)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rag/search` | Hybrid search with weighted scoring |
| POST | `/api/rag/feedback` | Record search feedback |
| PUT | `/api/rag/feedback/{id}` | Update execution results |
| GET | `/api/rag/stats` | Get RAG system statistics |

### Rollback API (v3.0)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rollback/generate` | Generate rollback plan for script |

### Remediation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/remediation/full` | Run full remediation analysis |
| GET | `/api/remediation/runbooks` | List available runbooks |
| POST | `/api/runbooks/{id}/execute-real` | Execute runbook on infrastructure |
| POST | `/api/runbooks/sync-from-github` | Sync runbooks from GitHub |

### HITL Approvals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/hitl/approvals/pending` | Get pending approvals |
| POST | `/api/hitl/approvals/{id}/approve-plan` | Approve remediation plan |
| POST | `/api/hitl/approvals/{id}/reject-plan` | Reject remediation plan |

---

## Security & Governance

### Risk-Based Approval Matrix

| Risk Level | Auto-Approve | Approvers Required |
|------------|--------------|-------------------|
| **Low** | Yes | None |
| **Medium** | No | 1 approver |
| **High** | No | 2 approvers |
| **Critical** | No | 2 approvers + manager |

### Authentication

| Service | Auth Method |
|---------|-------------|
| ServiceNow | HTTP Basic Auth |
| GCP | Service Account JSON key |
| GitHub | Personal Access Token |
| OpenAI | API Key |

### Audit Trail

All actions are logged to:
- Kafka `agent.events` topic
- PostgreSQL `audit_log` table
- Neo4j relationships (incident -> action -> result)

---

## File Structure

```
ai_agent_app/
+-- backend/
|   +-- orchestrator/
|   |   +-- main.py                    # FastAPI server
|   |   +-- llm_intelligence.py        # LLM integration
|   |   +-- enterprise_executor.py     # Script execution
|   |   +-- rollback_generator.py      # Automatic rollback plans (v3.0)
|   +-- agents/
|   |   +-- remediation/
|   |       +-- agent.py               # AI remediation engine
|   +-- rag/
|   |   +-- __init__.py                # RAG module exports
|   |   +-- hybrid_search_engine.py    # Weighted hybrid search (v3.0)
|   |   +-- cross_encoder_reranker.py  # Cross-encoder re-ranking (v3.0)
|   |   +-- smart_chunker.py           # Script-type chunking (v3.0)
|   |   +-- embedding_service.py       # Local embeddings (v3.0)
|   |   +-- feedback_optimizer.py      # ML-based optimization (v3.0)
|   |   +-- weaviate_client.py         # Vector store
|   |   +-- neo4j_client.py            # Graph store
|   +-- streaming/
|   |   +-- incident_consumer.py       # Kafka consumer
|   |   +-- servicenow_producer.py     # ServiceNow polling
|   |   +-- incident_sources.py        # Multi-source connectors (v3.0)
|   +-- runbooks/
|   |   +-- registry.json              # Runbook catalog
|   |   +-- scripts/                   # Shell scripts
|   |   +-- ansible/                   # Ansible playbooks
|   |   +-- terraform/                 # Terraform configs
|   +-- utils/
|       +-- kafka_client.py
|       +-- redis_client.py
+-- frontend/
|   +-- src/
|       +-- components/
|       |   +-- incidents/
|       |       +-- EnterpriseIncidentDetail.tsx
|       +-- app/
|           +-- graph/[id]/page.tsx    # Workflow visualization
+-- deployment/
|   +-- docker-compose.yml
+-- monitoring/
|   +-- prometheus.yml
|   +-- grafana/
+-- docs/
|   +-- ARCHITECTURE.md
|   +-- AI_AGENT_PLATFORM_PPT.md
|   +-- ENHANCED_RAG_FEATURES.md       # RAG documentation (v3.0)
+-- .github/
    +-- workflows/
        +-- shell-execute.yml          # GitHub Actions execution
```

---

## Service URLs

| Service | Local URL | External URL |
|---------|-----------|--------------|
| Frontend | http://localhost:3002 | http://34.171.221.200:3002 |
| Backend API | http://localhost:8000 | http://34.171.221.200:8000 |
| API Docs | http://localhost:8000/docs | |
| Kafka UI | http://localhost:8085 | http://34.171.221.200:8085 |
| Grafana | http://localhost:3000 | http://34.171.221.200:3000 |
| Neo4j | http://localhost:7474 | http://34.171.221.200:7474 |

---

## Quick Start

```bash
# 1. Start infrastructure
cd deployment && sudo docker compose up -d

# 2. Start backend
cd backend
export KAFKA_BOOTSTRAP_SERVERS=localhost:29092
export SNOW_INSTANCE_URL="https://your-instance.service-now.com"
export OPENAI_API_KEY="your-key"
python3 orchestrator/main.py

# 3. Start Kafka consumer (runs continuously)
python3 streaming/incident_consumer.py

# 4. Start frontend
cd frontend && npm run start
```

---

**Architecture designed for enterprise-scale AI operations.**
