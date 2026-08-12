import os
from celery import Celery
from celery.schedules import crontab

# Read Redis Broker URL from env
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "kharchasaathi_scheduler",
    broker=redis_url,
    backend=redis_url,
    include=["scheduler.tasks"]
)

# Configuration overrides
app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Celery Beat periodic schedule definitions
    beat_schedule={
        "check-overdue-settlements-daily": {
            "task": "scheduler.tasks.check_overdue_settlements_task",
            "schedule": crontab(hour="12", minute="0"),  # Daily at 12:00 PM UTC
        },
        "weekly-spending-insights-sunday": {
            "task": "scheduler.tasks.weekly_spending_insight_task",
            "schedule": crontab(day_of_week="0", hour="18", minute="0"),  # Sunday at 6:00 PM UTC
        },
        "inactivity-checks-daily": {
            "task": "scheduler.tasks.inactivity_check_task",
            "schedule": crontab(hour="10", minute="0"),  # Daily at 10:00 AM UTC
        },
        "month-end-settlements-monthly": {
            "task": "scheduler.tasks.month_end_settle_suggestion_task",
            "schedule": crontab(day_of_month="28", hour="9", minute="0"),  # 28th of every month
        }
    }
)
