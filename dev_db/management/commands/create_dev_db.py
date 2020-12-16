"""
Dumps data from the main database, but only dumps a subset of the items
To ensure we can load them on the development server

We use this because the production database became too heavy to load even with
optimized tools like pg_dump

This script follows relations to ensure referential integrity so if you load
blog_post, it will ensure the author is also serialized
"""
import gzip
import logging
from pathlib import Path

from django.core import serializers
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

from dev_db.utils import Timer
from dev_db.utils import get_creator_instance


logger = logging.getLogger(__name__)
DEBUG = False


class Command(BaseCommand):
    help = "Output a sample of the database as a fixture of the given format."

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            default=None,
            dest="format",
            help="Specifies the output serialization format for fixtures (default: guess it from the filename)",
        )
        parser.add_argument(
            "--indent",
            default=4,
            dest="indent",
            type=int,
            help="Specifies the indent level to use when pretty-printing output",
        )
        parser.add_argument(
            "--limit",
            default=None,
            dest="limit",
            type=int,
            help="Allows you to limit the number of tables, used for testing purposes only",
        )
        parser.add_argument(
            "-o",
            "--output",
            default="development_data.json.gz",
            dest="output",
            type=str,
            help="Path of the output file (default: development_data.json.gz)",
        )
        parser.add_argument(
            "--clear-cache",
            default=False,
            dest="clearcache",
            action="store_true",
            help="Clear the model settings cache",
        )

    def handle(self, **options):
        # setup the options
        self.indent = options.get("indent", 4)
        self.limit = options.get("limit")
        self.output = Path(options.get("output"))
        self.clearcache = options.get("clearcache")
        self.format = options.get("format") or (
            self.output.suffixes[0][1:].lower() if self.output.suffixes else "json"
        )
        self._validate_serializer(self.format)
        logger.info("serializing using %s and indent %s", self.format, self.indent)

        t = Timer()
        creator = get_creator_instance()
        logger.info("using creator instance %s", creator)

        if self.clearcache:
            logger.info("clearing the model settings cache")
            cache.delete("cached_model_settings")

        model_settings = creator.get_cached_model_settings()

        logger.info("model_settings lookup took %.2f s", next(t))
        data = creator.collect_data(model_settings, limit=self.limit)
        logger.info("data collection took %.2f s", next(t))
        extra_data = creator.add_extra_data(data)
        logger.info("adding extra data took %.2f s", next(t))
        filtered_data = creator.filter_data(extra_data)
        logger.info("filtering data took %.2f s", next(t))
        logger.info("in total, we collected %d unique instances", len(extra_data))
        logger.info(
            "serializing data with format %s (this can take a while)", self.format
        )
        serialized = serializers.serialize(
            self.format,
            filtered_data,
            indent=self.indent,
            use_natural_foreign_keys=False,
        )

        fopen = gzip.open if self.output.suffix == ".gz" else open

        with fopen(self.output.resolve(), "wb") as f:
            f.write(serialized.encode())

        logger.info("serializing data took %.2f s", next(t))
        logger.info("total duration %.2f s", t.total)

    def _validate_serializer(self, format):
        # Check that the serialization format exists; this is a shortcut to
        # avoid collating all the objects and _then_ failing.
        try:
            serializers.get_serializer(format)
        except KeyError:
            raise CommandError("Unknown serialization format: %s" % format)
