"""Celery background tasks for payments application."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)
