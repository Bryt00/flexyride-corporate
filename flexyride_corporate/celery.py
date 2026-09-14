"""
Celery configuration for FlexyRide Corporate.
Defines Celery app instance, loads Django settings, and enables auto-discovery of tasks.
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexyride_corporate.settings')

app = Celery('flexyride_corporate')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'FlexyRide Celery Task: {self.request!r}')
