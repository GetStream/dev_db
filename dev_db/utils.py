"""
Model level functions
"""
import time


def get_max_id(model):
    last = model._default_manager.order_by("-pk").first()
    return last.pk if last and isinstance(last, int) else 0


def get_field_names(model):
    return [f.name for f in model._meta.fields]


def model_name(model):
    return model._meta.label


def get_all_fields(model):
    # follow forward relation fields
    normal_fields = model._meta.fields
    many_to_many_fields = model._meta.many_to_many
    private_fields = model._meta.private_fields

    all_fields = list(normal_fields) + list(many_to_many_fields) + list(private_fields)
    return all_fields


"""
Instance level functions
"""


def hash_instance(instance):
    return hash((instance.__class__, instance.pk))


"""
General utilities
"""


def get_creator_instance():
    creator_class = get_creator_class()
    return creator_class()


def get_creator_class():
    from django.conf import settings

    default = "dev_db.creator.DevDBCreator"
    creator_class_string = getattr(settings, "DEV_DB_CREATOR", default)
    creator_class = get_class_from_string(creator_class_string)
    return creator_class


def get_class_from_string(path, default="raise"):
    """
    Return the class specified by the string.

    IE: django.contrib.auth.models.User
    Will return the user class

    If no default is provided and the class cannot be located
    (e.g., because no such module exists, or because the module does
    not contain a class of the appropriate name),
    ``django.core.exceptions.ImproperlyConfigured`` is raised.
    """
    from django.core.exceptions import ImproperlyConfigured

    backend_class = None
    try:
        from importlib import import_module
    except ImportError:
        from django.utils.importlib import import_module
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1 :]
    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured(
            'Error loading registration backend %s: "%s"' % (module, e)
        )
    try:
        backend_class = getattr(mod, attr)
    except AttributeError:
        if default == "raise":
            raise ImproperlyConfigured(
                'Module "%s" does not define a registration '
                'backend named "%s"' % (module, attr)
            )
        else:
            backend_class = default
    return backend_class


class Timer:
    def __init__(self):
        self.times = [time.time()]
        self.total = 0.0
        next(self)

    def __iter__(self):
        while True:
            yield next(self)

    def __next__(self):
        times = self.times
        times.append(time.time())
        delta = times[-1] - times[-2]
        self.total += delta
        return delta

    def get_avg(self, default=None):
        if self.times:
            return self.total / len(self.times)
        return default

    avg = property(get_avg)


def get_profile_class():
    from django.conf import settings
    from django.db import models

    profile_string = settings.AUTH_PROFILE_MODULE
    app_label, model = profile_string.split(".")

    return models.get_model(app_label, model)
