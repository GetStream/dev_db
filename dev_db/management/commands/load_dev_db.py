"""
Dumps data from the main database, but only dumps a subset of the items
To ensure we can load them on the development server

We use this because the production database became too heavy to load even with
optimized tools like pg_dump

This script follows relations to ensure referential integrity so if you load
blog_post, it will ensure the author is also serialized
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import BaseCommand
import logging
import os

logger = logging.getLogger(__name__)
DEBUG = False


class Command(BaseCommand):
    help = 'Output a sample of the database as a fixture of the given format.'

    def add_arguments(self, parser):
        parser.add_argument('--format', default='json', dest='format', help='Specifies the output serialization format for fixtures.')
        parser.add_argument('--indent', default=4, dest='indent', type=int, help='Specifies the indent level to use when pretty-printing output')
        parser.add_argument('--limit', default=None, dest='limit', type=int, help='Allows you to limit the number of tables, used for testing purposes only')
        parser.add_argument('--skipcache', default=False, dest='skipcache', action='store_true', help='Skips the settings cache')

    def handle(self, **options):
        fixture_path = os.path.join(
            settings.BASE_ROOT, 'development_data.json.gz')
        logger.info('loading the fixture from %s', fixture_path)

        ContentType.objects.clear_cache()
        call_command('loaddata', fixture_path,
            exclude=['contenttypes.ContentType', 'auth.Permission', 'auth.Group'],
            traceback=True, verbosity=3
        )
