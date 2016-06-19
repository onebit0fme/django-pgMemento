import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from django import db
from django.core.management import call_command
from django.test.runner import DiscoverRunner
from django.conf import settings

EXCLUDED_APPS = getattr(settings, 'TEST_EXCLUDE', [])

INIT_PG_MOMENTO = """
-- 'Create event trigger to log schema changes ...'
SELECT pgmemento.create_schema_event_trigger(0);

-- 'Creating triggers for tables in ':schema_name' schema ...'
SELECT pgmemento.create_schema_log_trigger('public', string_to_array('%s',','));

-- 'Creating audit_id columns for tables in ':schema_name' schema ...'
SELECT pgmemento.create_schema_audit_id('public', string_to_array('%s',','));
"""



def init(ignore_tables, connection):
    cursor = connection.cursor()

    cursor.execute(INIT_PG_MOMENTO % (','.join(ignore_tables), ','.join(ignore_tables)))


class CerebrumTestSuiteRunner(DiscoverRunner):

    def setup_databases(self, **kwargs):
        # self.keepdb = True
        # self.parallel = True
        r = super(CerebrumTestSuiteRunner, self).setup_databases(**kwargs)
        db.connection.close()
        db.connection.connect()
        call_command('initlogging')
        return r
