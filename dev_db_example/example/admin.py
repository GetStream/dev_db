from django.contrib import admin
from . import models as example_models
from django.db.models.base import ModelBase
import inspect

for k, m in inspect.getmembers(example_models, lambda x: isinstance(x, ModelBase)):
    if m.__module__ == example_models.__name__:
        admin.site.register(m)
