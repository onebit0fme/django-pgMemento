from django.db import models


class TestModel(models.Model):

    name = models.TextField()
    is_good = models.BooleanField()

    class Meta:
        app_label = 'test_app'
