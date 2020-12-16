from collections import defaultdict
import logging
from itertools import chain
from operator import attrgetter, itemgetter

import django.apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.functional import cached_property
from django.db.models.fields.related import ManyToManyField

from dev_db.decorators import cached
from dev_db.dependencies import get_dependency_mapping
from dev_db.utils import get_max_id, hash_instance, model_name

logger = logging.getLogger(__name__)
DEFAULT_LIMIT = 30


class DevDBCreator:
    """
    The dev creator class handles all the logic for creating a dev db sample from your main database

    It starts by getting the models it needs to run on
    - get_models
    - get_model_settings (determines how large a sample set we need for the given tables)
    - collect_data (actually retrieves the data)
    The collected data is ready for serialization
    """

    exclude_content_type = False

    @cached_property
    def reverse_mapping(self):
        return get_dependency_mapping(self.models)

    @cached_property
    def forward_mapping(self):
        mapping = defaultdict(set)

        for model, dependencies in self.reverse_mapping.items():
            for dependency, attr in dependencies:
                mapping[dependency].add((model, attr))

        return mapping

    @cached_property
    def model_settings(self):
        return {x: y for x, y in self.get_cached_model_settings()}

    @cached_property
    def models(self):
        return self.get_models()

    def get_models(self):
        """
        Get models creates a list of models to create the dev db from
        - full required (a custom list of models which you want imported in full)
        - all valid_models (you can list excluded models in self.get_all_models())
        """
        # these models go first
        full_required = self.get_full_required()
        excluded = self.get_excluded_models()
        all_models = self.get_all_models()
        valid_models = list(full_required)

        for model in all_models:
            if (
                model not in valid_models
                and all(map(lambda x: x not in model._meta.db_table, excluded))
                and not model._meta.proxy
            ):
                try:
                    model._default_manager.first()  # trigger potential database errors
                except Exception as e:
                    logger.error("%s: %s", type(e).__name__, e)
                else:
                    valid_models.append(model)

        logger.info("processing models: %s", list(map(model_name, valid_models)))

        return valid_models

    def get_model_settings(self):
        """
        determines how large a sample set we need for the given tables
        """
        model_settings = []
        full_required = self.get_full_required()

        for model in self.models:
            logger.info("getting settings for %s", model_name(model))
            max_id = get_max_id(model)
            if max_id > 50:
                limit = 10
            else:
                limit = DEFAULT_LIMIT
            if model in full_required:
                limit = 2000
            setting = (model, limit)
            model_settings.append(setting)
        return model_settings

    def collect_data(self, model_settings, limit=None):
        """
        You can easily add more data by implementing get_custom_data
        """
        # first add the data we are manually specifying
        logger.info("loading the custom data first")
        custom_data, fetched_pks = self.get_custom_data()

        models = set(map(itemgetter(0), model_settings))

        for obj in custom_data.keys():
            if obj in models:
                model_settings = list(filter(lambda x: x[0] != obj, model_settings))
                logger.info(
                    "skipping already collected data for custom model %s",
                    model_name(obj),
                )

        objects = list(chain.from_iterable(custom_data.values()))
        dependencies = defaultdict(list)

        for model, limit in model_settings[:limit]:
            logger.info("getting %s items for model %s", limit, model_name(model))
            queryset = model._default_manager.order_by("-pk")[:limit]
            objects.extend(queryset)
            self._fetch_forward_dependencies(model, queryset, dependencies, fetched_pks)

        objects.extend(list(chain.from_iterable(dependencies.values())))

        return objects

    def _fetch_forward_dependencies(self, model, qs, result, fetched_pks):
        for dependency, attr in self.forward_mapping.get(model, []):
            if self.exclude_content_type and isinstance(
                dependency, (ContentType, Permission)
            ):
                continue

            logger.info(
                "fetching dependency %s -> %s",
                model_name(model),
                model_name(dependency),
            )

            if isinstance(model._meta.get_field(attr), ManyToManyField):
                qs_new = dependency._base_manager.none()

                for q in qs.prefetch_related(attr):
                    qs_new = qs_new.union(
                        getattr(q, attr)
                        .exclude(pk__in=fetched_pks[dependency])
                        .order_by()
                    )
            else:
                qs_new = dependency._base_manager.filter(
                    pk__in=tuple(map(attrgetter(attr + "_id"), qs))
                ).exclude(pk__in=fetched_pks[dependency])

            if qs_new:
                result[dependency].extend(list(qs_new))
                fetched_pks[dependency].update(set(map(attrgetter("pk"), qs_new)))

                if dependency in self.forward_mapping:
                    self._fetch_forward_dependencies(
                        dependency, qs_new, result, fetched_pks
                    )

    def _fetch_reverse_dependencies(self, model, qs, result, fetched_pks):
        self._fetch_forward_dependencies(model, qs, result, fetched_pks)

        for dependency, attr in self.reverse_mapping.get(model, []):
            logger.info(
                "fetching dependency %s <- %s",
                model_name(model),
                model_name(dependency),
            )
            qs_new = dependency._base_manager.filter(**{attr + "__in": qs}).exclude(
                pk__in=fetched_pks[dependency]
            )[
                : max(
                    0,
                    self.model_settings.get(dependency, DEFAULT_LIMIT)
                    - len(fetched_pks[dependency]),
                )
            ]

            if qs_new:
                result[dependency].extend(list(qs_new))
                fetched_pks[dependency].update(set(map(attrgetter("pk"), qs_new)))

                if dependency in self.reverse_mapping:
                    self._fetch_reverse_dependencies(
                        dependency, qs_new, result, fetched_pks
                    )
                elif dependency in self.forward_mapping:
                    self._fetch_forward_dependencies(
                        dependency, qs_new, result, fetched_pks
                    )

    @cached(key="cached_model_settings", timeout=60 * 10)
    def get_cached_model_settings(self):
        return self.get_model_settings()

    def get_full_required(self):
        return set()

    def get_excluded_models(self):
        excluded = [
            "celery",
            "djcelery",
            "djkombu",
            "sentry",
            "south",
            # skip user profile as it gets loaded when users are loaded
            "user_profile",
            # log entries arent very interesting either
            "log",
        ]
        if self.exclude_content_type:
            # special cases in django which get generated automatically
            excluded += ["content_type", "permission"]
        return excluded

    def get_all_models(self):
        return django.apps.apps.get_models()

    def add_extra_data(self, data):
        """
        Replace this method with your own code
        """
        return data

    def get_custom_data(self):
        logger.info("loading staff users")
        user_model = get_user_model()
        qs = user_model._default_manager.filter(is_staff=True)[
            : self.model_settings.get(user_model, DEFAULT_LIMIT)
        ]

        custom_data = self._init_custom_data(user_model)
        custom_data[user_model].extend(list(qs))

        fetched_pks = defaultdict(set)
        fetched_pks[user_model].update(set(map(attrgetter("pk"), qs)))

        self._fetch_reverse_dependencies(user_model, qs, custom_data, fetched_pks)

        return custom_data, fetched_pks

    def _init_custom_data(self, model, custom_data=None):
        if custom_data is None:
            custom_data = defaultdict(list)

        for dependency, attr in self.reverse_mapping.get(model, []):
            if dependency not in custom_data:
                custom_data[dependency]  # initialize defaultdict key
                custom_data = self._init_custom_data(dependency, custom_data)

        return custom_data

    def filter_data(self, data):
        logger.info("filtering data to unique instances")
        unique_set = set()
        filtered_data = []
        for instance in data:
            h = hash_instance(instance)
            if h not in unique_set:
                unique_set.add(h)
                filtered_data.append(instance)
        return filtered_data
