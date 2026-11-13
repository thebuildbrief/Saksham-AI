"""Authenticated, short-token, database-backed interview WebSocket."""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.config import settings
from app.core.security import decode_interview_socket_token
from app.database.session import SessionLocal
from app.integrations.ai_provider import generate_text
from app.models.interview import InterviewSession
from app.models.platform import InterviewContext, InterviewTurn

router = APIRouter(tags=["Interview WebSocket"])


@router.websocket("/ws/interviews/{session_id}")
async def interview_socket(websocket: WebSocket, session_id: str, token: str = ""):
    origin = websocket.headers.get("origin")
    credential = decode_interview_socket_token(token)
    if (origin and origin.rstrip("/") not in settings.cors_origins) or not credential or credential["session_id"] != session_id:
        await websocket.close(code=4401)
        return
    with SessionLocal() as db:
        session = db.query(InterviewSession).filter_by(id=session_id, user_id=credential["user_id"], status="active").first()
        context = db.query(InterviewContext).filter_by(session_id=session_id).first() if session else None
        if not session:
            await websocket.close(code=4404)
            return
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > 16 * 1024:
                await websocket.close(code=1009, reason="Message too large")
                return
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Send a JSON message"})
                continue
            if not isinstance(message, dict) or message.get("type") != "answer" or not isinstance(message.get("content"), str):
                if isinstance(message, dict) and message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
                await websocket.send_json({"type": "error", "detail": "Expected an answer message"})
                continue
            answer = message["content"].strip()
            if not answer or len(answer) > 12000:
                await websocket.send_json({"type": "error", "detail": "Answer must contain 1 to 12000 characters"})
                continue
            with SessionLocal() as db:
                active = db.query(InterviewSession).filter_by(id=session_id, user_id=credential["user_id"], status="active").first()
                if not active:
                    await websocket.send_json({"type": "error", "detail": "Interview session is no longer active"})
                    await websocket.close(code=4409)
                    return
                db.add(InterviewTurn(session_id=session_id, role="user", content=answer))
                db.commit()
                turns = db.query(InterviewTurn).filter_by(session_id=session_id).order_by(InterviewTurn.created_at.asc(), InterviewTurn.id.asc()).limit(32).all()
                history = "\n".join(f"{turn.role}: {turn.content}" for turn in turns)
            try:
                question = await generate_text(
                    f"Role: {context.role if context else 'general'}. Type: {context.interview_type if context else 'behavioral'}.\n{history}\nAsk one relevant next interview question.",
                    system="You are a fair interview coach. Ask one clear question at a time.", max_tokens=240,
                )
            except Exception:
                await websocket.send_json({"type": "error", "detail": "AI service is temporarily unavailable"})
                continue
            with SessionLocal() as db:
                active = db.query(InterviewSession).filter_by(id=session_id, user_id=credential["user_id"], status="active").first()
                if not active:
                    await websocket.close(code=4409)
                    return
                turn = InterviewTurn(session_id=session_id, role="assistant", content=question)
                db.add(turn)
                db.commit()
                db.refresh(turn)
                await websocket.send_json({"type": "question", "id": turn.id, "content": question, "created_at": turn.created_at.isoformat()})
    except WebSocketDisconnect:
        return
