from bff.schemas import ResolveRequest, ActionType
import uuid


def test_resolve_request_validation():
    # Valid payload
    payload = {
        "attribution_id": str(uuid.uuid4()),
        "action": ActionType.APPROVE,
        "actor_id": "user-1",
    }
    req = ResolveRequest(**payload)
    assert req.action == ActionType.APPROVE

    # Override without new_reason_code should still validate but new_reason_code is optional
    payload2 = {
        "attribution_id": str(uuid.uuid4()),
        "action": ActionType.OVERRIDE,
        "actor_id": "user-2",
    }
    req2 = ResolveRequest(**payload2)
    assert req2.action == ActionType.OVERRIDE
