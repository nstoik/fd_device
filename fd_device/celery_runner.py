"""Main celery module."""
from celery import Celery

app = Celery()

app.config_from_object("fd_device.settings:CeleryConfig")
