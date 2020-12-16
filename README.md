Django development database
===========================

Tool to automatically create a development database for local development by sampling your production database of your Django application.
It maintains referential integrity by looking up the dependencies for the selected rows.
Regarding sampling of users, it only selects the site staff, so the customer data will not be compromised.


Installation
============

Use the Python package manager pip:

```bash
  pip install dev_db
```

Add `dev_db` to your installed apps:

```python
INSTALLED_APPS = [
    …
    "dev_db",
    …
]
```


Customization
=============

Optionally, you can customize the `DevDBCreator` class by creating a new file `dev_db_creator.py` inside your project:

```python
from dev_db.creator import DevDBCreator


class CustomisedDBCreator(DevDBCreator):
    …
```

You then need to provide the path to your customised class to your settings file:

```python
DEV_DB_CREATOR = 'your_project.dev_db_creator.CustomisedDBCreator'
```


Creating the data
=================

```bash
  python manage.py create_dev_db
```

Creating the test fixture usually takes a minute or two on a remote database. By default, the data are saved as `development_data.json.gz`. If you need to save them as a different filename, use the `--output` parameter.


Loading the data
================

First, you need to apply the migrations on an empty database:

```bash
  python manage.py migrate
```

Then, you just load the created fixture from the `development_data.json.gz` file:

```bash
  python manage.py load_dev_db
```

Beware, this step will truncate the `auth_permission` and `django_content_type` tables, which are filled up by the Django migrations. So do not ever attempt to run this command on the production database.


Running tests
=============

From the `dev_db_example` directory run:

```bash
  python manage.py test
```
