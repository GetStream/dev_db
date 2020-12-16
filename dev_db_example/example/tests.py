from operator import attrgetter

from django.core import serializers
from django.test.testcases import TestCase
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User, Permission, Group
from django.contrib.sites.models import Site as DjangoSite
from django.contrib.contenttypes.models import ContentType

from .dev_db_creator import ExampleDevDBCreator
from .models import (
    UserDependency,
    ForwardDependency,
    ReverseDependency,
    Loop,
    NotRelatedToUser,
    NotRelatedToUserDependency,
    M2MRegular,
    M2MThrough,
    Through,
    Extra,
)


class CreatorTestCase(TestCase):
    fixtures = ["auth.json", "example.json"]

    @classmethod
    def setUpTestData(cls):
        cls.creator = ExampleDevDBCreator()
        cls.result_data = cls.creator.filter_data(
            cls.creator.collect_data(cls.creator.get_model_settings())
        )

    def _model_result(self, model):
        return list(
            filter(
                lambda x: isinstance(x, model),
                self.result_data,
            )
        )

    def test_model_listing(self):
        """
        Some models are listed
        """
        models = self.creator.get_models()
        self.assertTrue(models)

    def test_model_settings(self):
        """
        A correct settings are loaded
        """
        model_settings = self.creator.get_model_settings()
        expected_result = [
            (UserDependency, 30),
            (ForwardDependency, 30),
            (ReverseDependency, 30),
            (Loop, 30),
            (NotRelatedToUser, 30),
            (NotRelatedToUserDependency, 30),
            (M2MRegular, 30),
            (M2MThrough, 30),
            (Through, 30),
            (Session, 30),
            (DjangoSite, 30),
            (Permission, 30),
            (Group, 30),
            (User, 30),
            (ContentType, 30),
        ]
        self.assertCountEqual(model_settings, expected_result)

    def test_collect(self):
        """
        Some data are collected
        """
        self.assertTrue(self.result_data)

    def test_filter_step(self):
        """
        Filter removes duplicates
        """
        instance = UserDependency.objects.all()[:1][0]
        list_with_duplicates = [instance.user, instance, instance.user]
        correct_result = [instance.user, instance]
        result = self.creator.filter_data(list_with_duplicates)
        self.assertEqual(result, correct_result)

    def test_full_create(self):
        """
        We are able to output a valid JSON
        """
        model_settings = self.creator.get_model_settings()
        data = self.creator.collect_data(model_settings)
        extra_data = self.creator.add_extra_data(data)
        filtered_data = self.creator.filter_data(extra_data)
        serializers.serialize(
            "json", filtered_data, indent=4, use_natural_foreign_keys=True
        )

    def test_only_staff(self):
        """
        Users that are not staff should be ignored
        """
        users = self._model_result(User)
        self.assertCountEqual(users, User.objects.filter(is_staff=True))
        self.assertNotIn(
            False,
            map(attrgetter("is_staff"), users),
        )

    def test_user(self):
        """
        All user dependencies are fetched
        """
        user_dependencies = self._model_result(UserDependency)
        self.assertCountEqual(
            user_dependencies,
            UserDependency.objects.filter(user__in=User.objects.filter(is_staff=True)),
        )

    def test_forward(self):
        """
        All forward dependencies are fetched
        """
        user_dependencies = self._model_result(UserDependency)
        forward_dependencies = self._model_result(ForwardDependency)
        self.assertCountEqual(
            forward_dependencies,
            set(map(attrgetter("forward_dependency"), user_dependencies)),
        )

    def test_reverse(self):
        """
        All reverse dependencies are fetched
        """
        reverse_dependencies = self._model_result(ReverseDependency)
        self.assertCountEqual(
            ReverseDependency.objects.filter(
                dependency__in=UserDependency.objects.filter(
                    user__in=User.objects.filter(is_staff=True)
                )
            ),
            reverse_dependencies,
        )

    def test_loop(self):
        """
        All loop components are fetched
        """
        loops = self._model_result(Loop)
        self.assertCountEqual(
            Loop.objects.all(),
            loops,
        )

    def test_unrelated(self):
        """
        All instances unrelated to user are fetched
        """
        unrelated = self._model_result(NotRelatedToUser)
        self.assertCountEqual(
            NotRelatedToUser.objects.all(),
            unrelated,
        )

        unrelated_dependencies = self._model_result(NotRelatedToUserDependency)
        self.assertCountEqual(
            NotRelatedToUserDependency.objects.all(),
            unrelated_dependencies,
        )

    def test_m2m(self):
        """
        All many to many dependencies are fetched
        """
        for model in (M2MRegular, M2MThrough, Through):
            m2m = self._model_result(model)
            self.assertCountEqual(
                model.objects.all(),
                m2m,
            )

    def test_extra(self):
        """
        Only selected extra instances are fetched (Extra is excluded)
        """
        extra = self._model_result(Extra)
        self.assertFalse(extra)

        extra = self.creator.add_extra_data(extra)
        self.assertEqual(len(extra), 1)
