from __future__ import unicode_literals
from django.test import TestCase
from pg_memento.models import RowLog
from test_app.models import TestModel


class LoggingTests(TestCase):

    def test_testrunner(self):
        self.assertEqual(RowLog.objects.all().count(), 0)
        TestModel.objects.create(name='Test name', is_good=True)
        self.assertGreater(RowLog.objects.all().count(), 0)
