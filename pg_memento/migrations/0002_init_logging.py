# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


IGNORE_TABLES = ['reversion_revision',  # Don't see the need to log reversions in case it's installed
                 'reversion_version']

INIT_PG_MOMENTO = """
-- 'Create event trigger to log schema changes ...'
SELECT pgmemento.create_schema_event_trigger(0);

-- 'Creating triggers for tables in ':schema_name' schema ...'
SELECT pgmemento.create_schema_log_trigger('public', string_to_array('%s',','));

-- 'Creating audit_id columns for tables in ':schema_name' schema ...'
SELECT pgmemento.create_schema_audit_id('public', string_to_array('%s',','));
""" % (','.join(IGNORE_TABLES), ','.join(IGNORE_TABLES))


DROP_SCHEMA_LOG = """
SELECT pgmemento.drop_schema_log_trigger('public', string_to_array('%s',','));
""" % (','.join(IGNORE_TABLES), )


class Migration(migrations.Migration):

    dependencies = [
        ('pg_memento', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[INIT_PG_MOMENTO],
            reverse_sql=[DROP_SCHEMA_LOG])
    ]
