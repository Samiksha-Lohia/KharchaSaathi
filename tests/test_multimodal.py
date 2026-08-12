import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.db.models import Expense
from app.db.crud import create_user, create_group, add_user_to_group
from app.services.whisper_service import transcribe_voice_note
from app.services.ocr_service import process_bill_image
from app.agents.agent_pipeline import process_whatsapp_message, get_pending_action, execute_parsed_intent, parse_fallback_intent

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

def test_whisper_size_limit():
    """
    Ensure voice transcription raises a size error for files larger than 2MB.
    """
    with pytest.raises(ValueError, match="Audio note exceeds maximum size limit of 2MB."):
        transcribe_voice_note("test_voice_note_large")

def test_ocr_totals_sum_validation():
    """
    Ensure OCR service checks that item price sum equals total, and flags mismatch.
    """
    # 1. Valid sum (600 + 300 = 900)
    valid_res = process_bill_image("test_bill_image")
    assert valid_res["success"] is True
    assert "validation_error" not in valid_res
    
    # 2. Invalid sum (600 + 300 = 900 != 1000)
    invalid_res = process_bill_image("test_bill_image_invalid")
    assert invalid_res["success"] is True
    assert "validation_error" in invalid_res
    assert "Sum of line items" in invalid_res["validation_error"]

def test_voice_note_pipeline_processing(db_session):
    """
    Ensures voice notes are transcribed and successfully parsed by NLP agents.
    """
    # Register user
    phone = "919999999999"
    alice = create_user(db_session, phone, "Alice")
    group = create_group(db_session, "Trip")
    add_user_to_group(db_session, group.id, alice.id, "admin")
    
    # Simulate receiving a voice note
    message_payload = {
        "id": "wamid.voice_test_123",
        "from": phone,
        "type": "voice",
        "voice": {"id": "test_voice_note", "mime_type": "audio/ogg"}
    }
    
    # Manually execute process function (normally run in FastAPI background task)
    # This should:
    # 1. Transcribe "test_voice_note" -> "Alice spent 900 on Dinner"
    # 2. Parse intent -> add_expense, 900, description "Dinner"
    # 3. Create expense -> split across members (Alice only, since she is the only member here)
    # Wait, let's see: she is the only member, so it split across Alice.
    process_whatsapp_message({}, phone, message_payload, db=db_session)
    
    # Check that the expense was added to db
    expenses = db_session.query(Expense).filter(Expense.group_id == group.id).all()
    assert len(expenses) == 1
    assert expenses[0].amount == 900
    assert expenses[0].description == "dinner"

def test_ocr_photo_confirmation_loop(db_session):
    """
    Ensures image receipts trigger confirmation check and require YES response.
    """
    phone = "919999999998"
    bob = create_user(db_session, phone, "Bob")
    group = create_group(db_session, "Trip")
    add_user_to_group(db_session, group.id, bob.id, "admin")
    
    # Simulate receiving an image
    message_payload = {
        "id": "wamid.image_test_123",
        "from": phone,
        "type": "image",
        "image": {"id": "test_bill_image", "mime_type": "image/jpeg"}
    }
    
    # Executing pipeline
    # This should:
    # 1. Process OCR -> 900 paise
    # 2. Set pending action `pending_confirm:bob.id`
    # 3. Stop before DB write.
    process_whatsapp_message({}, phone, message_payload, db=db_session)
    
    # Verify no expenses have been recorded in the database yet
    expenses = db_session.query(Expense).filter(Expense.group_id == group.id).all()
    assert len(expenses) == 0
    
    # Verify action cached in Redis confirm loop
    pending = get_pending_action(bob.id)
    assert pending is not None
    assert pending["action"] == "add_expense"
    assert pending["amount"] == 900
    
    # User confirms by sending "yes"
    parsed_confirm = parse_fallback_intent("yes")
    reply = execute_parsed_intent(db_session, group.id, bob.id, parsed_confirm)
    
    assert "recorded" in reply.lower()
    
    # Verify expense is now in database
    expenses2 = db_session.query(Expense).filter(Expense.group_id == group.id).all()
    assert len(expenses2) == 1
    assert expenses2[0].amount == 900
