from functools import update_wrapper

from django.core.checks import messages
from django.core import urlresolvers
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, NoReverseMatch
from django.shortcuts import render, redirect
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from django.contrib.admin import ModelAdmin, TabularInline
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin import ListFilter
from django.contrib.contenttypes.models import ContentType

from .models import AuditColumnLog, AuditTableLog, TransactionLog, TableEventLog, RowLog, NonManagedTable, add_audit_id


class NoAdditionsMixin(object):

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super(NoAdditionsMixin, self).get_actions(request)
        del actions['delete_selected']
        return actions


@admin.register(AuditTableLog)
class AuditTalbeLogAdmin(NoAdditionsMixin, admin.ModelAdmin):

    list_display = ('__str__', 'table_name')


@admin.register(AuditColumnLog)
class AuditColumnLogAdmin(NoAdditionsMixin, admin.ModelAdmin):
    pass


class EventLogInline(TabularInline):
    model = TableEventLog
    extra = 0


@admin.register(TransactionLog)
class TransactionLogAdmin(NoAdditionsMixin, admin.ModelAdmin):
    inlines = [EventLogInline]
    readonly_fields = ('txid', 'stmt_date', 'user_name', 'client_name')


class RowLogInline(TabularInline):
    model = RowLog
    extra = 0


@admin.register(TableEventLog)
class TableEventLogAdmin(NoAdditionsMixin, admin.ModelAdmin):

    inlines = [RowLogInline]


class ObjectRowLogFilter(ListFilter):

    # TODO: custom template?
    template = 'filter_input.html'

    model_parameter = 'model'
    object_id_parameter = 'object_id'
    object_audit_id_parameter = 'object_audit_id'
    include_m2m_parameter = 'include_m2m'

    accepted_params = [model_parameter, object_id_parameter, object_audit_id_parameter, include_m2m_parameter]
    toggle_params = [include_m2m_parameter]

    choices_display = (
        (include_m2m_parameter, 'Include many-to-many'),
    )

    def __init__(self, request, params, model, model_admin):
        self.obj = None
        super(ObjectRowLogFilter, self).__init__(
            request, params, model, model_admin)
        for param in self.accepted_params:
            if param in params:
                self.used_parameters[param] = params.pop(param)
        self.obj = self.select_object()

        # set to be accessible in template
        model_admin._filter_subject = self.obj
        # ^ don't really like this approach, but I'll keep it for now, as private

    def select_object(self):
        model_name = self.used_parameters.get(self.model_parameter)
        object_id = self.used_parameters.get(self.object_id_parameter)
        object_audit_id = self.used_parameters.get(self.object_audit_id_parameter)
        if model_name and (object_id or object_audit_id):
            try:
                ct = ContentType.objects.get(model=model_name.lower())
                model = ct.model_class()
                add_audit_id(model)
                try:
                    kwargs = {'pk': object_id} if object_id else {'audit_id': object_audit_id}
                    obj = model.objects.get(**kwargs)
                    return obj
                except model.DoesNotExist:
                    pass
            except ContentType.DoesNotExist:
                pass

    @property
    def title(self):
        if self.obj is None:
            return 'Object not selected'
        return "Object: %s" % str(self.obj)

    def queryset(self, request, queryset):
        if self.obj is not None:
            return self.get_row_logs(queryset, self.obj)
        return queryset

    def has_output(self):
        return self.obj is not None

    def is_selected(self, param):
        return self.used_parameters.get(param, 'yes') == 'yes'

    def negate(self, param_value):
        return 'no' if param_value == 'yes' else 'yes'

    def choices(self, cl):
        yield {
            'selected': not self.has_output(),
            'query_string': cl.get_query_string({}, self.accepted_params),
            'display': _('All'),
        }
        for param, name in self.choices_display:
            yield {
                'selected': self.is_selected(param),
                'query_string': cl.get_query_string({
                    param: self.negate(self.used_parameters.get(param, 'yes')),
                }, []),
                'display': name,
            }

    def expected_parameters(self):
        return self.accepted_params

    def contribute_audit_id(self, model):
        if not hasattr(model, 'audit_id'):
            add_audit_id(model)

    def get_row_logs(self, queryset, obj):
        # TODO: not DRY
        model = type(obj)
        db_table = model._meta.db_table

        # Self audit
        self.contribute_audit_id(model)
        obj.refresh_from_db()
        row_log_set = queryset.filter(event__table_relid__table_name=db_table,
                                      audit_id=obj.audit_id)

        # m2m audit
        if self.used_parameters.get(self.include_m2m_parameter, 'yes') == 'yes':
            for m2m_field in model._meta.many_to_many:
                # TODO: `assumed_column_name` this might require refactoring
                assumed_column_name = m2m_field.remote_field.related_query_name or m2m_field.remote_field.name + '_id'
                through_model = getattr(model, m2m_field.name).through
                self.contribute_audit_id(through_model)

                # existing relations
                audit_ids = through_model.objects.filter(**{assumed_column_name: obj.pk}).values_list('audit_id', flat=True)
                row_log_set |= RowLog.objects.filter(Q(audit_id__in=audit_ids) |  # existing relations
                                                     Q(**{'changes__'+assumed_column_name: obj.pk}),  # deleted relations
                                                     event__table_relid__table_name=through_model._meta.db_table)

                # inserts that are now deleted
                row_log_set |= RowLog.objects.filter(event__table_relid__table_name=through_model._meta.db_table,
                                                     audit_id__in=row_log_set.values_list('audit_id', flat=True))
        row_log_set = row_log_set.select_related('event')  # .order_by('-audit_id')
        m2m_tables = [x.related_model._meta.db_table for x in model._meta.many_to_many]
        m2m_tables.append(db_table)

        return row_log_set


@admin.register(RowLog)
class RowLogAdmin(NoAdditionsMixin, admin.ModelAdmin):

    list_display = ('pk', 'get_table_operation', 'get_table_name', 'changes', 'get_audit_id_url', 'get_select')
    list_filter = (ObjectRowLogFilter, 'event__table_operation', 'event__table_relid__table_name', )

    # Additional fields

    def get_table_operation(self, obj):
        return obj.event.table_operation
    get_table_operation.short_description = 'Operation'

    def get_table_name(self, obj):
        return obj.event.table_relid.table_name
    get_table_name.short_description = "Table"

    def get_audit_id_url(self, obj):
        info = self.model._meta.app_label, self.model._meta.model_name
        url = reverse('admin:%s_%s_subject_redirect' % info, args=(obj.pk,))
        return "<a href=\"%s\">%s</a>" % (url, str(obj.audit_id))
    get_audit_id_url.allow_tags = True
    get_audit_id_url.short_description = "Audit Id"

    def get_select(self, obj):
        # TODO: If the view try to get slow, make it so this view is handled through redirect
        try:
            model_name = obj.subject_model._meta.model_name
            row_log_url = reverse('admin:%s_%s_changelist' % (self.model._meta.app_label, self.model._meta.model_name))
            return "<a href=\"%s?%s=%s&%s=%s\">Select</a>" % (row_log_url,
                                                              ObjectRowLogFilter.model_parameter,
                                                              ObjectRowLogFilter.object_audit_id_parameter,
                                                              model_name,
                                                              str(obj.audit_id))
        except NonManagedTable:
            return "-"
    get_select.allow_tags = True
    get_select.short_description = "Select"

    # Actions

    actions = ['undo_changes']

    def undo_changes(self, request, queryset):
        irrevertable = []
        for row_log in queryset.order_by('-id'):
            try:
                row_log.revert()
            except NonManagedTable:
                irrevertable.append(row_log)
        if len(queryset) > len(irrevertable):
            rev_message = "%d row(s) were successfully reverted." % (len(queryset) - len(irrevertable),)
            self.message_user(request, rev_message)
        if irrevertable:
            irrev_message = "%d row(s) are irreversible through the admin. IDs are: %s" % (len(irrevertable), ", ".join([str(x.pk) for x in irrevertable]))
            self.message_user(request, irrev_message, level=messages.ERROR)
    undo_changes.short_description = "Revert selected changes"

    # Other

    def get_urls(self):
        """ Additional views """
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name

        urls = patterns('',
                        url(r'^(.+)/subject_view/$',
                            wrap(self.subject_view),
                            name='%s_%s_subject_redirect' % info),
                        )

        super_urls = super(RowLogAdmin, self).get_urls()

        return urls + super_urls

    def subject_view(self, request, object_id, form_url='', extra_context=None):
        """ The view redirects to the object admin change view if such exist """
        try:
            # try to get object link if it exists and has admin page
            obj = self.model.objects.get(pk=object_id)
            logged_subject = obj.subject
            if logged_subject:
                return redirect(reverse('admin:%s_%s_change' % (logged_subject._meta.app_label,
                                                                logged_subject._meta.model_name),
                                        args=(logged_subject.id,)))
        except (NonManagedTable, NoReverseMatch, self.model.DoesNotExist):
            pass

        # otherwise redirect back to the RowLog changelist
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        info = self.model._meta.app_label, self.model._meta.model_name
        return redirect(reverse('admin:%s_%s_changelist' % info))

    change_list_template = 'change_list.html'

    def get_changelist(self, request, **kwargs):
        from django.contrib.admin.views.main import ChangeList

        class ObjectChangeList(ChangeList):

            def get_queryset(self, request):
                # filter down to object-related RowLogs
                return super(ObjectChangeList, self).get_queryset(request)

        return ObjectChangeList

    def changelist_view(self, request, extra_context=None):
        extra = {}
        response = super(RowLogAdmin, self).changelist_view(request, extra_context=extra)

        if hasattr(response, 'context_data'):
            try:
                extra = self.get_subject_context()
                response.context_data.update(extra or {})
            except NoReverseMatch:
                pass

        return response

    # Helpers

    def get_subject_context(self):
        if getattr(self, '_filter_subject', None):
            obj = self._filter_subject
            model = type(self._filter_subject)
            obj_url = urlresolvers.reverse("admin:%s_%s_change" % (model._meta.app_label, model._meta.model_name.lower()),
                                           args=(obj.pk,))

            return dict(obj=obj, obj_model=model.__name__, obj_url=obj_url)


class VersionModelAdmin(ModelAdmin):
    change_form_template = 'change_form.html'
    manage_view_template = 'manage_view.html'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super(VersionModelAdmin, self).get_readonly_fields(request, obj)
        self.contribute_audit_id(self.model)
        return readonly_fields + ('audit_id', )

    def get_urls(self):
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name

        urls = patterns('',
                        url(r'^(.+)/manage/$',
                            wrap(self.manage_view),
                            name='%s_%s_manage' % info),
                        )

        super_urls = super(VersionModelAdmin, self).get_urls()

        return urls + super_urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['model_name'] = self.model._meta.model_name
        extra_context['app_label'] = self.model._meta.app_label

        try:
            return super(VersionModelAdmin, self).change_view(request, object_id, form_url, extra_context=extra_context)
        except Exception:
            from django.db import connections
            print(connections.query())
            raise

    def manage_view(self, request, id, form_url='', extra_context=None):
        opts = self.model._meta
        self.contribute_audit_id(self.model)
        obj = self.model.objects.get(pk=id)

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        preserved_filters = self.get_preserved_filters(request)
        form_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, form_url)

        # Get changes
        history = self.get_row_logs(obj=obj)

        context = {
            'title': 'Manage %s' % obj,
            'has_change_permission': self.has_change_permission(request, obj),
            'form_url': form_url,
            'opts': opts,
            'history': history,
            'app_label': opts.app_label,
            'original': obj,
        }
        context.update(extra_context or {})

        return render(request, self.manage_view_template, context)

    def contribute_audit_id(self, model):
        if not hasattr(model, 'audit_id'):
            add_audit_id(model)

    def get_row_logs(self, obj):
        db_table = self.model._meta.db_table
        print(db_table)

        # Self audit
        row_log_set = RowLog.objects.filter(event__table_relid__table_name=db_table,
                                            audit_id=obj.audit_id)

        # m2m audit
        for m2m_field in self.model._meta.many_to_many:
            assumed_column_name = m2m_field.remote_field.related_query_name + '_id'
            through_model = getattr(self.model, m2m_field.name).through
            self.contribute_audit_id(through_model)

            # existing relations
            audit_ids = through_model.objects.filter(**{assumed_column_name: obj.pk}).values_list('audit_id', flat=True)
            row_log_set |= RowLog.objects.filter(Q(audit_id__in=audit_ids) |  # existing relations
                                                 Q(**{'changes__'+assumed_column_name: obj.pk}),  # deleted relations
                                                 event__table_relid__table_name=through_model._meta.db_table)

            # inserts that are now deleted
            row_log_set |= RowLog.objects.filter(event__table_relid__table_name=through_model._meta.db_table,
                                                 audit_id__in=row_log_set.values_list('audit_id', flat=True))
        row_log_set = row_log_set.select_related('event').order_by('-audit_id')
        m2m_tables = [x.related_model._meta.db_table for x in self.model._meta.many_to_many]
        m2m_tables.append(db_table)

        return row_log_set
