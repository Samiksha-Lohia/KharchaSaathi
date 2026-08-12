# KharchaSaathi — Antigravity Prompt Playbook

A copy-paste prompt for every step of the roadmap, engineered to keep both Antigravity's agent context and your own Claude usage lean. Read the **Token Economy Rules** once, then work phase by phase.

---

## Token Economy Rules (why these prompts are shaped this way)

1. **Seed a knowledge file once, reference it forever.** Phase 0 creates `.antigravity/knowledge/project.md`. Every later prompt says "per project.md" instead of re-pasting your architecture. This is the single biggest token saver — you're not re-explaining the debt-optimizer-must-be-deterministic rule 15 times across the project.
2. **One agent task = one bounded slice of the repo.** Never say "build phase 2." Say "build the webhook + dedup layer, touch only these 3 files." Bounded tasks produce small diffs, which are cheap to review and cheap to regenerate if wrong.
3. **State the "do not touch" list.** This is the #1 cause of runaway diffs and wasted tokens — an agent "helpfully" refactoring a file you didn't ask about, which then needs a whole second pass to review and revert.
4. **TDD only where it earns its cost.** Full test-first is asked for only in Phase 1 (money math) and Phase 2 (idempotency) — the two places a silent bug costs real money or real duplicate writes. Elsewhere, tests are requested after the implementation, scoped to the new files only.
5. **Ask for a plan before code, on anything non-trivial.** Every "build X" prompt below ends with "list the files you'll create/edit and wait for my go-ahead before writing code." A 10-line plan review is far cheaper than reviewing then rejecting a 400-line diff.
6. **Batch parallel agents by skill-profile, not by phase-order.** Where the roadmap calls out parallelizable work (Phase 1 schema vs. algorithm; Phase 2 webhook vs. planner), launch both as separate Agent Manager tasks in the same sitting so you review two small diffs back-to-back instead of one large one.

Set **Workspace Mode = Review-driven** for Phase 0, 1, and anything touching production config in Phase 5. Switch to **Agent-Driven** for well-bounded subtasks from Phase 2 onward once the architecture is proven out.

---

## Phase 0 — Environment Setup & Repo Scaffolding

### Prompt 0.1 — Seed project knowledge (run this FIRST, before anything else)
```
Create a file at .antigravity/knowledge/project.md summarizing this project's
non-negotiable architecture rules, so I can reference this file instead of
re-explaining these in every future prompt:

- Project: KharchaSaathi, an agentic WhatsApp expense-settler for groups.
- Stack: FastAPI, PostgreSQL(Supabase), Redis(Upstash), LangGraph agent pipeline, Celery for
  scheduling, Meta WhatsApp Cloud API, Groq/OpenRouter LLMs, Whisper for voice.
- HARD RULE: the Debt Optimization Agent (app/algorithms/debt_optimizer.py) is
  pure deterministic code. It NEVER calls an LLM, ever, under any refactor.
- HARD RULE: all money is stored and computed as integer paise. Never float
  rupees, never Numeric columns for money fields.
- HARD RULE: DEBTS is a derived/cached table, recomputed via event-driven hook
  after any expense/settlement write — never a primary write target.
- HARD RULE: any agent task must stay scoped to the files it's explicitly
  asked to touch. No unrequested refactors of unrelated modules.
- Do not write any implementation code yet. Just create this knowledge file.
```

### Prompt 0.2 — Scaffold skeleton only
```
Per .antigravity/knowledge/project.md. Scaffold an empty project skeleton
only — docstring stubs, no logic, no implementation:

app/agents/, app/algorithms/, app/api/, app/db/, app/memory/, app/services/,
app/tools/, scheduler/, tests/, alembic/

Also create: README.md, .gitignore (Python), a docker-compose.yml with
FastAPI (empty health-check app), PostgreSQL, and Redis services, and a
.env.example listing (not filling): POSTGRES_URL, REDIS_URL,
META_WHATSAPP_TOKEN, META_PHONE_NUMBER_ID, GROQ_API_KEY, WHISPER_API_KEY.

Do not implement any endpoint logic beyond a single GET /health returning 200.
List the files you'll create, then proceed — this task is small enough to
run in one pass.
```

### Manual steps (no agent needed — save your tokens)
- Register the GitHub repo, connect it in Antigravity.
- Register Meta Developer app + WhatsApp test number, generate temp token — do this by hand in the Meta dashboard, not via agent.
- Fill in the real `.env` values yourself locally.
- Run `docker-compose up` and confirm `/health` returns 200 manually — this doesn't need an agent verification pass.

---

## Phase 1 — Core Ledger (No AI Yet)

Run these as **two separate, parallel Agent Manager tasks** — they touch different files.

### Prompt 1.1 — Schema + CRUD agent
```
Per .antigravity/knowledge/project.md. Scope: app/db/models/, app/db/crud/,
alembic/ only. Do not touch app/algorithms/ or anything else.

Implement the SQLAlchemy models for: USERS, GROUPS, GROUP_MEMBERS, EXPENSES,
EXPENSE_SPLITS, SETTLEMENTS, DEBTS, INSIGHTS, REMINDERS. [Paste your ER
diagram or field list here if not already in project.md.] DEBTS is a derived
cache table, not a primary write target — do not add public create/update
CRUD for it directly; it gets a dedicated recompute function instead.

Generate the first Alembic migration. Implement plain CRUD functions (no
agent framework, no LLM) for expenses, splits, and settlements.

All money columns must be Integer (paise), never Float or Numeric — this is
a hard rule, not a preference.

List the files you'll create/edit and wait for my go-ahead before writing code.
```

### Prompt 1.2 — Debt optimizer agent (strict TDD)
```
Per .antigravity/knowledge/project.md. Scope: app/algorithms/debt_optimizer.py
and tests/test_debt_optimizer.py only. This module must be pure deterministic
Python — zero LLM calls, zero network calls.

Write the test file FIRST, before any implementation, covering exactly these
cases: (1) simple 2-person split, (2) a 4-person example [paste your plan's
example numbers here], (3) fully circular debt A→B→C→A, (4) a partial
settlement mid-cycle, (5) a rounding-edge case with odd paise split across 3
people. Show me the test file and wait for my approval before implementing
the algorithm against it.

Once approved: implement the greedy min-cash-flow algorithm — net balance per
user, max-heap of creditors, max-heap of debtors, greedily match largest
creditor with largest debtor until balances zero. All amounts in integer paise.
```

### Prompt 1.3 — Recompute hook + reconciliation check (small follow-up, run after 1.1/1.2 merge)
```
Per .antigravity/knowledge/project.md. Scope: app/db/crud/ (add hook only)
and a new tests/test_debts_reconciliation.py. Do not modify debt_optimizer.py.

Add an event-driven hook: after any expense or settlement CRUD write,
recompute and upsert the affected rows in DEBTS using debt_optimizer.py's
output — not a scheduled job, triggered on write.

Add one reconciliation test: recompute DEBTS from scratch from
EXPENSE_SPLITS + SETTLEMENTS and diff it against the cached table for a
seeded multi-user scenario.
```

---

## Phase 2 — WhatsApp Webhook + Agent Pipeline (Text Only)

Two parallel tracks: plumbing vs. NLP. Launch as separate tasks.

### Prompt 2.1 — Webhook + idempotency agent (distributed-systems track)
```
Per .antigravity/knowledge/project.md. Scope: app/api/webhook.py,
app/services/redis_service.py (or equivalent), tests/test_webhook.py only.
Do not touch app/agents/ or app/tools/.

Implement:
1. webhook.py — Meta signature verification, event parsing, and an
   IMMEDIATE 200 ack. Heavy processing must be pushed to a background task
   after the ack, not before (Meta expects fast acks).
2. Dedup: msg_dedup:{whatsapp_msg_id} in Redis, 24h TTL, checked before any
   processing.
3. session_lock:{group_id}, 30s TTL, wrapped around expense writes to
   prevent race conditions from near-simultaneous group messages.

Write tests confirming: resending the same webhook payload twice does not
trigger duplicate processing, and two near-simultaneous writes to the same
group don't corrupt state.

List files first, wait for my go-ahead, then implement.
```

### Prompt 2.2 — Planner + Intent + Entity agents (NLP track)
```
Per .antigravity/knowledge/project.md. Scope: app/agents/ (LangGraph planner,
intent agent, entity resolution agent, response refiner) and
app/tools/{add_expense,settle,query_balance,undo}_tool.py. Do not touch
app/api/webhook.py.

Build a LangGraph pipeline: Planner → Intent Agent (classify into
add_expense | settle_up | query_balance | undo | set_reminder) → Entity
Resolution Agent (fuzzy-match member names against GROUP_MEMBERS, extract
amounts, flag ambiguity when names collide) → the four tool functions
(wired to Phase 1 CRUD + optimizer) → Response Refiner Agent (turns
structured tool output into a natural WhatsApp reply).

Implement pending_confirm:{user_id} in Redis (5 min TTL) for the YES/NO
disambiguation loop when entity resolution is ambiguous.

Before writing the agent code, draft the Intent Agent's system prompt and
test it against this hand-written Hinglish message set: [paste 5-10 example
messages from your plan, e.g. "maine 800 kharch kiya trip mein, Rahul aur
mujhe split kar do"]. Show me classification results before wiring it into
the full pipeline — I want to catch misclassification early, cheaply.
```

### Prompt 2.3 — Regression test set (run once 2.1 + 2.2 both merge)
```
Per .antigravity/knowledge/project.md. Scope: tests/test_e2e_text_flow.py
only, plus a new tests/fixtures/hinglish_messages.json with 30-50 labeled
real-style Hinglish/English messages and their expected intent. Do not
modify agent or webhook code — this task is test-authoring only. Flag any
existing misclassifications you find rather than silently patching the
intent prompt yourself.
```

---

## Phase 3 — Multimodal Input: OCR + Voice

Keep this fully separate from Phase 2 files — explicitly say so, since this is where agents most often "helpfully" touch the webhook.

### Prompt 3.1 — Voice pipeline
```
Per .antigravity/knowledge/project.md. Scope: app/services/whisper_service.py
only. Do not touch anything in app/agents/ or app/api/webhook.py beyond
adding the message-type branch described below.

Implement whisper_service.py: download WhatsApp voice note media, send to
Whisper API, return transcript text. Route the transcript into the existing
Intent Agent unchanged — do not build a parallel pipeline. Add a
Voice Note | Photo/Bill | Text branch at the router level before the shared
Intent Agent, touching only the minimum lines needed for that branch.

Cap accepted voice note length; return a clear WhatsApp error message (not
a silent failure) if exceeded.
```

### Prompt 3.2 — OCR pipeline (spot-check heavy — expect manual review)
```
Per .antigravity/knowledge/project.md. Scope: app/services/ocr_service.py
only.

Implement ocr_service.py: download the bill image, send to a vision-capable
LLM with a strict structured-extraction JSON schema (line items, total,
currency). Validate extracted total against the sum of line items before
proceeding. If they mismatch, flag it rather than silently trusting either
number.

Add a mandatory confirmation step: show the user the extracted total via
WhatsApp and require an explicit YES before any DB write — reuse the
existing pending_confirm Redis pattern from Phase 2, don't build a new one.
Never allow a skip-confirm path for OCR-sourced expenses.

First show me the extraction JSON schema and prompt design only — I'll test
it against a handful of real bill photos before you wire it into the write
path.
```

---

## Phase 4 — Proactive Insight Agent + Scheduling

### Prompt 4.1 — Scheduler + pattern detection (deterministic part first)
```
Per .antigravity/knowledge/project.md. Scope: scheduler/, app/db/ (read-only
queries), docker-compose.yml (Celery worker + Beat addition) only.

Stand up Celery worker + Beat in docker-compose, Redis as broker. Implement
four scheduled tasks: check_overdue_settlements, weekly_spending_insight,
inactivity_check, month_end_settle_suggestion — each producing a plain
Python dict of computed numbers (late-settlement counts, category spend
deltas, days-since-activity). Do NOT call any LLM in this task — that's a
separate step. These four functions must be independently unit-testable
against a seeded DB with no network calls.
```

### Prompt 4.2 — Nudge phrasing agent (run after 4.1 merges)
```
Per .antigravity/knowledge/project.md. Scope: app/agents/insight_agent.py
only. This agent's ONLY job is phrasing — it receives already-computed
numbers from the Phase 4.1 scheduler functions and turns them into a
natural WhatsApp message. It must never compute the numbers itself.

Generate 3 tone variants per pattern type (caring-but-direct Hinglish, per
project voice) so I can pick one. Wire the chosen variant into
whatsapp_service.py for actual sending, respecting Meta's business-initiated
messaging window rules — flag explicitly if a given scheduled task would
need a pre-approved template because it falls outside an active 24h window.

Add per-user/group rate limiting: max 1 unsolicited nudge per few days, and
a mute mechanism.
```

---

## Phase 5 — Hardening, Deployment & Pilot

Keep Workspace Mode on **Review-driven** for this entire phase.

### Prompt 5.1 — Deployment config (review every line — production secrets involved)
```
Per .antigravity/knowledge/project.md. Scope: Dockerfile, production
docker-compose.yml or Render/Railway platform config, and env-var wiring
only. Do not touch application logic.

Finalize a production Dockerfile and deployment config for Render/Railway
with managed Postgres + Redis (or Upstash for Redis). List every environment
variable it expects, and show me the full diff before I apply it — this is
a review-every-line task, not an autonomous one.
```

### Prompt 5.2 — Logging + alerting (small, bounded)
```
Per .antigravity/knowledge/project.md. Scope: a new app/core/logging.py plus
minimal call-sites in the agent pipeline and webhook. Add structured logging
across the pipeline and one simple error-alerting hook (a WhatsApp/Slack
message to a single admin number on unhandled exceptions is sufficient at
this scale — no external monitoring service needed yet).
```

### Prompt 5.3 — End-to-end staging verification (use browser-in-the-loop here)
```
Per .antigravity/knowledge/project.md. Against the live staging URL, run
through these scenarios and report pass/fail as an Artifact:
add expense → query balance → settle → undo. Also verify: resent webhook
payload doesn't duplicate, ambiguous name triggers YES/NO clarification,
OCR confirm-before-write blocks on a NO reply. Report only — do not modify
any code as part of this task.
```

### Prompt 5.4 — Bug triage template (reuse per pilot bug report — keep each instance small)
```
Per .antigravity/knowledge/project.md. Here is a pilot user's confused/failed
WhatsApp interaction transcript: [paste transcript]. Diagnose the likely
root cause and propose a minimal, scoped fix as a reviewable diff. Do not
touch files unrelated to this specific bug.
```

---

## Phase 6 — Iterate & Scale (Post-Pilot)

### Prompt 6.1 — Evidence-based retro (no code — keep this cheap)
```
Per .antigravity/knowledge/project.md, and using the pilot logs at
[path/table], summarize: intent-classification accuracy, OCR accuracy,
undo rate, and nudge engagement rate. Update
.antigravity/knowledge/project.md with any recurring Hinglish phrasings
that broke intent classification, so future prompts inherit this data
automatically. Do not propose or write any code in this task — analysis
and knowledge-file update only.
```

### Prompt 6.2 — Next-increment scoping (only run after you've decided to continue)
```
Per .antigravity/knowledge/project.md and the retro findings just added to
it. Propose a single next increment scoped to the biggest evidenced friction
point (e.g., OCR accuracy) — not a feature wishlist. List files touched and
wait for my go-ahead before implementing.
```

---

## Quick Reference: What NOT to Send an Agent

- Never paste your entire roadmap or plan into a single prompt — that's the fastest way to burn context on both ends. Reference `project.md` instead.
- Never ask for a whole phase in one prompt once you're past Phase 0 — split by the sub-prompts above.
- Never let an agent "verify while it's at it" outside its stated scope — that's implicit permission to wander into unrelated files and balloon the diff.
- Never re-explain the paise/deterministic-optimizer rules inline — that's what `project.md` is for.
