import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from app.db.session import Base
from app.db.crud import create_user, create_group, add_user_to_group
from app.agents.agent_pipeline import process_whatsapp_message
from app.core.logging import ADMIN_ALERTS

@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@patch("app.agents.agent_pipeline.parse_llm_intent")
def test_production_error_alerting(mock_intent, db_session):
    """
    Ensures that unhandled exceptions in the processing pipeline
    successfully dispatch alert notifications to the admin alert cache.
    """
    phone = "919999999990"
    alice = create_user(db_session, phone, "Alice")
    group = create_group(db_session, "Trip")
    add_user_to_group(db_session, group.id, alice.id, "admin")
    
    # 1. Clear existing alerts
    ADMIN_ALERTS.clear()
    
    # 2. Force parse_llm_intent to throw an unhandled critical exception
    mock_intent.side_effect = RuntimeError("Database connection lost during parsing")
    
    message_payload = {
        "id": "wamid.critical_crash_123",
        "from": phone,
        "type": "text",
        "text": {"body": "Alice spent 900"}
    }
    
    # 3. Execute message processing loop (should catch and alert, but not crash the process)
    process_whatsapp_message({}, phone, message_payload, db=db_session)
    
    # 4. Verify admin alert was successfully triggered
    assert len(ADMIN_ALERTS) == 1
    assert "Database connection lost during parsing" in ADMIN_ALERTS[0]
