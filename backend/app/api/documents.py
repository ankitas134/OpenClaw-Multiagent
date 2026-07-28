import os
import uuid
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, Document, AuditLog
from app.api.auth import get_current_user
from app.api.teams import verify_team_membership
from app.tasks.tasks import extract_document_task

router = APIRouter(prefix="/api/documents", tags=["Documents"])

DATA_DOCS_ROOT = os.path.abspath(os.path.join(os.getcwd(), "data", "documents"))

@router.post("/{team_id}")
async def upload_document(
    team_id: str,
    file: UploadFile = File(...),
    visibility: Optional[str] = Form("team"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t_uuid = uuid.UUID(team_id)
    await verify_team_membership(t_uuid, current_user.id, "member", db)

    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    allowed_exts = ["pdf", "docx", "txt", "md", "csv"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type .{ext}. Allowed: {', '.join(allowed_exts)}")

    doc_id = uuid.uuid4()
    target_dir = os.path.join(DATA_DOCS_ROOT, str(t_uuid), str(doc_id))
    os.makedirs(target_dir, exist_ok=True)
    target_file_path = os.path.join(target_dir, file.filename)

    with open(target_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size_bytes = os.path.getsize(target_file_path)

    doc = Document(
        id=doc_id,
        team_id=t_uuid,
        uploaded_by=current_user.id,
        visibility=visibility or "team",
        filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        storage_path=target_file_path,
        extraction_status="pending"
    )
    db.add(doc)

    audit = AuditLog(team_id=t_uuid, user_id=current_user.id, action="document.upload", metadata_={"docId": str(doc_id), "filename": file.filename})
    db.add(audit)
    await db.commit()

    extract_document_task.delay(str(doc.id))

    return {
        "id": str(doc.id),
        "teamId": str(doc.team_id),
        "filename": doc.filename,
        "mimeType": doc.mime_type,
        "sizeBytes": doc.size_bytes,
        "extractionStatus": doc.extraction_status,
        "createdAt": doc.created_at.isoformat()
    }

@router.get("/{team_id}")
async def list_documents(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t_uuid = uuid.UUID(team_id)
    await verify_team_membership(t_uuid, current_user.id, "member", db)

    res = await db.execute(
        select(Document)
        .where(Document.team_id == t_uuid)
        .order_by(Document.created_at.desc())
    )
    docs = res.scalars().all()
    return [{
        "id": str(d.id),
        "teamId": str(d.team_id),
        "uploadedBy": str(d.uploaded_by) if d.uploaded_by else None,
        "visibility": d.visibility,
        "filename": d.filename,
        "mimeType": d.mime_type,
        "sizeBytes": d.size_bytes,
        "extractionStatus": d.extraction_status,
        "createdAt": d.created_at.isoformat() if d.created_at else None
    } for d in docs]

@router.delete("/{team_id}/{doc_id}")
async def delete_document(
    team_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t_uuid = uuid.UUID(team_id)
    d_uuid = uuid.UUID(doc_id)
    await verify_team_membership(t_uuid, current_user.id, "member", db)

    res = await db.execute(select(Document).where(Document.id == d_uuid, Document.team_id == t_uuid))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    target_dir = os.path.join(DATA_DOCS_ROOT, str(t_uuid), str(d_uuid))
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)

    await db.delete(doc)
    audit = AuditLog(team_id=t_uuid, user_id=current_user.id, action="document.delete", metadata_={"docId": doc_id, "filename": doc.filename})
    db.add(audit)
    await db.commit()

    return {"success": True, "message": "Document deleted successfully"}
