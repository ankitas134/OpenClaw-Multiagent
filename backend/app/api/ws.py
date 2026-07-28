import asyncio
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.config import settings

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/agents/{agent_id}")
async def agent_events_websocket(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    redis_pubsub = aioredis.from_url(settings.REDIS_URL)
    pubsub = redis_pubsub.pubsub()
    channel = f"agent:{agent_id}:events"

    await pubsub.subscribe(channel)
    print(f"[WebSocket] Client connected for agent events: {agent_id}")

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                data_str = message["data"].decode("utf-8")
                await websocket.send_text(data_str)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected for agent {agent_id}")
    except Exception as e:
        print(f"[WebSocket] Error streaming events: {e}")
    finally:
        await pubsub.unsubscribe(channel)
        await redis_pubsub.close()
