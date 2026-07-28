import os
import json
import redis
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.sandboxing.docker_manager import spinup_agent_container, stop_agent_container, exec_container_command
from app.llm.provider import get_llm_provider
from app.rag.embeddings import generate_embedding, cosine_similarity

sync_engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
redis_client = redis.Redis.from_url(settings.REDIS_URL)

def publish_agent_event(agent_id: str, event_type: str, payload: dict):
    channel = f"agent:{agent_id}:events"
    message = json.dumps({"eventType": event_type, "payload": payload})
    redis_client.publish(channel, message)

@celery_app.task
def spinup_agent_task(agent_id: str):
    print(f"[Celery] Starting spinup task for agent {agent_id}")
    with sync_engine.connect() as conn:
        res = conn.execute(
            text("""
                SELECT a.*, t.name as team_name, t.context_md as team_context
                FROM agents a
                JOIN teams t ON a.team_id = t.id
                WHERE a.id = :agent_id
            """),
            {"agent_id": agent_id}
        ).fetchone()

        if not res:
            print(f"[Celery] Agent {agent_id} not found.")
            return

        agent = dict(res._mapping)

        conn.execute(
            text("UPDATE agents SET status = 'starting' WHERE id = :agent_id"),
            {"agent_id": agent_id}
        )
        conn.commit()

        publish_agent_event(agent_id, "status_change", {"status": "starting", "text": "Container spin-up initiated"})

        try:
            container_id = spinup_agent_container(
                agent_id=str(agent["id"]),
                team_name=agent["team_name"],
                team_context=agent["team_context"] or "",
                agent_name=agent["name"],
                task_context=agent["task_context"] or "",
                config=agent["config"] or {}
            )

            workspace_path = os.path.join(settings.WORKSPACES_ROOT, str(agent_id))
            is_dev_mode = container_id.startswith("local-dev-agent-")
            status_text = "unsandboxed (dev mode)" if is_dev_mode else "running"
            event_text = "Agent is running (unsandboxed dev mode)" if is_dev_mode else "Agent is running inside sandbox"

            conn.execute(
                text("""
                    UPDATE agents 
                    SET status = :status, container_id = :container_id, workspace_path = :workspace_path, started_at = :now
                    WHERE id = :agent_id
                """),
                {
                    "status": status_text,
                    "container_id": container_id,
                    "workspace_path": workspace_path,
                    "now": datetime.now(timezone.utc),
                    "agent_id": agent_id
                }
            )

            conn.execute(
                text("INSERT INTO agent_runs (agent_id, event_type, payload) VALUES (:agent_id, 'status_change', :payload)"),
                {
                    "agent_id": agent_id,
                    "payload": json.dumps({"status": status_text, "text": event_text})
                }
            )
            conn.commit()

            publish_agent_event(agent_id, "status_change", {"status": status_text, "text": event_text})
            print(f"[Celery] Agent {agent_id} successfully spun up ({status_text}, ID: {container_id[:12]})")

        except Exception as e:
            print(f"[Celery] Error spinning up agent {agent_id}: {e}")
            conn.execute(
                text("UPDATE agents SET status = 'failed' WHERE id = :agent_id"),
                {"agent_id": agent_id}
            )
            conn.execute(
                text("INSERT INTO agent_runs (agent_id, event_type, payload) VALUES (:agent_id, 'error', :payload)"),
                {
                    "agent_id": agent_id,
                    "payload": json.dumps({"status": "failed", "error": f"Sandboxing failed: {e}"})
                }
            )
            conn.commit()
            publish_agent_event(agent_id, "status_change", {"status": "failed", "error": f"Sandboxing failed: {e}"})

@celery_app.task
def stop_agent_task(agent_id: str):
    print(f"[Celery] Stopping agent {agent_id}")
    with sync_engine.connect() as conn:
        res = conn.execute(
            text("SELECT container_id FROM agents WHERE id = :agent_id"),
            {"agent_id": agent_id}
        ).fetchone()

        if res and res._mapping["container_id"]:
            stop_agent_container(res._mapping["container_id"])

        conn.execute(
            text("""
                UPDATE agents 
                SET status = 'stopped', container_id = NULL, stopped_at = :now 
                WHERE id = :agent_id
            """),
            {"now": datetime.now(timezone.utc), "agent_id": agent_id}
        )
        conn.execute(
            text("INSERT INTO agent_runs (agent_id, event_type, payload) VALUES (:agent_id, 'status_change', :payload)"),
            {
                "agent_id": agent_id,
                "payload": json.dumps({"status": "stopped", "text": "Agent container stopped"})
            }
        )
        conn.commit()
        publish_agent_event(agent_id, "status_change", {"status": "stopped", "text": "Agent stopped"})

@celery_app.task
def extract_document_task(document_id: str):
    print(f"[Celery] Processing document extraction for {document_id}")
    with sync_engine.connect() as conn:
        doc_res = conn.execute(
            text("SELECT * FROM documents WHERE id = :doc_id"),
            {"doc_id": document_id}
        ).fetchone()

        if not doc_res:
            return

        doc = dict(doc_res._mapping)
        file_path = os.path.abspath(doc["storage_path"])

        if not os.path.exists(file_path):
            print(f"[Celery] Document file not found at: {file_path}")
            conn.execute(text("UPDATE documents SET extraction_status = 'failed' WHERE id = :doc_id"), {"doc_id": document_id})
            conn.commit()
            return

        extracted_text = ""
        ext = os.path.splitext(doc["filename"])[1].lower()

        try:
            if ext == ".docx":
                import mammoth
                with open(file_path, "rb") as docx_file:
                    result = mammoth.extract_raw_text(docx_file)
                    extracted_text = result.value
            elif ext == ".pdf":
                import pypdf
                reader = pypdf.PdfReader(file_path)
                pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
                extracted_text = "\n".join(pages_text)
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    extracted_text = f.read()

            if not extracted_text.strip():
                extracted_text = "[No printable text found in file]"

            chunk_size = 500
            overlap = 50
            chunks = []
            start = 0
            text_len = len(extracted_text)

            while start < text_len:
                end = min(start + chunk_size, text_len)
                chunk_str = extracted_text[start:end]
                chunks.append(chunk_str)
                if end == text_len:
                    break
                start += (chunk_size - overlap)

            conn.execute(text("DELETE FROM document_chunks WHERE document_id = :doc_id"), {"doc_id": document_id})

            for idx, chunk_content in enumerate(chunks):
                emb = generate_embedding(chunk_content)
                emb_str = f"[{','.join(map(str, emb))}]"
                conn.execute(
                    text("""
                        INSERT INTO document_chunks (document_id, chunk_index, content, embedding)
                        VALUES (:doc_id, :idx, :content, CAST(:emb AS vector))
                    """),
                    {
                        "doc_id": document_id,
                        "idx": idx,
                        "content": chunk_content,
                        "emb": emb_str
                    }
                )

            conn.execute(text("UPDATE documents SET extraction_status = 'done' WHERE id = :doc_id"), {"doc_id": document_id})
            conn.commit()
            print(f"[Celery] Extracted {len(chunks)} chunks for document {doc['filename']}")

        except Exception as e:
            print(f"[Celery] Document extraction failed for {document_id}: {e}")
            conn.execute(text("UPDATE documents SET extraction_status = 'failed' WHERE id = :doc_id"), {"doc_id": document_id})
            conn.commit()

@celery_app.task
def process_message_task(agent_id: str, message_id: str):
    print(f"[Celery] Processing message {message_id} for agent {agent_id}")
    with sync_engine.connect() as conn:
        msg_res = conn.execute(
            text("SELECT * FROM agent_messages WHERE id = :msg_id"),
            {"msg_id": message_id}
        ).fetchone()

        if not msg_res:
            return
        user_msg = dict(msg_res._mapping)

        agent_res = conn.execute(
            text("""
                SELECT a.*, t.name as team_name, t.context_md as team_context
                FROM agents a
                JOIN teams t ON a.team_id = t.id
                WHERE a.id = :agent_id
            """),
            {"agent_id": agent_id}
        ).fetchone()

        if not agent_res:
            return
        agent = dict(agent_res._mapping)

        if agent.get("container_id") and agent["status"] == "running":
            try:
                exec_container_command(agent["container_id"], f"echo '[CHAT] ({datetime.now(timezone.utc).isoformat()}) Message: {user_msg['text']}' >> /workspace/chat.log")
            except Exception as ex:
                print(f"[Celery] Container exec warning: {ex}")

        query_emb = generate_embedding(user_msg["text"])

        chunks_res = conn.execute(
            text("""
                SELECT c.content, d.filename, c.embedding
                FROM documents d
                JOIN document_chunks c ON c.document_id = d.id
                LEFT JOIN agent_documents ad ON ad.document_id = d.id AND ad.agent_id = :agent_id
                WHERE (ad.agent_id = :agent_id OR d.team_id = :team_id)
            """),
            {"agent_id": agent_id, "team_id": agent["team_id"]}
        ).fetchall()

        matched_chunks = []
        for row in chunks_res:
            r = dict(row._mapping)
            emb_vec = r["embedding"]
            if isinstance(emb_vec, str):
                emb_vec = [float(x) for x in emb_vec.strip("[]").split(",")]
            score = cosine_similarity(query_emb, emb_vec)
            if score > 0.15:
                matched_chunks.append({"content": r["content"], "filename": r["filename"], "score": score})

        matched_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = matched_chunks[:5]

        if top_chunks:
            context_str = ""
            for chunk in top_chunks:
                context_str += f"\n--- Document: {chunk['filename']} ---\n{chunk['content']}\n"

            system_prompt = f"""You are an AI assistant for agent "{agent['name']}" in team "{agent['team_name']}".
Task Context: {agent['task_context']}

Answer the user's message using the reference team document excerpts provided below whenever applicable.

Reference Team Documents:
\"\"\"
{context_str}
\"\"\"

Standing Team Guidelines:
\"\"\"
{agent['team_context']}
\"\"\"
"""
        else:
            system_prompt = f"""You are an AI assistant for agent "{agent['name']}" in team "{agent['team_name']}".

Agent Task Context:
\"\"\"
{agent['task_context'] or 'Provide helpful operational assistance.'}
\"\"\"

Standing Team Guidelines:
\"\"\"
{agent['team_context'] or 'Standard operating procedures.'}
\"\"\"
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg["text"]}
        ]

        try:
            provider = get_llm_provider()
            import asyncio
            reply_text = asyncio.run(provider.generate(messages=messages, temperature=0.1, max_tokens=1024))
        except Exception as e:
            print(f"[Celery] LLM Provider generation error: {e}")
            reply_text = "I'm sorry, an error occurred while processing the response from the LLM provider."

        reply_res = conn.execute(
            text("""
                INSERT INTO agent_messages (agent_id, user_id, sender, text, thread_id)
                VALUES (:agent_id, NULL, 'agent', :text, :thread_id)
                RETURNING *
            """),
            {
                "agent_id": agent_id,
                "text": reply_text,
                "thread_id": user_msg["thread_id"]
            }
        )
        conn.commit()
        agent_reply = dict(reply_res.fetchone()._mapping)

        publish_agent_event(agent_id, "chat_message_status", {"id": message_id, "status": "sent"})
        publish_agent_event(agent_id, "chat_message", {
            "id": str(agent_reply["id"]),
            "agentId": str(agent_reply["agent_id"]),
            "userId": None,
            "sender": "agent",
            "text": agent_reply["text"],
            "threadId": agent_reply["thread_id"],
            "createdAt": agent_reply["created_at"].isoformat()
        })

@celery_app.task
def prune_idle_agents_task(idle_hours: int = 2):
    print(f"[Celery Periodic Task] Checking for idle agents older than {idle_hours} hours...")
    with sync_engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT a.id, a.name, a.container_id, COALESCE(MAX(r.created_at), a.started_at) as last_activity
                FROM agents a
                LEFT JOIN agent_runs r ON a.id = r.agent_id
                WHERE a.status = 'running'
                GROUP BY a.id, a.name, a.container_id, a.started_at
                HAVING COALESCE(MAX(r.created_at), a.started_at) < (NOW() - (:hours || ' hours')::interval)
            """),
            {"hours": str(idle_hours)}
        ).fetchall()

        if result:
            print(f"[Celery Periodic Task] Pruning {len(result)} idle agents...")
            for row in result:
                r = dict(row._mapping)
                agent_id = str(r["id"])
                print(f"[Celery Periodic Task] Pruning idle agent '{r['name']}' ({agent_id})")
                if r["container_id"]:
                    stop_agent_container(r["container_id"])
                conn.execute(
                    text("UPDATE agents SET status = 'stopped', container_id = NULL, stopped_at = NOW() WHERE id = :id"),
                    {"id": agent_id}
                )
                conn.execute(
                    text("INSERT INTO audit_logs (id, action, metadata, created_at) VALUES (gen_random_uuid(), 'agent.idle_prune', :meta::jsonb, NOW())"),
                    {"meta": json.dumps({"agentId": agent_id, "name": r["name"]})}
                )
            conn.commit()
            print("[Celery Periodic Task] Idle agent pruning completed.")
        else:
            print("[Celery Periodic Task] No idle agents found.")
