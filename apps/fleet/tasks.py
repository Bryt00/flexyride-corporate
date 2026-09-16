"""Celery background tasks for fleet application."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)
