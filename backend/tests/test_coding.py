"""API, validation, ownership, and result tests for code execution."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.judge0_adapter import ExecutionProviderError, Judge0Adapter
from app.main import app
from app.database.session import SessionLocal
from app.models.coding import CodingSubmission
from app.models.interview import InterviewSession
from app.services.execution_engine import _EXECUTION_SLOTS, _outputs_match


client = TestClient(app)


def register_user():
    email = f"coding_{uuid.uuid4().hex}@example.com"
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Coding Test User",
    })
    assert response.status_code == 201
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["id"]


def configure_provider(monkeypatch):
    monkeypatch.setattr(settings, "JUDGE0_API_URL", "https://judge0.test")
    monkeypatch.setattr(settings, "JUDGE0_API_KEY", "test-only-key")


def test_coding_problem_catalog():
    response = client.get("/api/v1/coding/problems")
    assert response.status_code == 200
    problems = response.json()
    assert len(problems) >= 3
    assert any(problem["id"] == "two-sum" for problem in problems)


def test_execute_requires_authentication(monkeypatch):
    monkeypatch.setattr(settings, "JUDGE0_API_URL", "")
    monkeypatch.setattr(settings, "JUDGE0_API_KEY", "")
    response = client.post("/api/v1/coding/execute", json={
        "problem_id": "two-sum", "language": "python", "code": "print('x')",
    })
    assert response.status_code == 401


@pytest.mark.parametrize("payload", [
    {"problem_id": "../users", "language": "python", "code": "print(1)"},
    {"problem_id": "two-sum", "language": "ruby", "code": "puts 1"},
    {"problem_id": "two-sum", "language": "python", "code": "x" * (32 * 1024 + 1)},
    {"problem_id": "two-sum", "language": "python", "code": "print(1)", "custom_input": "😀" * 8193},
])
def test_execution_request_validation(payload):
    headers, _ = register_user()
    response = client.post("/api/v1/coding/execute", json=payload, headers=headers)
    assert response.status_code == 422


def test_execution_body_limit_precedes_json_parsing():
    response = client.post(
        "/api/v1/coding/execute",
        content=b"{" + (b" " * (64 * 1024)) + b"}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_unconfigured_provider_fails_closed(monkeypatch):
    headers, _ = register_user()
    monkeypatch.setattr(settings, "JUDGE0_API_URL", "")
    monkeypatch.setattr(settings, "JUDGE0_API_KEY", "")
    response = client.post("/api/v1/coding/execute", json={
        "problem_id": "two-sum", "language": "python", "code": "print(1)",
    }, headers=headers)
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_test_cases_execute_independently_and_hidden_data_is_redacted(monkeypatch):
    configure_provider(monkeypatch)
    headers, user_id = register_user()
    seen_inputs = []
    expected_by_input = {
        "[2, 7, 11, 15]\n9": "[0, 1]",
        "[3, 2, 4]\n6": "[1, 2]",
        "[3, 3]\n6": "[0, 1]",
    }
    source = f"owner-check-{uuid.uuid4().hex}"

    async def fake_execute(self, language, source_code, stdin=""):
        seen_inputs.append(stdin)
        return {
            "stdout": expected_by_input[stdin], "stderr": "", "compile_output": "",
            "time_ms": 5, "memory_kb": 1000, "status_desc": "Accepted",
        }

    monkeypatch.setattr(Judge0Adapter, "execute", fake_execute)
    response = client.post("/api/v1/coding/execute", json={
        "problem_id": "two-sum", "language": "python", "code": source,
    }, headers=headers)

    assert response.status_code == 200
    result = response.json()
    assert len(seen_inputs) == len(expected_by_input)
    assert set(seen_inputs) == set(expected_by_input)
    assert result["status"] == "Accepted"
    assert result["passed_tests"] == result["total_tests"] == 3
    assert len(result["test_results"]) == 3
    hidden_results = [item for item in result["test_results"] if item["input_data"] == "[Hidden Test Case]"]
    assert len(hidden_results) == 1
    hidden = hidden_results[0]
    assert hidden["input_data"] == "[Hidden Test Case]"
    assert hidden["expected_output"] == "[Hidden]"
    for item in result["test_results"]:
        if item["input_data"] != "[Hidden Test Case]":
            assert item["expected_output"] == expected_by_input[item["input_data"]]
        assert item["passed"] is True
    assert "[3, 3]" not in response.text
    with SessionLocal() as db:
        submission = db.query(CodingSubmission).filter(CodingSubmission.code == source).one()
        assert submission.user_id == user_id


def test_exact_output_comparison_rejects_substrings():
    assert _outputs_match("two-sum", "[0, 1]", "[1, 0]")
    assert not _outputs_match("valid-parentheses", "true", "not true")
    assert not _outputs_match("two-sum", "[0, 1]", "[0, 1] trailing")
    assert _outputs_match("valid-parentheses", "true\n", "true")


def test_optional_interview_session_must_belong_to_user(monkeypatch):
    configure_provider(monkeypatch)
    owner_headers, owner_id = register_user()
    attacker_headers, _ = register_user()
    with SessionLocal() as db:
        session = InterviewSession(user_id=owner_id)
        db.add(session)
        db.commit()
        session_id = session.id

    response = client.post("/api/v1/coding/execute", json={
        "problem_id": "two-sum", "language": "python", "code": "print(1)",
        "session_id": session_id,
    }, headers=attacker_headers)
    assert response.status_code == 403


def test_provider_failure_is_unavailable_and_never_falls_back(monkeypatch):
    configure_provider(monkeypatch)
    headers, _ = register_user()

    async def fail_provider(self, language, source_code, stdin=""):
        raise ExecutionProviderError("provider details must not leak")

    monkeypatch.setattr(Judge0Adapter, "execute", fail_provider)
    response = client.post("/api/v1/coding/execute", json={
        "problem_id": "two-sum", "language": "python", "code": "print(1)",
    }, headers=headers)
    assert response.status_code == 503
    assert "provider details" not in response.text


def test_execution_deadline_is_enforced(monkeypatch):
    import asyncio

    configure_provider(monkeypatch)
    monkeypatch.setattr(settings, "CODE_REQUEST_TIMEOUT_SECONDS", 0.001)
    headers, _ = register_user()

    async def slow_provider(self, language, source_code, stdin=""):
        await asyncio.sleep(0.02)
        return {"stdout": "", "stderr": "", "compile_output": "", "time_ms": 1, "memory_kb": 1, "status_desc": "Accepted"}

    monkeypatch.setattr(Judge0Adapter, "execute", slow_provider)
    response = client.post("/api/v1/coding/execute", json={
        "problem_id": "two-sum", "language": "python", "code": "print(1)",
    }, headers=headers)
    assert response.status_code == 503
    assert "timed out" in response.json()["detail"]


def test_output_limit_is_reported(monkeypatch):
    configure_provider(monkeypatch)
    headers, _ = register_user()

    async def oversized_output(self, language, source_code, stdin=""):
        return {
            "stdout": "x" * (16 * 1024 + 1), "stderr": "", "compile_output": "",
            "time_ms": 1, "memory_kb": 1000, "status_desc": "Accepted",
        }

    monkeypatch.setattr(Judge0Adapter, "execute", oversized_output)
    response = client.post("/api/v1/coding/execute", json={
        "problem_id": "two-sum", "language": "python", "code": "print(1)",
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "Output Limit Exceeded"
    assert response.json()["test_results"][0]["actual_output"] == "[Output limit exceeded]"


def test_test_case_count_limit(monkeypatch):
    configure_provider(monkeypatch)
    monkeypatch.setattr(settings, "CODE_MAX_TEST_CASES", 2)
    headers, _ = register_user()
    response = client.post("/api/v1/coding/execute", json={
        "problem_id": "two-sum", "language": "python", "code": "print(1)",
    }, headers=headers)
    assert response.status_code == 422


def test_concurrency_limit_returns_bounded_overload_response(monkeypatch):
    configure_provider(monkeypatch)
    headers, _ = register_user()
    acquired = 0
    while _EXECUTION_SLOTS.acquire(blocking=False):
        acquired += 1
    assert acquired > 0
    try:
        response = client.post("/api/v1/coding/execute", json={
            "problem_id": "two-sum", "language": "python", "code": "print(1)",
        }, headers=headers)
        assert response.status_code == 429
    finally:
        for _ in range(acquired):
            _EXECUTION_SLOTS.release()
