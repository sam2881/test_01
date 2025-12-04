# AI Agent Platform for Enterprise Incident Remediation

> Enterprise-grade, Event-Driven AI Agent Platform for Automated Incident Remediation

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/sam2881/test_01)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Overview

The AI Agent Platform is an enterprise-grade system that automates incident detection, analysis, and remediation. It uses GPT-4 for intelligent analysis, hybrid RAG for script matching, and GitHub Actions for secure execution.

### Key Features

| Feature | Description |
|---------|-------------|
| **Event-Driven Architecture** | Kafka-based real-time incident processing |
| **LangGraph Orchestration** | 18-node workflow with 8 phases |
| **Enhanced Hybrid RAG** | Semantic (60%) + Keyword (30%) + Metadata (10%) search |
| **Cross-Encoder Re-ranking** | ms-marco model for 20-30% improved precision |
| **Local Embeddings** | SentenceTransformers - FREE, no API cost |
| **Multi-Source Incidents** | ServiceNow, GCP, Datadog, Prometheus, CloudWatch, PagerDuty |
| **Automatic Rollback** | Generated rollback plans for safe execution |
| **Human-in-the-Loop (HITL)** | Approval workflow for high-risk actions |
| **Secure Execution** | GitHub Actions for auditable script execution |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js)                           │
│        http://localhost:3002 | Incidents | Workflows | Approvals         │
└──────────────────────────────────────┬───────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY (FastAPI)                             │
│                        http://localhost:8000                              │
│   /api/incidents | /api/rag | /api/rollback | /api/langgraph | /api/mcp  │
└──────────────────────────────────────┬───────────────────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────┐     ┌─────────────────────────┐     ┌────────────────┐
│   Multi-Source   │     │   Enhanced RAG v2.0     │     │    LangGraph   │
│    Incidents     │     │   Hybrid + Re-ranking   │     │   18 Nodes     │
│  (6 connectors)  │     │   + Feedback Loop       │     │   8 Phases     │
└──────────────────┘     └─────────────────────────┘     └────────────────┘
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                      │
│   PostgreSQL | Redis | Weaviate (Vector) | Neo4j (Graph) | Kafka         │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- OpenAI API key
- ServiceNow instance (optional)
- GCP service account (optional)

### 1. Clone Repository

```bash
git clone https://github.com/sam2881/test_01.git
cd ai_agent_app
```

### 2. Start Infrastructure

```bash
cd deployment
sudo docker compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Kafka (port 29092)
- Weaviate (port 8080)
- Neo4j (port 7474)

### 3. Configure Environment

```bash
# Create .env file
cat > .env << 'EOF'
# OpenAI
OPENAI_API_KEY=sk-your-key-here

# ServiceNow
SNOW_INSTANCE_URL=https://your-instance.service-now.com
SNOW_USERNAME=admin
SNOW_PASSWORD=your-password

# GCP (optional)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCP_PROJECT=your-project-id

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:29092

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_agent
REDIS_URL=redis://localhost:6379
EOF
```

### 4. Start Backend

```bash
cd backend
pip install -r requirements.txt
python3 orchestrator/main.py
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 6. Access Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3002 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |

---

## Enhanced RAG Pipeline v2.0

The platform uses an advanced RAG system for accurate script matching:

### Hybrid Search

```
Final_Score = (0.6 × Semantic) + (0.3 × Keyword) + (0.1 × Metadata)
```

| Component | Weight | Technology | Purpose |
|-----------|--------|------------|---------|
| Semantic | 60% | all-MiniLM-L6-v2 | Meaning-based similarity |
| Keyword | 30% | TF-IDF | Exact term matching |
| Metadata | 10% | Exact match | cloud_provider, service, environment |

### Cross-Encoder Re-ranking

Two-stage retrieval for improved precision:
1. **Stage 1**: Fast bi-encoder search → Top 20 results
2. **Stage 2**: Cross-encoder re-ranking → Top 5 results

Uses `ms-marco-MiniLM-L-6-v2` for 20-30% precision improvement.

### Feedback Optimizer

System learns optimal weights from execution outcomes:
- Records search results and execution success/failure
- Adjusts weights per incident type using ML
- Continuously improves over time

---

## Multi-Source Incidents

Unified incident ingestion from 6 monitoring sources:

| Source | Connector | Webhook Endpoint |
|--------|-----------|------------------|
| ServiceNow | Native | `/api/incidents` |
| GCP Monitoring | Native | `/api/gcp/alerts` |
| Datadog | `DatadogConnector` | `/api/incidents/webhook/datadog` |
| Prometheus | `PrometheusConnector` | `/api/incidents/webhook/prometheus` |
| CloudWatch | `CloudWatchConnector` | `/api/incidents/webhook/cloudwatch` |
| PagerDuty | `PagerDutyConnector` | `/api/incidents/webhook/pagerduty` |

All incidents are normalized to a unified format for processing.

---

## Automatic Rollback Plans

Every script execution generates an automatic rollback plan:

| Action | Rollback |
|--------|----------|
| Start VM | Stop VM |
| Scale Up K8s | Scale Down to original |
| Config Change | Restore from checkpoint |
| Create Firewall | Delete Firewall |

---

## API Endpoints

### Core APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/incidents` | List incidents |
| GET | `/api/incidents/{id}` | Get incident details |
| POST | `/api/langgraph/node/{id}` | Execute workflow node |

### Enhanced RAG APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rag/search` | Hybrid search with re-ranking |
| POST | `/api/rag/feedback` | Record search feedback |
| GET | `/api/rag/stats` | Get RAG statistics |

### Rollback APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rollback/generate` | Generate rollback plan |

### Multi-Source Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/incidents/webhook/{source}` | Receive external incidents |
| GET | `/api/incidents/sources` | List supported sources |

---

## Technology Stack

### Backend
- **Python 3.11** - Core language
- **FastAPI** - API framework
- **LangGraph** - Workflow orchestration
- **OpenAI GPT-4** - LLM intelligence
- **SentenceTransformers** - Local embeddings (FREE)
- **Apache Kafka** - Event streaming

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **TailwindCSS** - Styling

### Data Stores
- **PostgreSQL** - Relational data
- **Redis** - Caching
- **Weaviate** - Vector store
- **Neo4j** - Knowledge graph

### Execution
- **GitHub Actions** - Secure script execution
- **MCP Servers** - Tool integration

---

## Project Structure

```
ai_agent_app/
├── backend/
│   ├── orchestrator/          # FastAPI server & workflow
│   │   ├── main.py
│   │   ├── llm_intelligence.py
│   │   └── rollback_generator.py
│   ├── rag/                   # Enhanced RAG v2.0
│   │   ├── hybrid_search_engine.py
│   │   ├── cross_encoder_reranker.py
│   │   ├── smart_chunker.py
│   │   ├── embedding_service.py
│   │   └── feedback_optimizer.py
│   └── streaming/             # Event processing
│       ├── incident_consumer.py
│       └── incident_sources.py
├── frontend/                  # Next.js UI
├── deployment/                # Docker configs
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md
│   ├── AI_AGENT_PLATFORM_PPT.md
│   └── ENHANCED_RAG_FEATURES.md
└── .github/workflows/         # GitHub Actions
```

---

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - System architecture details
- [Enhanced RAG Features](docs/ENHANCED_RAG_FEATURES.md) - RAG v2.0 documentation
- [Platform Overview](docs/AI_AGENT_PLATFORM_PPT.md) - Comprehensive PPT-style guide

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Contact

- **Repository**: [https://github.com/sam2881/test_01](https://github.com/sam2881/test_01)
- **Issues**: [GitHub Issues](https://github.com/sam2881/test_01/issues)

---

*Version 3.0.0 - December 2024*
