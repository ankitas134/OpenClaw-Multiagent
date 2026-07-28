import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, Table
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base

# Association table for Agent <-> Document
agent_documents = Table(
    'agent_documents',
    Base.metadata,
    Column('agent_id', UUID(as_uuid=True), ForeignKey('agents.id', ondelete='CASCADE'), primary_key=True),
    Column('document_id', UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    memberships = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")

class Team(Base):
    __tablename__ = 'teams'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    context_md = Column(Text, default='', nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="team", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="team", cascade="all, delete-orphan")

class TeamMember(Base):
    __tablename__ = 'team_members'
    team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role = Column(String, default='member', nullable=False) # owner, admin, member
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="memberships")

class Invite(Base):
    __tablename__ = 'invites'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, default='member', nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

class Agent(Base):
    __tablename__ = 'agents'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    name = Column(String, nullable=False)
    config = Column(JSONB, default=dict, nullable=False)
    container_id = Column(String, nullable=True)
    status = Column(String, default='pending', nullable=False) # pending, starting, running, stopping, stopped, failed
    visibility = Column(String, default='personal', nullable=False) # personal, team
    task_context = Column(Text, default='', nullable=False)
    workspace_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)

    team = relationship("Team", back_populates="agents")
    documents = relationship("Document", secondary=agent_documents, back_populates="agents")
    runs = relationship("AgentRun", back_populates="agent", cascade="all, delete-orphan")
    messages = relationship("AgentMessage", back_populates="agent", cascade="all, delete-orphan")

class AgentRun(Base):
    __tablename__ = 'agent_runs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String, nullable=False) # status_change, log, error
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    agent = relationship("Agent", back_populates="runs")

class AgentMessage(Base):
    __tablename__ = 'agent_messages'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    sender = Column(String, nullable=False) # user | agent
    text = Column(Text, nullable=False)
    thread_id = Column(String, nullable=True)
    attachments = Column(JSONB, default=list, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    agent = relationship("Agent", back_populates="messages")

class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id', ondelete='SET NULL'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class Document(Base):
    __tablename__ = 'documents'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    visibility = Column(String, default='team', nullable=False) # personal, team
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)
    extracted_text_path = Column(String, nullable=True)
    extraction_status = Column(String, default='pending', nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    team = relationship("Team", back_populates="documents")
    agents = relationship("Agent", secondary=agent_documents, back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = 'document_chunks'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)

    document = relationship("Document", back_populates="chunks")
