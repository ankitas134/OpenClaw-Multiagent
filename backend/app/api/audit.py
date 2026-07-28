import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, AuditLog
from app.api.auth import get_current_user
from app.api.teams import verify_team_membership

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])

@router.get("/")
async def list_audit_logs(
    teamId: str = Query(..., description="Target Team ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t_uuid = uuid.UUID(teamId)
    await verify_team_membership(t_uuid, current_user.id, "member", db)

    res = await db.execute(
        select(AuditLog)
        .where(AuditLog.team_id == t_uuid)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    logs = res.scalars().all()
    return [{
        "id": str(l.id),
        "teamId": str(l.team_id) if l.team_id else None,
        "userId": str(l.user_id) if l.user_id else None,
        "action": l.action,
        "metadata": l.metadata_,
        "createdAt": l.created_at.isoformat() if l.created_at else None
    } for l in logs]
