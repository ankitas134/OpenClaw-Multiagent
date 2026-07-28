import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, RefreshToken, Team, TeamMember
from app.core.security import get_password_hash, verify_password, create_access_token, generate_refresh_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class RegisterSchema(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/register", status_code=201)
async def register(data: RegisterSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        name=data.name
    )
    db.add(new_user)
    await db.flush()

    default_team = Team(name=f"{data.name}'s Team", created_by=new_user.id)
    db.add(default_team)
    await db.flush()

    team_member = TeamMember(team_id=default_team.id, user_id=new_user.id, role="owner")
    db.add(team_member)
    await db.commit()

    return {"message": "User registered successfully", "id": str(new_user.id)}

@router.post("/login")
async def login(data: LoginSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = generate_refresh_token()

    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=get_password_hash(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(db_refresh)
    await db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "user": {"id": str(user.id), "email": user.email, "name": user.name}
    }

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    memberships_res = await db.execute(
        select(TeamMember, Team)
        .join(Team, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == current_user.id)
    )
    teams_list = []
    for member, team in memberships_res.all():
        teams_list.append({
            "teamId": str(team.id),
            "name": team.name,
            "role": member.role
        })

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "teams": teams_list
    }
