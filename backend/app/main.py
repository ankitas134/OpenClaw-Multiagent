# pyrefly: ignore [missing-import]
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, teams, agents, documents, audit, ws, context_assistant, voice

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Enterprise Multi-Tenant AI Agent Orchestration API (Python Reimplementation)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(agents.router)
app.include_router(documents.router)
app.include_router(audit.router)
app.include_router(ws.router)
app.include_router(context_assistant.router)
app.include_router(voice.router)

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "llm_provider": settings.LLM_PROVIDER,
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
