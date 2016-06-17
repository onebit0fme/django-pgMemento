from django.core.management.base import BaseCommand, CommandError
from ._sql import init, uninit


class Command(BaseCommand):
    help = 'Uninitialize pgMemento logging.'

    def handle(self, *args, **options):
        uninit()
        self.stdout.write(self.style.SUCCESS('Uninitialized!'))
