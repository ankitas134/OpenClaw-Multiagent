import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, Agent, AgentMessage, Document, agent_documents, AuditLog
from app.api.auth import get_current_user
from app.api.teams import verify_team_membership
from app.tasks.tasks import spinup_agent_task, stop_agent_task, process_message_task

router = APIRouter(prefix="/api/agents", tags=["Agents"])

class AgentCreateSchema(BaseModel):
    teamId: str
    name: str
    taskContext: Optional[str] = ""
    visibility: Optional[str] = "personal"
    config: Optional[Dict[str, Any]] = None
    documentIds: Optional[List[str]] = []

class PostMessageSchema(BaseModel):
    text: str
    threadId: Optional[str] = None

async def check_agent_access(agent_id: uuid.UUID, user_id: uuid.UUID, min_role: str, db: AsyncSession) -> Agent:
    res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = res.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await verify_team_membership(agent.team_id, user_id, min_role, db)
    return agent

@router.get("/")
async def list_agents(
    teamId: str = Query(..., description="Target Team ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t_uuid = uuid.UUID(teamId)
    await verify_team_membership(t_uuid, current_user.id, "member", db)

    res = await db.execute(
        select(Agent)
        .where(Agent.team_id == t_uuid)
        .order_by(Agent.created_at.desc())
    )
    agents = res.scalars().all()
    return [{
        "id": str(a.id),
        "teamId": str(a.team_id),
        "createdBy": str(a.created_by) if a.created_by else None,
        "name": a.name,
        "config": a.config,
        "status": a.status,
        "visibility": a.visibility,
        "containerId": a.container_id,
        "taskContext": a.task_context,
        "workspacePath": a.workspace_path,
        "createdAt": a.created_at.isoformat() if a.created_at else None
    } for a in agents]

@router.post("/", status_code=202)
async def create_agent(
    data: AgentCreateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t_uuid = uuid.UUID(data.teamId)
    await verify_team_membership(t_uuid, current_user.id, "member", db)

    default_config = {
        "sandboxMode": "all",
        "sandboxBackend": "docker",
        "sandboxDockerNetwork": "none",
        "sandboxDockerReadOnlyRoot": True,
        "sandboxDockerCapDrop": ["ALL"],
        "memoryLimit": 268435456,
        "cpuLimit": 500000000
    }
    if data.config:
        default_config.update(data.config)

    agent = Agent(
        team_id=t_uuid,
        created_by=current_user.id,
        name=data.name,
        config=default_config,
        status="pending",
        task_context=data.taskContext or "",
        visibility=data.visibility or "personal"
    )
    db.add(agent)
    await db.flush()

    if data.documentIds:
        for doc_id in data.documentIds:
            d_uuid = uuid.UUID(doc_id)
            doc_res = await db.execute(select(Document).where(Document.id == d_uuid, Document.team_id == t_uuid))
            doc = doc_res.scalars().first()
            if doc:
                await db.execute(agent_documents.insert().values(agent_id=agent.id, document_id=doc.id))

    audit = AuditLog(team_id=t_uuid, user_id=current_user.id, action="agent.create", metadata_={"agentId": str(agent.id), "name": agent.name})
    db.add(audit)
    await db.commit()

    spinup_agent_task.delay(str(agent.id))

    return {
        "id": str(agent.id),
        "teamId": str(agent.team_id),
        "name": agent.name,
        "status": agent.status,
        "visibility": agent.visibility,
        "taskContext": agent.task_context
    }

@router.get("/{agent_id}")
async def get_agent_detail(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)

    doc_res = await db.execute(
        select(Document)
        .join(agent_documents, Document.id == agent_documents.c.document_id)
        .where(agent_documents.c.agent_id == agent.id)
    )
    documents = [{
        "id": str(d.id),
        "filename": d.filename,
        "mimeType": d.mime_type,
        "sizeBytes": d.size_bytes,
        "extractionStatus": d.extraction_status,
        "visibility": d.visibility
    } for d in doc_res.scalars().all()]

    return {
        "id": str(agent.id),
        "teamId": str(agent.team_id),
        "name": agent.name,
        "config": agent.config,
        "status": agent.status,
        "visibility": agent.visibility,
        "containerId": agent.container_id,
        "taskContext": agent.task_context,
        "workspacePath": agent.workspace_path,
        "createdAt": agent.created_at.isoformat() if agent.created_at else None,
        "documents": documents
    }

@router.post("/{agent_id}/start")
async def start_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)

    spinup_agent_task.delay(str(agent.id))
    return {"message": "Spinup task queued successfully"}

@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)

    stop_agent_task.delay(str(agent.id))
    return {"message": "Stop task queued successfully"}

class AgentUpdateContextSchema(BaseModel):
    taskContext: str

@router.patch("/{agent_id}/context")
async def update_agent_context(
    agent_id: str,
    data: AgentUpdateContextSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)
    agent.task_context = data.taskContext
    audit = AuditLog(team_id=agent.team_id, user_id=current_user.id, action="agent.context_update", metadata_={"agentId": str(agent.id)})
    db.add(audit)
    await db.commit()
    return {"id": str(agent.id), "taskContext": agent.task_context}

@router.get("/{agent_id}/threads")
async def get_agent_threads(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)
    res = await db.execute(
        select(AgentMessage.thread_id)
        .where(AgentMessage.agent_id == agent.id)
        .distinct()
    )
    raw_threads = res.scalars().all()
    threads = list(set([t for t in raw_threads if t]))
    threads.sort()
    return threads

@router.get("/{agent_id}/messages")
async def get_agent_messages(
    agent_id: str,
    threadId: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)

    stmt = select(AgentMessage).where(AgentMessage.agent_id == agent.id)
    if threadId:
        stmt = stmt.where(AgentMessage.thread_id == threadId)

    stmt = stmt.order_by(AgentMessage.created_at.asc())
    res = await db.execute(stmt)
    msgs = res.scalars().all()
    return [{
        "id": str(m.id),
        "agentId": str(m.agent_id),
        "userId": str(m.user_id) if m.user_id else None,
        "sender": m.sender,
        "text": m.text,
        "threadId": m.thread_id,
        "createdAt": m.created_at.isoformat() if m.created_at else None
    } for m in msgs]

@router.post("/{agent_id}/messages")
async def post_agent_message(
    agent_id: str,
    data: PostMessageSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)

    user_msg = AgentMessage(
        agent_id=agent.id,
        user_id=current_user.id,
        sender="user",
        text=data.text,
        thread_id=data.threadId or "main"
    )
    db.add(user_msg)
    await db.commit()

    process_message_task.delay(str(agent.id), str(user_msg.id))

    return {
        "id": str(user_msg.id),
        "agentId": str(user_msg.agent_id),
        "sender": "user",
        "text": user_msg.text,
        "threadId": user_msg.thread_id,
        "createdAt": user_msg.created_at.isoformat()
    }
