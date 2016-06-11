# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from django.db import migrations
from pg_memento.compat import PG_MEMENTO_PATH, read_file_content

from django.conf import settings

db_to_log = settings.DATABASES.get('default')
# TODO: allow multiple databases
assert db_to_log is not None, "missing 'default' database!"
db_name = db_to_log.get('NAME')

PG_MOMENTO_PATH = os.path.join(PG_MEMENTO_PATH, 'pgMemento')

SETUP = 'src/SETUP.sql'
LOG_UTILS = 'src/LOG_UTIL.sql'
DDL_LOG = 'src/DDL_LOG.sql'
VERSIONING = 'src/VERSIONING.sql'
REVERT = 'src/REVERT.sql'
SCHEMA_MANAGEMENT = 'src/SCHEMA_MANAGEMENT.sql'

FINISH_INSTALL = """
-- Introducing pgMemento to search path...

ALTER DATABASE %s SET search_path TO "$user", public, pgmemento;

-- pgMemento setup completed!
"""


INSTALL_PG_MEMENTO = [
    read_file_content(os.path.join(PG_MOMENTO_PATH, SETUP)),
    read_file_content(os.path.join(PG_MOMENTO_PATH, LOG_UTILS)),
    read_file_content(os.path.join(PG_MOMENTO_PATH, DDL_LOG)),
    read_file_content(os.path.join(PG_MOMENTO_PATH, VERSIONING)),
    read_file_content(os.path.join(PG_MOMENTO_PATH, REVERT)),
    read_file_content(os.path.join(PG_MOMENTO_PATH, SCHEMA_MANAGEMENT)),
    [FINISH_INSTALL, [db_name]]
]

UNINSTALL_PG_MEMENTO = """
-- UNINSTALL_PGMEMENTO.sql

SELECT pgmemento.drop_schema_event_trigger();
SELECT pgmemento.drop_table_audit(tablename, schemaname) FROM pgmemento.audit_tables;

DROP SCHEMA pgmemento CASCADE;

ALTER DATABASE %s SET search_path TO "$user", public;
"""


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=INSTALL_PG_MEMENTO,
            reverse_sql=[[UNINSTALL_PG_MEMENTO, [db_name]]])
    ]
