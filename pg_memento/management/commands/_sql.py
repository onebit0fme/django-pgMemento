from django.db import connection


INIT_PG_MOMENTO = """
-- 'Create event trigger to log schema changes ...'
SELECT pgmemento.create_schema_event_trigger(0);

-- 'Creating triggers for tables in ':schema_name' schema ...'
SELECT pgmemento.create_schema_log_trigger('public', string_to_array('%s',','));

-- 'Creating audit_id columns for tables in ':schema_name' schema ...'
SELECT pgmemento.create_schema_audit_id('public', string_to_array('%s',','));
"""


DROP_SCHEMA_LOG_IGNORE = """
SELECT pgmemento.drop_schema_log_trigger('public', string_to_array('%s',','));
"""

DROP_SCHEMA_LOG = """
SELECT pgmemento.drop_schema_log_trigger('public');
"""


def init(ignore_tables):
    cursor = connection.cursor()

    cursor.execute(INIT_PG_MOMENTO % (','.join(ignore_tables), ','.join(ignore_tables)))


def uninit(ignore_tables=None):
    cursor = connection.cursor()

    if ignore_tables is None:
        cursor.execute(DROP_SCHEMA_LOG)
    else:
        cursor.execute(DROP_SCHEMA_LOG_IGNORE % (','.join(ignore_tables),))
