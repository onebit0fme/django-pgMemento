from django.db import models
import django.apps
from django.core.exceptions import FieldDoesNotExist
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


class NonManagedTable(Exception):
    pass


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

    _subject_model = None

    @property
    def subject_model(self):
        if self._subject_model is None:
            all_models = django.apps.apps.get_models(include_auto_created=True)

            # find the model with corresponding db_table
            db_table = self.event.table_relid.table_name
            m = None
            for model in all_models:
                if model._meta.db_table == db_table:
                    m = model
                    break
            if m is None:
                # TODO: Handle this case
                raise NonManagedTable("Irreversible: The table is not managed by any installed app")
            add_audit_id(m)
            self._subject_model = m

        return self._subject_model

    @property
    def field_mapping(self):
        model = self.subject_model
        # TODO: Test mapping under various circumstances (ex. custom db_column, foreign_key, etc.)
        return dict([(getattr(f, 'column', None) or getattr(f, 'attname', None) or f.name, getattr(f, 'attname', None) or f.name) for f in model._meta.get_fields()])

    @property
    def subject(self):
        model = self.subject_model
        add_audit_id(model)
        try:
            obj = model.objects.get(audit_id=self.audit_id)
            return obj
        except model.DoesNotExist:
            pass

    def subject_update(self, obj):
        mapping = self.field_mapping
        changes = self.changes
        if isinstance(changes, dict):
            for col, value in changes.items():
                if col in mapping:
                    setattr(obj, mapping.get(col), value)
            obj.save()

    def revert(self):

        # handle restoring
        event = self.event
        if event.op_id == 1:  # INSERT
            subject = self.subject
            if subject is not None:
                subject.delete()
        elif event.op_id == 2:  # UPDATE
            subject = self.subject
            if subject is not None:
                self.subject_update(subject)
        elif event.op_id == 3:  # DELETE
            mapping = self.field_mapping
            changes = self.changes
            model = self.subject_model

            subject = self.subject
            if subject is not None:
                self.subject_update(subject)
            else:
                kwargs = {}
                for col, value in changes.items():
                    if col in mapping:
                        kwargs[mapping[col]] = value
                subject = model(**kwargs)
                subject.save()


def add_audit_id(sender, **kwargs):
    try:
        sender._meta.get_field('audit_id')
    except FieldDoesNotExist:
        field = models.BigIntegerField(null=True, blank=True)
        field.contribute_to_class(sender, 'audit_id')
