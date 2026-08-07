import uuid
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, Team, TeamMember, AuditLog
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/teams", tags=["Teams"])

class TeamCreateSchema(BaseModel):
    name: str

class TeamUpdateContextSchema(BaseModel):
    context_md: str

async def verify_team_membership(team_id: uuid.UUID, user_id: uuid.UUID, min_role: str, db: AsyncSession) -> TeamMember:
    res = await db.execute(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id))
    membership = res.scalars().first()
    if not membership:
        raise HTTPException(status_code=403, detail="Forbidden: You are not a member of this team")

    role_weights = {"member": 1, "admin": 2, "owner": 3}
    if role_weights.get(membership.role, 0) < role_weights.get(min_role, 0):
        raise HTTPException(status_code=403, detail=f"Forbidden: Requires at least '{min_role}' role")
    return membership

@router.post("/", status_code=201)
async def create_team(data: TeamCreateSchema, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    team = Team(name=data.name, created_by=current_user.id)
    db.add(team)
    await db.flush()

    member = TeamMember(team_id=team.id, user_id=current_user.id, role="owner")
    db.add(member)

    audit = AuditLog(team_id=team.id, user_id=current_user.id, action="team.create", metadata_={"name": data.name})
    db.add(audit)
    await db.commit()

    return {"id": str(team.id), "name": team.name, "contextMd": team.context_md}

@router.get("/{team_id}")
async def get_team(team_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t_uuid = uuid.UUID(team_id)
    await verify_team_membership(t_uuid, current_user.id, "member", db)

    res = await db.execute(select(Team).where(Team.id == t_uuid))
    team = res.scalars().first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return {"id": str(team.id), "name": team.name, "contextMd": team.context_md}

@router.patch("/{team_id}/context")
async def update_team_context(team_id: str, data: TeamUpdateContextSchema, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t_uuid = uuid.UUID(team_id)
    await verify_team_membership(t_uuid, current_user.id, "admin", db)

    res = await db.execute(select(Team).where(Team.id == t_uuid))
    team = res.scalars().first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    team.context_md = data.context_md
    audit = AuditLog(team_id=team.id, user_id=current_user.id, action="team.context_update", metadata_={"length": len(data.context_md)})
    db.add(audit)
    await db.commit()

    return {"id": str(team.id), "contextMd": team.context_md}

class AddMemberSchema(BaseModel):
    email: str
    role: str = "member"

@router.post("/{team_id}/members")
async def add_team_member(
    team_id: str,
    data: AddMemberSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t_uuid = uuid.UUID(team_id)
    await verify_team_membership(t_uuid, current_user.id, "admin", db)

    # Find user by email
    res = await db.execute(select(User).where(User.email == data.email))
    target_user = res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User with email '{data.email}' not found. Ask them to register first.")

    # Check if already a member
    mem_res = await db.execute(select(TeamMember).where(TeamMember.team_id == t_uuid, TeamMember.user_id == target_user.id))
    if mem_res.scalars().first():
        return {"message": f"User '{data.email}' is already a member of this team."}

    new_member = TeamMember(team_id=t_uuid, user_id=target_user.id, role=data.role)
    db.add(new_member)
    audit = AuditLog(team_id=t_uuid, user_id=current_user.id, action="team.add_member", metadata_={"email": data.email, "role": data.role})
    db.add(audit)
    await db.commit()

    return {"message": f"Successfully added '{data.email}' to the team workspace!"}

