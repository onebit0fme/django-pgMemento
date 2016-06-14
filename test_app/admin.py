from django.contrib import admin
from pg_memento.admin import VersionModelAdmin
from .models import TestModel
from django.contrib.auth import get_user_model


# @admin.register(TestModel)
# class TestModelAdmin(admin.ModelAdmin):
#     pass



# forms

from django.forms import ModelForm


class TestModelForm(ModelForm):

    class Meta:
        model = TestModel
        fields = ('name', 'is_good')


admin.site.register(TestModel, VersionModelAdmin)

User = get_user_model()
admin.site.unregister(User)
admin.site.register(User, VersionModelAdmin)
