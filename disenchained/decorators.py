"""Decorator interface to logging queries.

The `log_queries` decorator allows you to log (and later analyze) all queries
performed during the executing of the decorated function.

Example of profiling a Django management command:

```
from django.core.management.base import BaseCommand
from disenchained.decorators import log_queries

from myapp.models import Book

class Command(BaseCommand):
    args = ()

    @log_queries('my_command')
    def handle(self, *args, **kwargs):
        print Book.objects.count()
```

All queries executed during the execution of this command will be logged and
outputted as a pickle file in the directory specified by the
`DISENCHAINED_DATA_DIRECTORY` setting and with the filename
`my_command.<timestamp>.pickle`. This file can be analyzed with
`disenchained` tools to identify potential optimizations.

"""

from collections import defaultdict
from functools import wraps
import thread

from debug_toolbar.utils.tracking.db import CursorWrapper
from debug_toolbar.utils.tracking import replace_call
from debug_toolbar.panels.sql import SQLDebugPanel
from django.db.backends import BaseDatabaseWrapper

from disenchained.panels import dump_queries


class QueryLogger(object):
    """Singleton for maintaing query loggers per thread.
    """

    _loggers = defaultdict(lambda: SQLDebugPanel())

    @classmethod
    def get_current(cls):
        return cls._loggers[thread.get_ident()]


# Inject debug-toolbar's tracking cursor
@replace_call(BaseDatabaseWrapper.cursor)
def cursor(func, self):
    result = func(self)
    logger = QueryLogger.get_current()
    return CursorWrapper(result, self, logger=logger)


def log_queries(prefix=None):
    """Decorator for logging queries performed during a function.
    """

    def inner(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            result = func(*args, **kwargs)

            logger = QueryLogger.get_current()
            func_name = prefix or func.__name__
            dump_queries(logger._queries, filename_prefix=func_name)

            return result
        return wrapped
    return inner
