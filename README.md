django-disenchained helps you free Django from the shackles of inefficient queries!

## What

The Django ORM is great because it lets you treat a relational database as a collection of objects but it's a leaky abstraction that makes it _very easy_ to write inefficient code. Especially in large codebases where the functions that query the database are far removed from the view (and written by someone else), it's not readily obvious that you're making multiple queries when one would have sufficed.

`disenchained` logs all queries executed during a Django view, management command or any arbitrary function and provides tools to analyze the query log. You can identify long-running queries; duplicate queries; files, functions or specific lines of code that generate lots of queries; and more!

## How it works

`disenchained.panels.DisenchainedPanel` defines a custom panel for the
[django-debug-toolbar](https://github.com/django-debug-toolbar/django-debug-toolbar) that saves the query log in a pickle file that can
later be analyzed by other `disenchained` modules. Enabling the panel (see below)
is all it takes to log queries executed during views.

`disenchained.decorators.log_queries` defines a decorator that logs queries
executed by the decorated function.

## Setup and Configuration

1. Install `disenchained` by cloning the git repo and running setup.py or using pip:


    ```sh
    pip install django-disenchained
    ```


2. Enable the debug toolbar, add the `disenchained.panels.DisenchainedPanel` panel and specify the `DISENCHAINED_DATA_DIRECTORY` parameter. 

    Your `settings.py` should include this:

    ```python

    if 'debug_toolbar' in settings['INSTALLED_APPS']:
        settings['DISENCHAINED_DATA_DIRECTORY'] = "/var/disenchained-data"
        settings['MIDDLEWARE_CLASSES'].append(
            'debug_toolbar.middleware.DebugToolbarMiddleware')

        settings['DEBUG_TOOLBAR_PANELS'] = (
            'disenchained.panels.DisenchainedPanel',
            'debug_toolbar.panels.sql.SQLDebugPanel',
        )
    ```

    For every request, the `django-disenchained` will place a pickle file in the `DISENCHAINED_DATA_DIRECTORY` directory with the name `<view_name>.<timetamp>.pickle`.

## Usage: logging queries in a view

After you visit a page, click the `Disenchained` panel in the debug toolbar to get
the full path to the saved pickle file. Or, simply check the directory specified
by `DISENCHAINED_DATA_DIRECTORY`. 

## Usage: logging queries in a function

The following is an example of decorating a Django management command:

```
from django.core.management.base import BaseCommand
from disenchained.decorators import log_queries

from myapp.models import Book
from myapp.utils import sales_summary

class Command(BaseCommand):
    args = ()

    @log_queries('my_command')
    def handle(self, *args, **kwargs):
        for book in Book.objects.all():
            print sales_summary(book)
```

All queries executed during the execution of this command will be logged and
outputted as a pickle file in the directory specified by the
`DISENCHAINED_DATA_DIRECTORY` setting and with the filename
`my_command.<timestamp>.pickle`.

## Usage: analyzing disenchained pickle files

[Gist:abhik/5089967](https://gist.github.com/abhik/5089967) includes `models.py` and `views.py` for a toy Django app that demonstrates the use of `disenchained` to identify inefficient use of queries. The app includes several models and a view for a simple book store app.  

The following is an example session in the python shell for using the `disenchained` pickle file to analyze queries executed during a view in the toy app defined above. Keep in mind that, although this uses a toy problem where the solution is obvious (and the code obviously poorly written), the same types of inefficiencies have been found in large, well-written code bases. The ORM is a wonderful thing but can hide many inefficiencies.

```python
>>> from disenchained import DebugFile
>>> from disenchained.query import most_common
>>> from disenchained.query import num_duplicates
>>> from disenchained.query import where

# Load the disenchained pickle file
# The DISENCHAINED_DATA_DIRECTORY setting specifies the directory for these files
>>> debug = DebugFile("/var/disenchained-data/sales_summary.136248367389.pickle")

# Some metadata about the view
>>> debug.info
{'app_name': 'books',
 'func_args': (),
 'func_kwargs': {'sales_campaign': u'supersale'},
 'func_name': 'sales_summary',
 'sessionid': '338065d96ad99fdacb2a96afd3433d62',
 'url_name': 'sales_summary',
 'view_name': 'sales_summary'}

>>> len(debug.queries)
1663

# in milliseconds
>>> sum(query.duration for query in debug.queries)
510.6410000000003

# How many queries are exact duplicates (same query template and params)?
# In most cases, this should be zero!
>>> num_duplicates(debug.queries, "sql")
999

# How many queries have the same template but different params?
# Often, this indicates that we're making O(N) queries instead of O(1) -- a
# common problem when using an ORM.
>>> num_duplicates(debug.queries, "rawsql")
1659

# What's the most common exact query (same template and params)?
>>> most_common(debug.queries, "sql", n=3)
[{'count': 1000,
  'duration': 279.4810000000006,
  'key': 'SELECT "books_salescampaign"."id", "books_salescampaign"."name" FROM "books_salescampaign" WHERE "books_salescampaign"."id" = 1 '},
 {'count': 1,
  'duration': 0.245,
  'key': 'SELECT "books_booksale"."id", "books_booksale"."book_id", "books_booksale"."price", "books_booksale"."sales_campaign_id" FROM "books_booksale" WHERE "books_booksale"."book_id" = 201 '},
 {'count': 1,
  'duration': 0.304,
  'key': 'SELECT "books_booksale"."id", "books_booksale"."book_id", "books_booksale"."price", "books_booksale"."sales_campaign_id" FROM "books_booksale" WHERE "books_booksale"."book_id" = 383 '}]

# Wow, this one query is executed 1000 times and takes up 54% of the query runtime.
# Let's dig into it further
>>> bad_sql = most_common(debug.queries, "sql")[0]['key']
>>> bad_queries = where(debug.queries, "sql", bad_sql)
>>> len(bad_queries)
1000

# All 100 queries are executed from the same function..
>>> most_common(bad_queries, "function", n=2)
[{'count': 1000,
  'duration': 279.4810000000006,
  'key': FunctionInfo(file='/Users/abhik/src/disenchained_demo/books/models.py', function='has_discount')}]

# ..and the same line of code.
>>> most_common(bad_queries, "codeline", n=2)
[{'count': 1000,
  'duration': 279.4810000000006,
  'key': Codeline(file='/Users/abhik/src/disenchained_demo/books/models.py', function='has_discount', lineno=34)}]

# You can also see the stacktrace for any query to see exactly where and why it
# was executed. This should give you a good starting point for eliminating
# these duplicate queries.
>>> bad_queries[0].stacktrace
[('/usr/local/Cellar/python/2.7.3/lib/python2.7/site-packages/django/contrib/staticfiles/handlers.py',
  67,
  '__call__',
  'return self.application(environ, start_response)'),
 ('/Users/abhik/src/disenchained_demo/books/views.py',
  15,
  'sales_summary',
  'total_sales[book.name] = book.total_sales()'),
 ('/Users/abhik/src/disenchained_demo/books/models.py',
  11,
  'total_sales',
  'if sale.has_discount:'),
 ('/Users/abhik/src/disenchained_demo/books/models.py',
  34,
  'has_discount',
  'return self.sales_campaign.has_discount')]

# Now, let's look at duplicated "raw" queries -- these are the same template
# query but with different params.
>>> most_common(debug.queries, "rawsql", n=3)
[{'count': 1000,
  'duration': 279.4810000000006,
  'key': 'SELECT "books_salescampaign"."id", "books_salescampaign"."name" FROM "books_salescampaign" WHERE "books_salescampaign"."id" = %s '},
 {'count': 661,
  'duration': 215.9600000000001,
  'key': 'SELECT "books_booksale"."id", "books_booksale"."book_id", "books_booksale"."price", "books_booksale"."sales_campaign_id" FROM "books_booksale" WHERE "books_booksale"."book_id" = %s '},
 {'count': 1,
  'duration': 8.776,
  'key': 'SELECT DISTINCT "books_book"."id", "books_book"."name" FROM "books_book" INNER JOIN "books_booksale" ON ("books_book"."id" = "books_booksale"."book_id") INNER JOIN "books_salescampaign" ON ("books_booksale"."sales_campaign_id" = "books_salescampaign"."id") WHERE "books_salescampaign"."name" = %s '}]

# All of these are also executed from a single line of code.
>>> bad_rawsql = most_common(debug.queries, "rawsql", n=3)[1]['key']
>>> most_common(where(debug.queries, "rawsql", bad_rawsql), "codeline")
[{'count': 661,
  'duration': 215.9600000000001,
  'key': Codeline(file='/Users/abhik/src/disenchained_demo/books/models.py', function='total_sales', lineno=9)}]
```
