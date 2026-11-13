"""Integration tests for recovered platform routes and provider boundaries."""
import json
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.core.config import Settings, settings
from app.integrations.judge0_adapter import ExecutionProviderError, Judge0Adapter
from app.main import app
from app.models.user import User
from app.database.session import SessionLocal

client = TestClient(app)


def register(name="Platform Test User"):
    response = client.post("/api/v1/auth/register", json={"email": f"platform_{uuid.uuid4().hex}@example.com", "password": "StrongPassword123!", "full_name": name})
    assert response.status_code == 201
    result = response.json()
    return {"Authorization": f"Bearer {result['access_token']}"}, result["user"]


def test_all_backend_routers_are_mounted():
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/auth/register", "/api/v1/users/me", "/api/v1/interviews", "/api/v1/interviewers",
        "/api/v1/coding/problems", "/api/v1/problems", "/api/v1/resumes", "/api/v1/evaluations/{session_id}",
        "/api/v1/analytics/overview", "/api/v1/companies", "/api/v1/roadmaps", "/api/v1/settings",
        "/api/v1/subscriptions/plans", "/api/v1/voice/status", "/api/v1/admin/overview",
    }
    assert expected <= set(paths)
    assert sum(len(operations) for operations in paths.values()) >= 40


def test_user_profile_settings_and_public_catalogs():
    headers, user = register()
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200 and response.json()["id"] == user["id"]
    assert client.patch("/api/v1/users/me", headers=headers, json={"full_name": "Updated Name"}).json()["full_name"] == "Updated Name"
    profile = client.patch("/api/v1/users/me/profile", headers=headers, json={"target_role": "Backend Engineer", "skills": ["Python", "SQL"]})
    assert profile.status_code == 200 and profile.json()["data"]["target_role"] == "Backend Engineer"
    assert client.get("/api/v1/users/me/profile", headers=headers).json()["data"]["skills"] == ["Python", "SQL"]
    prefs = client.patch("/api/v1/settings", headers=headers, json={"values": {"theme": "dark", "weekly_goal": 4}})
    assert prefs.status_code == 200 and prefs.json()["settings"]["theme"] == "dark"
    assert client.patch("/api/v1/settings", headers=headers, json={"values": {"JWT_SECRET_KEY": "leak"}}).status_code == 422
    assert client.get("/api/v1/interviewers").status_code == 200
    assert client.get("/api/v1/companies").status_code == 200
    roadmap = client.get("/api/v1/roadmaps", headers=headers)
    assert roadmap.status_code == 200 and roadmap.json()["items"]


def test_interviews_persist_turns_and_enforce_ownership(monkeypatch):
    import app.api.v1.interviews as interviews
    async def question(*args, **kwargs):
        return "Tell me about a technical challenge you solved."
    monkeypatch.setattr(interviews, "generate_text", question)
    owner, _ = register("Interview Owner")
    other, _ = register("Different User")
    created = client.post("/api/v1/interviews", headers=owner, json={"role": "Backend Engineer", "interview_type": "technical"})
    assert created.status_code == 201
    session_id = created.json()["id"]
    assert created.json()["turns"][0]["content"] == "Tell me about a technical challenge you solved."
    assert client.get(f"/api/v1/interviews/{session_id}", headers=other).status_code == 404
    monkeypatch.setattr(interviews, "generate_text", question)
    answered = client.post(f"/api/v1/interviews/{session_id}/turns", headers=owner, json={"content": "I reduced API latency by profiling a slow query."})
    assert answered.status_code == 200 and len(answered.json()["turns"]) == 3
    assert client.post(f"/api/v1/interviews/{session_id}/finish", headers=owner).json()["status"] == "completed"
    assert client.post(f"/api/v1/interviews/{session_id}/turns", headers=owner, json={"content": "A late answer"}).status_code == 409


def test_evaluation_is_persisted_and_owned(monkeypatch):
    import app.api.v1.interviews as interviews
    import app.api.v1.evaluations as evaluations
    async def question(*args, **kwargs):
        return "Describe a difficult project decision."
    async def scoring(*args, **kwargs):
        return json.dumps({"communication": 80, "problem_solving": 85, "role_knowledge": 78, "structure": 82, "overall": 81, "summary": "Clear example; quantify the outcome."})
    monkeypatch.setattr(interviews, "generate_text", question)
    monkeypatch.setattr(evaluations, "generate_text", scoring)
    headers, _ = register()
    created = client.post("/api/v1/interviews", headers=headers, json={"role": "Engineer"}).json()
    session_id = created["id"]
    client.post(f"/api/v1/interviews/{session_id}/turns", headers=headers, json={"content": "I worked through the issue with the team."})
    result = client.post(f"/api/v1/evaluations/{session_id}", headers=headers)
    assert result.status_code == 200 and result.json()["total_score"] == 81
    assert client.get(f"/api/v1/evaluations/{session_id}", headers=headers).json()["summary"] == "Clear example; quantify the outcome."


def test_resume_upload_download_and_owner_isolation(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "STORAGE_LOCAL_DIR", str(tmp_path))
    owner, _ = register("Resume Owner")
    other, _ = register("Resume Other")
    uploaded = client.post("/api/v1/resumes", headers=owner, files={"file": ("resume.txt", b"Python engineer with database experience", "text/plain")})
    assert uploaded.status_code == 201
    record = uploaded.json()
    assert record["size_bytes"] > 0 and record["filename"] == "resume.txt"
    assert client.get(f"/api/v1/resumes/{record['id']}/download", headers=owner).content == b"Python engineer with database experience"
    assert client.get(f"/api/v1/resumes/{record['id']}/download", headers=other).status_code == 404
    assert client.delete(f"/api/v1/resumes/{record['id']}", headers=owner).status_code == 204
    assert client.get(f"/api/v1/resumes/{record['id']}/download", headers=owner).status_code == 404


def test_resume_rejects_unknown_or_invalid_file(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STORAGE_LOCAL_DIR", str(tmp_path))
    headers, _ = register()
    assert client.post("/api/v1/resumes", headers=headers, files={"file": ("x.exe", b"x", "application/octet-stream")}).status_code == 415
    assert client.post("/api/v1/resumes", headers=headers, files={"file": ("bad.pdf", b"not pdf", "application/pdf")}).status_code == 422


def test_websocket_uses_scoped_short_lived_token_and_persists_turn(monkeypatch):
    import app.api.v1.interviews as interviews
    import app.websocket.interview_socket as ws
    async def question(*args, **kwargs):
        return "What trade-off would you revisit?"
    monkeypatch.setattr(interviews, "generate_text", question)
    monkeypatch.setattr(ws, "generate_text", question)
    headers, _ = register()
    session_id = client.post("/api/v1/interviews", headers=headers, json={"role": "Engineer"}).json()["id"]
    response = client.post(f"/api/v1/interviews/{session_id}/socket-token", headers=headers)
    assert response.status_code == 200 and response.json()["expires_in"] == 120
    with client.websocket_connect(f"/api/v1/ws/interviews/{session_id}?token={response.json()['token']}") as socket:
        socket.send_json({"type": "answer", "content": "I would add monitoring first."})
        message = socket.receive_json()
        assert message["type"] == "question" and message["content"] == "What trade-off would you revisit?"
    with SessionLocal() as db:
        from app.models.platform import InterviewTurn
        assert db.query(InterviewTurn).filter_by(session_id=session_id, role="user").count() == 1


def test_subscription_and_voice_status_are_explicit():
    headers, _ = register()
    assert client.get("/api/v1/subscriptions/plans").status_code == 200
    assert client.get("/api/v1/subscriptions/me", headers=headers).json()["plan"] == "free"
    assert client.get("/api/v1/subscriptions/me").status_code == 401
    assert client.post("/api/v1/subscriptions/checkout", headers=headers, json={"success_url": "https://frontend.example/success", "cancel_url": "https://frontend.example/cancel"}).status_code == 503
    voice = client.get("/api/v1/voice/status")
    assert voice.status_code == 200 and voice.json()["provider"] == "browser"


def test_admin_routes_require_admin_role():
    headers, user = register()
    assert client.get("/api/v1/admin/overview", headers=headers).status_code == 403
    with SessionLocal() as db:
        db.query(User).filter_by(id=user["id"]).update({"role": "admin"})
        db.commit()
    assert client.get("/api/v1/admin/overview", headers=headers).status_code == 200


def test_judge0_requires_tls_except_local_development(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    with pytest.raises(ExecutionProviderError):
        Judge0Adapter("http://judge0.example/api", "test-key")
    assert Judge0Adapter("http://127.0.0.1:2358", "dev-key")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(ExecutionProviderError):
        Judge0Adapter("http://127.0.0.1:2358", "dev-key")
    assert Judge0Adapter("https://judge0.example/api", "key")


def test_production_settings_reject_missing_integrations_and_mask_secrets():
    valid = {
        "APP_ENV": "production", "DEBUG": False, "APP_SECRET_KEY": "a" * 40, "JWT_SECRET_KEY": "b" * 40,
        "DATABASE_URL": "postgresql+psycopg://user:pass@localhost/db", "REDIS_URL": "rediss://token@redis.example:6380/0", "FRONTEND_ORIGINS": "https://saksham.example",
        "AI_PROVIDER": "openai", "OPENAI_API_KEY": "openai-test-key", "JUDGE0_API_URL": "https://judge.example",
        "JUDGE0_API_KEY": "judge-test-key", "STORAGE_PROVIDER": "s3", "STORAGE_S3_BUCKET": "private-bucket",
        "STORAGE_S3_ACCESS_KEY_ID": "access-test-key", "STORAGE_S3_SECRET_ACCESS_KEY": "secret-test-key",
    }
    configured = Settings(_env_file=None, **valid)
    assert "openai-test-key" not in repr(configured)
    assert "user:pass" not in repr(configured)
    assert configured.OPENAI_API_KEY.get_secret_value() == "openai-test-key"
    invalid = {**valid, "JUDGE0_API_URL": "http://judge.example"}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **invalid)
    invalid = {**valid, "STORAGE_PROVIDER": "local"}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **invalid)




def test_voice_synthesis_requires_authentication(monkeypatch):
    monkeypatch.setattr(settings, "VOICE_PROVIDER", "elevenlabs")
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "test-voice-key")
    monkeypatch.setattr(settings, "ELEVENLABS_VOICE_ID", "voice")
    assert client.post("/api/v1/voice/speech", json={"text": "hello"}).status_code == 401


def test_stripe_checkout_does_not_grant_entitlement_until_subscription_active(monkeypatch):
    monkeypatch.setattr(settings, "SUBSCRIPTION_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec-test")
    headers, user = register("Stripe User")

    def send_event(event_type, obj):
        payload = json.dumps({"type": event_type, "data": {"object": obj}}).encode()
        timestamp = int(time.time())
        signature = hmac.new(b"whsec-test", str(timestamp).encode() + b"." + payload, hashlib.sha256).hexdigest()
        return client.post("/api/v1/subscriptions/webhook", content=payload, headers={"stripe-signature": f"t={timestamp},v1={signature}"})

    checkout_event = send_event("checkout.session.completed", {"id": "cs_test", "client_reference_id": user["id"], "subscription": "sub_test", "metadata": {"user_id": user["id"]}})
    assert checkout_event.status_code == 200
    assert client.get("/api/v1/subscriptions/me", headers=headers).json()["status"] == "pending"

    active_event = send_event("customer.subscription.created", {"id": "sub_test", "status": "active", "current_period_end": int(time.time()) + 3600, "metadata": {"user_id": user["id"]}})
    assert active_event.status_code == 200
    subscription = client.get("/api/v1/subscriptions/me", headers=headers).json()
    assert subscription["plan"] == "pro" and subscription["status"] == "active"
