from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ._sql import init, uninit

IGNORE_TABLES = ['reversion_revision',  # Don't see the need to log reversions in case it's installed
                 'reversion_version']


class Command(BaseCommand):
    help = 'Initialize pgMemento logging.'

    def handle(self, *args, **options):
        ignore_tables = getattr(settings, 'PG_MEMENTO_IGNORE_TABLES', IGNORE_TABLES)
        uninit()
        init(ignore_tables=ignore_tables)
        self.stdout.write(self.style.SUCCESS('Initialized!'))
