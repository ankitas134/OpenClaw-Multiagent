import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, Agent, AgentMessage, Document, agent_documents, AuditLog
from app.api.auth import get_current_user
from app.api.teams import verify_team_membership
from app.tasks.tasks import spinup_agent_task, stop_agent_task, process_message_task
from app.core.sandbox_config import SERVER_SANDBOX_SETTINGS, AgentCustomConfigSchema

router = APIRouter(prefix="/api/agents", tags=["Agents"])

class AgentCreateSchema(BaseModel):
    teamId: str
    name: str
    taskContext: Optional[str] = ""
    visibility: Optional[str] = "personal"
    config: Optional[AgentCustomConfigSchema] = None
    documentIds: Optional[List[str]] = []

class PostMessageSchema(BaseModel):
    text: str
    threadId: Optional[str] = None

async def check_agent_access(agent_id: uuid.UUID, user_id: uuid.UUID, min_role: str, db: AsyncSession) -> Agent:
    res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = res.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Agent creator always has full access to manage their own agent
    if agent.created_by == user_id:
        await verify_team_membership(agent.team_id, user_id, "member", db)
        return agent

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
        select(Agent).where(
            Agent.team_id == t_uuid,
            (Agent.created_by == current_user.id) | (Agent.visibility == "team")
        )
    )
    agents = res.scalars().all()
    return [{
        "id": str(a.id),
        "teamId": str(a.team_id),
        "name": a.name,
        "status": a.status,
        "visibility": a.visibility,
        "createdBy": str(a.created_by) if a.created_by else None,
        "taskContext": a.task_context,
        "createdAt": a.created_at.isoformat()
    } for a in agents]

@router.post("/")
async def create_agent(
    data: AgentCreateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t_uuid = uuid.UUID(data.teamId)
    await verify_team_membership(t_uuid, current_user.id, "member", db)

    config_dict = SERVER_SANDBOX_SETTINGS.model_dump()

    agent = Agent(
        team_id=t_uuid,
        created_by=current_user.id,
        name=data.name,
        task_context=data.taskContext or "",
        visibility=data.visibility or "personal",
        config=config_dict,
        status="stopped"
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    if data.documentIds:
        for d_id in data.documentIds:
            doc_uuid = uuid.UUID(d_id)
            await db.execute(agent_documents.insert().values(agent_id=agent.id, document_id=doc_uuid))
        await db.commit()

    audit = AuditLog(team_id=t_uuid, user_id=current_user.id, action="agent.create", metadata_={"agentId": str(agent.id), "name": agent.name})
    db.add(audit)
    await db.commit()

    return {
        "id": str(agent.id),
        "teamId": str(agent.team_id),
        "name": agent.name,
        "status": agent.status,
        "visibility": agent.visibility,
        "taskContext": agent.task_context,
        "config": agent.config,
        "createdAt": agent.created_at.isoformat()
    }

@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)
    return {
        "id": str(agent.id),
        "teamId": str(agent.team_id),
        "name": agent.name,
        "status": agent.status,
        "containerId": agent.container_id,
        "visibility": agent.visibility,
        "taskContext": agent.task_context,
        "config": agent.config,
        "createdAt": agent.created_at.isoformat(),
        "startedAt": agent.started_at.isoformat() if agent.started_at else None,
        "stoppedAt": agent.stopped_at.isoformat() if agent.stopped_at else None
    }

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "admin", db)

    if agent.status == "running":
        stop_agent_task.delay(str(agent.id), agent.container_id)

    audit = AuditLog(team_id=agent.team_id, user_id=current_user.id, action="agent.delete", metadata_={"agentId": str(agent.id), "name": agent.name})
    db.add(audit)

    await db.delete(agent)
    await db.commit()
    return {"message": f"Agent '{agent.name}' deleted successfully"}

@router.post("/{agent_id}/start")
async def start_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)

    agent.status = "starting"
    audit = AuditLog(team_id=agent.team_id, user_id=current_user.id, action="agent.start", metadata_={"agentId": str(agent.id)})
    db.add(audit)
    await db.commit()

    spinup_agent_task.delay(str(agent.id))
    return {"id": str(agent.id), "status": "starting", "message": "Spinup task queued"}

@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)

    agent.status = "stopping"
    audit = AuditLog(team_id=agent.team_id, user_id=current_user.id, action="agent.stop", metadata_={"agentId": str(agent.id)})
    db.add(audit)
    await db.commit()

    stop_agent_task.delay(str(agent.id))
    return {"id": str(agent.id), "status": "stopping", "message": "Teardown task queued"}

class ContextUpdateSchema(BaseModel):
    taskContext: str

@router.patch("/{agent_id}/context")
async def update_agent_context(
    agent_id: str,
    data: ContextUpdateSchema,
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

    stmt = stmt.order_by(AgentMessage.created_at.asc(), AgentMessage.id.asc())
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

@router.delete("/{agent_id}/threads/{thread_id}")
async def delete_agent_thread(
    agent_id: str,
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)

    stmt = delete(AgentMessage).where(
        AgentMessage.agent_id == agent.id,
        AgentMessage.thread_id == thread_id
    )
    await db.execute(stmt)
    await db.commit()
    return {"message": f"Thread '{thread_id}' deleted successfully"}

@router.post("/{agent_id}/messages")
async def post_agent_message(
    agent_id: str,
    data: PostMessageSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "member", db)

    if agent.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Agent sandbox container is stopped. Please click 'Start Sandbox Container' above first."
        )

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

class UpdateVisibilitySchema(BaseModel):
    visibility: str

@router.patch("/{agent_id}/visibility")
async def update_agent_visibility(
    agent_id: str,
    data: UpdateVisibilitySchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    a_uuid = uuid.UUID(agent_id)
    agent = await check_agent_access(a_uuid, current_user.id, "admin", db)

    if data.visibility not in ["personal", "team"]:
        raise HTTPException(status_code=400, detail="Visibility must be 'personal' or 'team'")

    agent.visibility = data.visibility
    audit = AuditLog(team_id=agent.team_id, user_id=current_user.id, action="agent.visibility_update", metadata_={"agent_id": str(agent.id), "visibility": data.visibility})
    db.add(audit)
    await db.commit()

    return {"id": str(agent.id), "visibility": agent.visibility, "message": f"Agent visibility set to '{data.visibility}'"}
    