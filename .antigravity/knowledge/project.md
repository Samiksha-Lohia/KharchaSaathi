# KharchaSaathi — Project Knowledge Base & Rules

## Project Overview
KharchaSaathi is an agentic expense-settling assistant for WhatsApp groups. It parses expense statements, tracks splits, and computes group debt settlements using natural language interactions (text, voice, and receipt scans).

## Architecture Stack
- **API Framework**: FastAPI (Uvicorn as ASGI server)
- **Database**: PostgreSQL (SQLAlchemy ORM, Alembic migrations)
- **Caching & Message Queue**: Redis (Deduplication, locking, and celery backend)
- **Agent Pipeline**: LangGraph
- **Task Scheduler**: Celery + Celery Beat
- **External Integration**: Meta WhatsApp Cloud API
- **Language Models**: Groq / OpenRouter LLMs (Llama 3, etc.)
- **Voice Transcription**: Whisper (Groq/OpenAI endpoints)

## Non-Negotiable Rules (HARD RULES)

1. **Deterministic Debt Optimization**:
   - The optimization engine at `app/algorithms/debt_optimizer.py` is **strictly deterministic**.
   - It **NEVER** calls an LLM or makes external network calls under any circumstances or refactors.

2. **Integer Paise Storage**:
   - All monetary fields, balances, and computations must be represented and stored as **integer paise** (1 INR = 100 paise).
   - Never use floating point representations (`float`) or decimal type columns (`Numeric`/`Decimal`) for money.

3. **Derived Debts Table**:
   - `DEBTS` is a derived cache table. It is **never** a primary target for direct user writes or CRUD modifications.
   - It must be recomputed programmatically via event-driven hooks triggered immediately after any write to `EXPENSES`, `EXPENSE_SPLITS`, or `SETTLEMENTS`.

4. **Task Scoping Boundaries**:
   - Every agent task must be tightly scoped to the specific files requested.
   - Do **NOT** perform any unrequested refactorings, optimizations, or modifications of unrelated modules.
