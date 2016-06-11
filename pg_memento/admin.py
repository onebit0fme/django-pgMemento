from django.contrib import admin
from .models import AuditColumnLog, AuditTableLog, TransactionLog, TableEventLog, RowLog


@admin.register(AuditTableLog)
class RowLogAdmin(admin.ModelAdmin):

    list_display = ('__str__', 'table_name')


@admin.register(AuditColumnLog)
class RowLogAdmin(admin.ModelAdmin):
    pass


@admin.register(TransactionLog)
class RowLogAdmin(admin.ModelAdmin):
    pass


@admin.register(TableEventLog)
class RowLogAdmin(admin.ModelAdmin):
    pass


@admin.register(RowLog)
class RowLogAdmin(admin.ModelAdmin):

    list_display = ('__str__', 'get_table_operation', 'get_table_name', 'changes')
    list_filter = ('event__table_operation', 'event__table_relid__table_name')

    def get_table_operation(self, obj):
        return obj.event.table_operation
    get_table_operation.short_description = 'Operation'

    def get_table_name(self, obj):
        return obj.event.table_relid.table_name
