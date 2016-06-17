from django.apps import AppConfig
from django.db.models.signals import post_migrate


class PgMemento(AppConfig):
    name = 'pg_memento'
    verbose_name = "pgMemento"
