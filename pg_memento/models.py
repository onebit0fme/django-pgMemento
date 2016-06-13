from django.db import models
from django.contrib.postgres.fields import FloatRangeField, JSONField


class ReadOnlyModel(models.Model):

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        return

    def delete(self, *args, **kwargs):
        return


class AuditTableLog(ReadOnlyModel):

    relid = models.IntegerField(primary_key=True)
    schema_name = models.TextField()
    table_name = models.TextField()
    txid_range = FloatRangeField()

    class Meta:
        managed = False
        db_table = 'audit_table_log'
        app_label = 'pg_memento'

    def __str__(self):
        return str(self.table_name)


class AuditColumnLog(ReadOnlyModel):

    table_relid = models.ForeignKey('AuditTableLog', db_column='table_relid')
    column_name = models.TextField()
    ordinal_position = models.IntegerField()
    column_default = models.TextField()
    is_nullable = models.CharField(max_length=3)
    data_type = models.TextField()
    data_type_name = models.TextField()
    char_max_length = models.IntegerField()
    numeric_precision = models.IntegerField()
    numeric_precision_radix = models.IntegerField()
    numeric_scale = models.IntegerField()
    datetime_precision = models.IntegerField()
    interval_type = models.TextField()
    txid_range = FloatRangeField()

    class Meta:
        managed = False
        db_table = 'audit_column_log'
        app_label = 'pg_memento'

    def __str__(self):
        return str(self.id)


class SerialField(models.BigIntegerField):

    def db_type(self, connection):
        return 'serial'


class TransactionLog(ReadOnlyModel):
    id = SerialField(primary_key=True, editable=False)
    txid = models.IntegerField()
    stmt_date = models.DateTimeField()
    user_name = models.TextField(null=True)
    client_name = models.TextField(null=True)

    class Meta:
        managed = False
        db_table = 'transaction_log'
        app_label = 'pg_memento'

    def __str__(self):
        return str(self.id)


class TableEventLog(ReadOnlyModel):

    # TODO: transaction ForeignKey does not work in Django, possibly due to field type inconsistency
    transaction = models.ForeignKey(TransactionLog, db_column='transaction_id', to_field='id')
    op_id = models.SmallIntegerField()
    table_operation = models.CharField(max_length=8, null=True)
    table_relid = models.ForeignKey(AuditTableLog, db_column='table_relid')

    class Meta:
        managed = False
        db_table = 'table_event_log'
        app_label = 'pg_memento'

    def __str__(self):
        return str(self.id)


class RowLog(ReadOnlyModel):

    id = models.BigIntegerField(primary_key=True)
    event = models.ForeignKey(TableEventLog, to_field='id')
    audit_id = models.IntegerField()
    changes = JSONField()

    class Meta:
        managed = False
        db_table = 'row_log'
        app_label = 'pg_memento'

    def __str__(self):
        return str(self.id)


def add_audit_id(sender, **kwargs):
    # if sender.__name__ == 'User':
    field = models.BigIntegerField(null=True, editable=False)
    field.contribute_to_class(sender, 'audit_id')

# from django.db.models.signals import class_prepared
#
# class_prepared.connect(add_audit_id)
