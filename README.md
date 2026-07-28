# OpenClaw Platform (Standalone Python Edition)

An enterprise-grade, multi-tenant AI Agent Orchestration and RAG Execution Platform built natively in **Python**.

This repository is a completely standalone project located outside of the original Node.js codebase.

---

## 🏗️ Technology Architecture Map

| Service / Layer | Reference System (Node.js) | Python Reimplementation |
| :--- | :--- | :--- |
| **Backend API** | Fastify (TypeScript) | **FastAPI** (Python 3.11, AsyncIO) |
| **Database** | PostgreSQL 16 + `pgvector` | **PostgreSQL 16 + `pgvector`** (SQLAlchemy Async) |
| **Background Queuing** | BullMQ + Redis | **Celery + Redis** |
| **Container Sandboxing** | Dockerode | **Python `docker` SDK** |
| **Vector Embeddings** | `@xenova/transformers` | **`sentence-transformers`** (`all-MiniLM-L6-v2`) |
| **LLM Engine** | Hardcoded Gemini API | **Provider-Agnostic LLM Engine** (Groq API / HuggingFace TGI) |
| **Authentication** | JWT + bcrypt | **python-jose (JWT) + passlib (bcrypt)** |
| **Real-time Streaming** | Redis Pub/Sub | **Redis Pub/Sub + FastAPI WebSockets** |
| **Web Portal UI** | Next.js 16 (App Router) | **Streamlit Web Portal** |

---

## 🚀 Quick Start Guide (Docker Compose)

### 1. Prerequisites
- Docker Desktop installed and running.

### 2. Verify `.env` Configuration
The `.env` file in this directory is already pre-configured with your Groq API key:
```env
LLM_PROVIDER=groq
GROQ_API_KEY=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
GROQ_MODEL=llama-3.3-70b-versatile
```

### 3. Launch Services
Open PowerShell or Command Prompt in `openclaw-python-platform`:

```powershell
cd c:\Users\ankit\OneDrive\Desktop\openclaw-python-platform
docker-compose up --build -d
```

### 4. Access the Applications
- **Streamlit Web Portal**: [http://localhost:8501](http://localhost:8501)
- **FastAPI OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **FastAPI Health Check**: [http://localhost:8000/](http://localhost:8000/)
