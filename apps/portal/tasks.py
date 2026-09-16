"""Celery background tasks for portal application."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)
