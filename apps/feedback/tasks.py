"""Celery background tasks for feedback application."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)
