"""
Loads data from the main database
"""
import logging
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models.signals import pre_save, post_save

logger = logging.getLogger(__name__)
DEBUG = False


class Command(BaseCommand):
    help = "Load the saved fixture from a file named development_data.json.gz."

    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--input",
            default="development_data.json.gz",
            dest="input",
            type=str,
            help="Path of the input file (default: development_data.json.gz)",
        )
        parser.add_argument(
            "-y",
            "--yes",
            default=False,
            dest="yes",
            action="store_true",
            help="Do not ask the users whether they are sure or not",
        )

    def handle(self, **options):
        self.input = Path(options.get("input"))
        self.yes = options.get("yes")

        fixture_path = (
            self.input
            if self.input.is_absolute()
            else Path(settings.BASE_ROOT) / self.input
        )
        logger.info("loading the fixture from %s", fixture_path)

        if not self.yes:
            print(
                "Beware, this step will delete data from your database {} at {}.".format(
                    connection.settings_dict["NAME"],
                    connection.settings_dict["HOST"] or "localhost",
                )
            )
            print("DO NOT EVER ATTEMPT TO RUN THIS COMMAND IN PRODUCTION!")

            answer = input("Are you sure you want to continue? [y/N] ")

            if not answer.lower().startswith("y"):
                return

        # these signals can trigger a DoesNotExist exception, so we disconnect them
        signals = {pre_save: [], post_save: []}

        for signal in signals.keys():
            signals[signal] = signal.receivers
            signal.receivers = []

        # ContentType and Permission models are populated by the migrations and
        # that would clash with the loaded data, so we need to truncate these tables
        logger.info("cleaning ContentType and Permission models")
        ContentType.objects.all().delete()
        Permission.objects.all().delete()

        call_command(
            "loaddata",
            fixture_path,
            traceback=True,
            verbosity=3,
        )

        for signal, receivers in signals.items():
            signal.receivers = receivers
