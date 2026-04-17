# Agentic Workflow Orchestrator

A backend system that executes multi-step workflows by delegating reasoning to AI agents while maintaining strict control through a central orchestrator. The system consists of two services and a simple frontend:

- **Orchestrator API** (NestJS / TypeScript) — REST API for submitting and tracking workflow executions
- **LangGraph Service** (Python / FastAPI) — Agentic workflow engine with a dynamic router and four sub-agents
- **Frontend** (HTML / CSS / JS) — Browser UI for submitting workflows and viewing results in real time

## Architecture

```
Client / Frontend → POST /workflows → Orchestrator API (NestJS)
                                            ↓
                                      HTTP POST /execute
                                            ↓
                                    LangGraph Service (Python)
                                            ↓
                                ┌── Orchestrator Router ──┐
                                │   (LLM-based routing)   │
                                ├──→ Planner Agent         │
                                ├──→ Validator Agent       │
                                ├──→ Executor Agent        │
                                ├──→ Evaluator Agent       │
                                └──→ Exit (done/fail)      │
                                            ↓
                                Callback → Orchestrator API
                                            ↓
                                      PostgreSQL DB
```

The LangGraph service uses a hub-and-spoke pattern: a central Orchestrator Router uses LLM reasoning to dynamically decide which sub-agent to call next, rather than following a fixed sequence.

## Prerequisites

- **Node.js** >= 18.x and **npm**
- **Python** >= 3.9
- **PostgreSQL** >= 14
- **Groq API key** (free at [console.groq.com](https://console.groq.com))

## Project Structure

```
.
├── orchestrator-api/          # NestJS TypeScript service
│   ├── src/
│   │   ├── auth/              # API key authentication guard (available but not enforced)
│   │   ├── workflows/         # Workflow module (controller, service, DTOs, entity)
│   │   ├── app.module.ts      # Root module with TypeORM + ConfigModule
│   │   └── main.ts            # Bootstrap with CORS, Swagger, ValidationPipe
│   ├── package.json
│   └── tsconfig.json
│
├── langgraph-service/         # Python FastAPI service
│   ├── app/
│   │   ├── agents/            # Sub-agents (Planner, Validator, Executor, Evaluator)
│   │   ├── api/               # FastAPI routes (/execute endpoint)
│   │   ├── models/            # Data models (WorkflowState, API payloads)
│   │   ├── workflow/          # Graph builder, Router, LLM client
│   │   ├── config.py          # Centralized environment-based configuration
│   │   ├── prompt_registry.py # Template loader for externalized prompts
│   │   └── main.py            # FastAPI app entry point
│   ├── prompts/               # LLM prompt templates (planner.txt, router.txt, etc.)
│   └── requirements.txt
│
├── frontend/                  # Single-page HTML app (no build tools needed)
│   └── index.html
│
│
└── README.md
```

---

## Quick Start (End-to-End)

### 1. Start PostgreSQL

Using Docker (recommended):

```bash
docker run -d \
  --name orchestrator-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=orchestrator \
  -p 5432:5432 \
  postgres:16
```

Or create the database manually:

```bash
psql -U postgres -c "CREATE DATABASE orchestrator;"
```

### 2. Get a Groq API Key

1. Go to [https://console.groq.com](https://console.groq.com)
2. Create an API key
3. Copy it — you'll need it for the LangGraph Service

### 3. Set Up the Orchestrator API

```bash
cd orchestrator-api
npm install
cp .env.example .env
```

Edit `orchestrator-api/.env`:

```dotenv
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_NAME=orchestrator

# Application
PORT=3000
NODE_ENV=development

# LangGraph Service
LANGGRAPH_SERVICE_URL=http://localhost:8000
ORCHESTRATOR_BASE_URL=http://localhost:3000

# Workflow Defaults (optional — these are the defaults if omitted)
# DEFAULT_MAX_RETRIES=3
# DEFAULT_MAX_ITERATIONS=15
# DEFAULT_TIMEOUT_SECONDS=300
```

Start it:

```bash
npm run start:dev
```

The API runs at `http://localhost:3000`. Swagger docs at `http://localhost:3000/api-docs`. CORS is enabled so the frontend can connect from any origin.

### 4. Set Up the LangGraph Service

```bash
cd langgraph-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `langgraph-service/.env`:

```dotenv
# Service URLs
ORCHESTRATOR_API_URL=http://localhost:3000

# Groq API — REQUIRED
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_API_BASE_URL=https://api.groq.com/openai/v1

# Global Defaults
DEFAULT_MODEL=llama-3.3-70b-versatile
DEFAULT_MAX_RETRIES=3
DEFAULT_MAX_ITERATIONS=15
DEFAULT_TEMPERATURE=0.2

# Per-Agent Model Overrides (optional — uncomment to use different models per agent)
# PLANNER_MODEL=llama-3.3-70b-versatile
# VALIDATOR_MODEL=llama-3.1-8b-instant
# EXECUTOR_MODEL=llama-3.3-70b-versatile
# EVALUATOR_MODEL=llama-3.3-70b-versatile
# ROUTER_MODEL=llama-3.1-8b-instant

# Per-Agent Temperature Overrides (optional — uncomment to tune per agent)
# PLANNER_TEMPERATURE=0.3
# VALIDATOR_TEMPERATURE=0.1
# EXECUTOR_TEMPERATURE=0.2
# EVALUATOR_TEMPERATURE=0.2
# ROUTER_TEMPERATURE=0.1
```

Start it:

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The service runs at `http://localhost:8000`. Health check at `http://localhost:8000/health`.

### 5. Open the Frontend

Open `frontend/index.html` in your browser. Type what you want the agents to do in plain text and hit Submit. The frontend auto-polls and shows the result as soon as the workflow completes or fails — no need to manually check status.

You can also pass JSON if you prefer, but plain text works fine.

### 6. Or Use curl

Submit a workflow with plain text:

```bash
curl -X POST http://localhost:3000/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Analyze customer feedback and generate a summary report"
  }'
```

Or with structured JSON input:

```bash
curl -X POST http://localhost:3000/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "task": "Analyze customer feedback",
      "data": {
        "feedbackItems": [
          { "id": "1", "text": "Great product", "rating": 5 },
          { "id": "2", "text": "Poor support", "rating": 2 }
        ]
      }
    },
    "config": {
      "maxRetries": 3,
      "maxIterations": 15
    }
  }'
```


---

## Configuration Reference

### Orchestrator API (`orchestrator-api/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_HOST` | Yes | `localhost` | PostgreSQL host |
| `DB_PORT` | Yes | `5432` | PostgreSQL port |
| `DB_USERNAME` | Yes | `postgres` | PostgreSQL username |
| `DB_PASSWORD` | Yes | `postgres` | PostgreSQL password |
| `DB_NAME` | Yes | `orchestrator` | Database name |
| `PORT` | No | `3000` | API server port |
| `NODE_ENV` | No | `development` | `development` enables DB auto-sync |
| `LANGGRAPH_SERVICE_URL` | Yes | `http://localhost:8000` | LangGraph Service URL |
| `ORCHESTRATOR_BASE_URL` | Yes | `http://localhost:3000` | This service's URL (for callback construction) |
| `DEFAULT_MAX_RETRIES` | No | `3` | Default max retries per workflow |
| `DEFAULT_MAX_ITERATIONS` | No | `15` | Default max routing iterations |
| `DEFAULT_TIMEOUT_SECONDS` | No | `300` | Default workflow timeout |

### LangGraph Service (`langgraph-service/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `ORCHESTRATOR_API_URL` | Yes | `http://localhost:3000` | Orchestrator API URL |
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM calls |
| `GROQ_API_BASE_URL` | No | `https://api.groq.com/openai/v1` | Groq API base URL |
| `DEFAULT_MODEL` | No | `llama-3.3-70b-versatile` | Default LLM model |
| `DEFAULT_MAX_RETRIES` | No | `3` | Default max retries |
| `DEFAULT_MAX_ITERATIONS` | No | `15` | Default max iterations |
| `DEFAULT_TEMPERATURE` | No | `0.2` | Default LLM temperature |
| `PLANNER_MODEL` | No | *(DEFAULT_MODEL)* | Model override for Planner |
| `VALIDATOR_MODEL` | No | *(DEFAULT_MODEL)* | Model override for Validator |
| `EXECUTOR_MODEL` | No | *(DEFAULT_MODEL)* | Model override for Executor |
| `EVALUATOR_MODEL` | No | *(DEFAULT_MODEL)* | Model override for Evaluator |
| `ROUTER_MODEL` | No | *(DEFAULT_MODEL)* | Model override for Router |
| `PLANNER_TEMPERATURE` | No | *(DEFAULT_TEMPERATURE)* | Temperature for Planner |
| `VALIDATOR_TEMPERATURE` | No | *(DEFAULT_TEMPERATURE)* | Temperature for Validator |
| `EXECUTOR_TEMPERATURE` | No | *(DEFAULT_TEMPERATURE)* | Temperature for Executor |
| `EVALUATOR_TEMPERATURE` | No | *(DEFAULT_TEMPERATURE)* | Temperature for Evaluator |
| `ROUTER_TEMPERATURE` | No | *(DEFAULT_TEMPERATURE)* | Temperature for Router |

---

## Workflow Config Options

These can be passed per-workflow in the request body under `config`:

| Field | Type | Range | Default | Description |
|---|---|---|---|---|
| `maxRetries` | int | 0–10 | 3 | Max retry cycles |
| `maxIterations` | int | 1–50 | 15 | Max router decisions before forced exit |
| `timeoutSeconds` | int | 1–600 | 300 | Max execution time in seconds |
| `model` | string | — | *(from env)* | LLM model override for all agents in this workflow |

---

## How It Works

1. Client submits a workflow via `POST /workflows` with plain text or JSON input and optional config
2. If the input is a plain string, the backend wraps it as `{ task: "your text" }` for the agents
3. Orchestrator API creates a workflow record (`PENDING`), then fires an async request to the LangGraph Service
4. LangGraph Service runs the agent graph:
   - **Router** analyzes the current state using LLM reasoning and picks the next agent
   - The selected **sub-agent** runs and updates the state
   - Control returns to the Router
   - Loop continues until evaluation passes or max iterations are reached
5. LangGraph Service sends a callback to the Orchestrator API with the final result
6. The frontend auto-polls and displays the result as soon as it's ready

### Sub-Agents

| Agent | Purpose | How it works | Output |
|---|---|---|---|
| Planner | Breaks input into discrete execution steps | Single LLM call, returns a list of steps | `plan` |
| Validator | Checks plan feasibility and constraints | Single LLM call, validates the entire plan | `validation` |
| Executor | Executes the validated plan | Single LLM call with the full plan, returns results for all steps at once | `execution` |
| Evaluator | Validates the final outcome against success criteria | Single LLM call, scores the execution | `evaluation` |

### Routing Constraints

The Router enforces these rules to prevent invalid or redundant agent calls:
- Cannot call Validator without a plan
- Cannot call Executor without a valid validation
- Cannot call Evaluator without execution output
- Cannot re-plan when validation already passed and execution hasn't run yet
- If the LLM routing fails, a deterministic fallback picks the next logical agent

### Prompt Templates

All LLM prompts are externalized in `langgraph-service/prompts/` as `.txt` files with `{placeholder}` syntax. Edit them to customize agent behavior without touching code.

---
