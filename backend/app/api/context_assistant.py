from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.api.auth import get_current_user
from app.db.models import User
from app.llm.provider import get_llm_provider
import datetime

router = APIRouter(prefix="/api/context-assistant", tags=["Context Assistant"])

class CompileContextSchema(BaseModel):
    goal: str
    docs: Optional[str] = "None"
    constraints: Optional[str] = "None"
    audience: Optional[str] = "General Operations Team"

@router.post("/compile")
async def compile_context_brief(
    data: CompileContextSchema,
    current_user: User = Depends(get_current_user)
):
    prompt_text = f"""You are a context brief compiler. Integrate the following questionnaire answers into a structured, professional project brief named "MEMORY.md".
Use clean Markdown hierarchy with sections like:
- # Objectives
- # Reference Documents
- # Implementation Constraints
- # Operational Audience

Questionnaire answers:
1. Agent Goal: "{data.goal}"
2. Reference Files/Docs: "{data.docs or 'None'}"
3. Deadlines/Constraints: "{data.constraints or 'None'}"
4. Intended Team/Audience: "{data.audience or 'General Operations Team'}"

Compile these raw points into a cohesive, concise, and structured brief. Return ONLY the formatted Markdown text. Do not wrap it in markdown backticks, just output raw markdown content.
"""
    compiled_md = ""
    try:
        provider = get_llm_provider()
        messages = [{"role": "user", "content": prompt_text}]
        compiled_md = await provider.generate(messages=messages, temperature=0.2, max_tokens=1024)
        compiled_md = compiled_md.strip("`").strip()
    except Exception as e:
        print(f"[Context Assistant] Error compiling brief via LLM: {e}")

    if not compiled_md:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d")
        compiled_md = f"""# Agent Operational Brief (MEMORY.md)

## 1. Objectives & Goals
- {data.goal}

## 2. Reference Documents & Knowledge Bases
- {data.docs or 'No additional reference files provided.'}

## 3. Implementation Constraints & Deadlines
- {data.constraints or 'Standard container sandbox guidelines apply (no internet access, readonly root fs).'}

## 4. Intended Team / Operational Audience
- This agent is provisioned to support the team: **{data.audience or 'General Operations Team'}**.

---
*Brief automatically compiled on {now_str} by the Context-Intake Assistant.*"""

    return {"compiledMd": compiled_md}
