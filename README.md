<div align="center">

# 🪙 KharchaSaathi

### WhatsApp Group Expense Settler

<p align="center">
Manage and settle your group expenses directly from WhatsApp using Agentic AI Planning, Natural Language and OCR.
</p>

<p align="center">

[![Live Demo](https://img.shields.io/badge/Render-Live_Production-brightgreen?style=for-the-badge&logo=render)](https://kharchasaathi.onrender.com)
![Agentic AI](https://img.shields.io/badge/Agentic_AI-Smart_AI_Agents-purple?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Production-green?style=for-the-badge&logo=fastapi)
![Redis](https://img.shields.io/badge/Redis-Cache%20-red?style=for-the-badge&logo=redis)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Business_API-25D366?style=for-the-badge&logo=whatsapp)

</p>

### 🔗 Live Production API URL
`https://kharchasaathi.onrender.com`

---

### 📱 Settle Group Bills on WhatsApp. Skip the Bill-Splitting Apps.

No more downloading third-party splitwise-like apps, creating accounts, or manually adding friends.

KharchaSaathi turns WhatsApp into an **AI Expense-Settling Assistant** capable of understanding natural language, tracking multi-person group budgets, processing receipt images via OCR, and resolving debts with deterministic mathematical optimization.

</div>

## 🌟 Why KharchaSaathi?

Managing shared expenses shouldn't mean endless calculations, forgotten bills, or confusion over who owes whom.

Traditional group expense tracking is tedious and prone to friction. Friends often forget to enter bills or get confused by complex split calculations.

KharchaSaathi removes this friction using **Smart AI Agent Workflows**. Any member of the group simply messages the WhatsApp bot:

```text
Rahul paid 1200 for movie tickets, split equally between Rahul, Anjali, and Tina

Maine 500 kharch kiya dinner pe, add my share and Rahul's share

Show current group balances

Optimize debts and show settlement report
```

KharchaSaathi interprets expense messages, identifies participants and split details, validates the information, and records expenses in PostgreSQL. It then returns clear expense summaries and settlement information directly through WhatsApp.

# ✨ Core Features

## 💬 Natural Language Expense Parsing
- Deciphers conversational Hindi, English, and Hinglish split commands seamlessly.
- Handles default splits, equal division, or specific weights per participant.

## 📒 Derived Debt Cache & Event Hooking
- Maintains a dedicated, derived `DEBTS` table that automatically updates after every expense write.
- Prevents database state drifts through robust event-driven triggers.

## 🤖 Smart AI Agent Pipeline
- Utilizes structured LLM agents to reason through multi-step commands.
- Features custom classification, disambiguation, and user refinement steps.

## 📸 Multimodal OCR Receipt Scanning
- Analyzes food bills, cab receipts, or ticket images using Vision LLMs to extract itemized splits.

## ⚖ Deterministic Debt Optimization (Greedy Max-Flow)
- Employs a strictly **deterministic** mathematical engine to minimize the total number of transactions required to settle up the group.
- **Zero LLM dependency** for core mathematical debt reduction.
- Automatically aggregates overdue debts, monitors group inactivity, and sends daily/weekly outstanding reports.

---

# 🏗 High Level Architecture

```mermaid
flowchart LR

A[Group Member] --> B[WhatsApp]
B --> C[Meta Cloud API]
C --> D[FastAPI Backend]
D --> E[Smart AI Agent Pipeline]
E --> F[Business Services]
F --> G[(PostgreSQL)]
F --> H[(Redis Cache & Lock)]
F --> I[Groq Response Refiner]
I --> J[WhatsApp Response]
J --> A
```

---

# 🏛 Production Architecture

```mermaid
flowchart TD

A[User/Group] --> B[WhatsApp Webhook]
B --> C[FastAPI Main App]
C --> D[Redis Deduplicator & State Manager]
D --> E[Smart AI Agent Pipeline]
E --> F[Refiner Agent]
E --> G[Planner Agent]
E --> H[Insight Agent]
F & G & H --> I[Deterministic Debt Optimizer]
I --> J[(PostgreSQL)]
```

---
# 🧩 Agentic Request Lifecycle

```mermaid
sequenceDiagram

participant U as User
participant W as WhatsApp
participant API as FastAPI
participant P as Smart AI Agent
participant S as Service Layer
participant DB as PostgreSQL
participant R as Redis
participant F as Response Refiner

U->>W: Send Message / Voice Note / Bill Photo
W->>API: Webhook Payload
API->>R: Deduplicate Message ID
API->>P: Run Agent Pipeline
P->>S: Process Receipt / Transcribe Audio (Whisper)
P->>S: Trigger Expense & Split Tool
S->>DB: Write Expense / Recalculate derived Debts
DB-->>S: Success
S->>F: Structured Output
F-->>API: Friendly Response
API-->>W: WhatsApp Cloud API Send
W-->>U: Formatted Summary Message
```

---
# 📸 Screenshots & Live Deployment

## 1. WhatsApp Conversation Assistant
![WhatsApp Conversation](docs/images/01-whatsapp-chat.png)

---

## 2. Live Render Cloud Production Deployment
![Render Production Live Deployment](docs/images/02-render-live.png)

---

# ⚙ Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic, Celery
- **AI Providers**: Groq LLaMA 3.1 & Vision LLMs (NLP & Receipt Processing), Groq Whisper (Voice to Text)
- **Database & Cache**: PostgreSQL 16 (Permanent State), Redis (Deduplication, Lock, Queue)
- **Deployment**: Docker, Docker Compose, Render Cloud Platform

---

# 📂 Project Structure

```text
KharchaSaathi
├── app
│   ├── agents          # Smart AI Agents (Refiner, NLP Parser, Proactive Insights)
│   ├── algorithms      # Pure deterministic debt optimizer math
│   ├── api             # FastAPI Webhook & REST Endpoints
│   ├── core            # Settings, Logging & Database Config
│   ├── db              # SQLAlchemy Models & Migrations
│   ├── memory          # Redis
│   ├── services        # WhatsApp Cloud API, Vision LLMs
│   └── tools           # Expense tracking, reports, settlements
├── scheduler           # Worker tasks
├── tests               # Automated Pytest Suite
├── render.yaml         # Render Blueprint Specification
└── README.md
```

---
