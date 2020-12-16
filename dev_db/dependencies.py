from collections import defaultdict

from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField

from dev_db.utils import get_all_fields


def get_dependency_mapping(models):
    """
    Returns a mapping in form of:
    {model: set of (models, attributes) that depend on it}
    """
    mapping = defaultdict(set)

    for model in models:
        _mapping_for_model(model, mapping, set())

    return mapping


def _mapping_for_model(model, mapping, visited):
    visited.add(model)

    for field in get_all_fields(model):
        if isinstance(field, (ForeignKey, OneToOneField, ManyToManyField)):
            if (
                isinstance(field, ManyToManyField)
                and hasattr(field.remote_field.through, "_meta")
                and not field.remote_field.through._meta.auto_created
            ):  # user-defined M2M models
                _mapping_for_model(field.remote_field.through, mapping, visited)
                continue

            mapping[field.related_model].add((model, field.name))

            if field.related_model not in visited:
                _mapping_for_model(field.related_model, mapping, visited)
