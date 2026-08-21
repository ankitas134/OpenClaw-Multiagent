# OpenClaw Platform (Standalone Python Edition)

An enterprise-grade, multi-tenant AI Agent Orchestration and RAG Execution Platform built natively in **Python**.

---

## 🏗️ Technology Architecture Map

| Service / Layer | Reference System (Node.js) | Python Reimplementation |
| :--- | :--- | :--- |
| **Backend API** | Fastify (TypeScript) | **FastAPI** (Python 3.11, AsyncIO) |
| **Database** | PostgreSQL 16 + `pgvector` | **PostgreSQL 16 + `pgvector`** (SQLAlchemy Async) |
| **Background Queuing** | BullMQ + Redis | **Celery + Redis** |
| **Container Sandboxing** | Dockerode | **Python `docker` SDK** |
| **Vector Embeddings** | `@xenova/transformers` | **`sentence-transformers`** (`all-MiniLM-L6-v2`) |
| **LLM Engine** | Hardcoded Gemini API | **Provider-Agnostic LLM Engine** (`groq/compound` / HuggingFace TGI) |
| **Authentication** | JWT + bcrypt | **python-jose (JWT) + passlib (bcrypt)** |
| **Real-time Streaming** | Redis Pub/Sub | **Redis Pub/Sub + FastAPI WebSockets** |
| **Web Portal UI** | Next.js 16 (App Router) | **Streamlit Web Portal** |

---

## 🚀 Quick Start Guide (Docker Compose)

### 1. Prerequisites
- Docker Desktop installed and running.

### 2. Verify `.env` Configuration
Copy `.env.example` to `.env` (or configure your `.env` file):
```env
LLM_PROVIDER=groq
GROQ_API_KEY=YOUR_GROQ_API_KEY
GROQ_MODEL=groq/compound
```

### 3. Launch Services
Open PowerShell or Command Prompt in the project directory:

```powershell
docker compose up --build -d
```

### 4. Access the Applications
- **Streamlit Web Portal**: [http://127.0.0.1:8501](http://127.0.0.1:8501)
- **FastAPI OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **FastAPI Health Check**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

> 💡 *Note: Use `127.0.0.1` instead of `localhost` on Windows to ensure IPv4 binding connects immediately.*

---

## 🧪 Automated Test Suites

Run the end-to-end integration and security test pipelines directly from PowerShell:

```powershell
# 1. Run End-to-End System Integration Test (10/10 Stages)
python test_isolation.py

# 2. Run Container Sandbox Security Unit Tests (5/5 Tests)
python test_sandbox_security.py
```
