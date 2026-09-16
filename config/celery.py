"""
Celery configuration for FlexyRide Corporate.
Defines Celery app instance, loads Django settings, and enables auto-discovery of tasks.
"""

import os
import sys
from pathlib import Path
from celery import Celery

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'FlexyRide Celery Task: {self.request!r}')
