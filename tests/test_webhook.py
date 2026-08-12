import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

from app.api.webhook import VERIFY_TOKEN

def test_webhook_verification_success():
    """
    Ensure webhook GET verification succeeds with the correct verify token.
    """
    response = client.get(f"/webhook?hub.mode=subscribe&hub.challenge=ch123&hub.verify_token={VERIFY_TOKEN}")
    assert response.status_code == 200
    assert response.text == "ch123"

def test_webhook_verification_failure():
    """
    Ensure webhook GET verification fails with 403 with incorrect verify token.
    """
    response = client.get("/webhook?hub.mode=subscribe&hub.challenge=ch123&hub.verify_token=wrong_token")
    assert response.status_code == 403
    assert response.json() == {"detail": "Verification token mismatch"}

@patch("app.api.webhook.is_duplicate_message")
def test_webhook_post_message_ack(mock_dup):
    """
    Ensure webhook POST acks immediately with 200 OK and registers background task.
    """
    mock_dup.return_value = False
    
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "wamid.HBgMOTE5ODA0NTY3ODkwFQIAERgSQjU5NkQwMEE2OUQ4OTkyOUEyAA==",
                        "from": "1111111111",
                        "type": "text",
                        "text": {"body": "Alice spent 900 on Dinner"}
                    }]
                }
            }]
        }]
    }
    
    # We pass verification since META_APP_SECRET is not configured by default in test env
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}
    mock_dup.assert_called_once()

@patch("app.api.webhook.is_duplicate_message")
def test_webhook_post_duplicate_ignored(mock_dup):
    """
    Ensure duplicate webhook payloads are successfully deduplicated and ignored.
    """
    mock_dup.return_value = True
    
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "wamid.dup_message_123",
                        "from": "1111111111",
                        "type": "text",
                        "text": {"body": "Alice spent 900 on Dinner"}
                    }]
                }
            }]
        }]
    }
    
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "duplicate_ignored"}
    mock_dup.assert_called_once_with("wamid.dup_message_123")
