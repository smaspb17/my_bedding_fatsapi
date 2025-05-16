# tasks/celery.py
from celery import Celery

from app.core.config import settings

celery = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    include=["app.tasks.tasks"],
    backend=settings.REDIS_URL,
)

celery.conf.task_ignore_result = False
celery.conf.result_expires = 3600  # 1 час
