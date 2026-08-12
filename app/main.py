from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from app.api.webhook import router as webhook_router
from app.db.session import engine, Base
from app.core.logging import setup_logging

# Configure structured logging handlers
setup_logging()

# For local SQLite/development ease, auto-create tables on startup
if engine.url.drivername == "sqlite" or "sqlite" in str(engine.url):
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="KharchaSaathi API",
    description="Agentic WhatsApp Expense-Settler for Groups",
    version="0.1.0"
)

app.include_router(webhook_router)

@app.get("/health")
async def health_check():
    """
    Health check endpoint returning 200 OK.
    """
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "service": "KharchaSaathi"}
    )

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    template_path = BASE_DIR / "templates" / "index.html"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Landing page template not found</h1>", status_code=404)

