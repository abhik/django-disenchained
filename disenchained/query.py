"""Tools for analyzing query debug information.
"""

from collections import defaultdict
from collections import Counter
from collections import namedtuple
from collections import OrderedDict
import re


#
# Utils
#
def cleanup_sql(sql):
    return re.sub("SELECT (.*) FROM", "SELECT .. FROM", sql)


def key_func(key):
    if key is None:
        return lambda item: item
    if callable(key):
        return key
    return lambda item: getattr(item, key)


#
# Query
#
FunctionInfo = namedtuple("FunctionInfo", "file function")
Codeline = namedtuple("Codeline", "file function lineno")
TemplateInfo = namedtuple("TemplateInfo", "template lineno text")


class Query(object):
    def __init__(self, query_tuple):
        self.query = query_tuple[1]

    @property
    def stacktrace(self):
        return self.query['stacktrace']

    @property
    def file(self):
        return self.stacktrace[-1][0]

    @property
    def function(self):
        return FunctionInfo(self.file, self.stacktrace[-1][2])

    @property
    def codeline(self):
        func_info = self.function
        return Codeline(func_info.file,
                        func_info.function,
                        self.stacktrace[-1][1])

    @property
    def template(self):
        template_info = self.query['template_info']
        if template_info:
            lineno, line = [(tdict['num'], tdict['content'])
                            for tdict in template_info['context']
                            if tdict['highlight']][0]
            return TemplateInfo(template_info['name'],
                                lineno,
                                line.lstrip("\t "))
        return None

    @property
    def is_from_template(self):
        return bool(self.query['template_info'])

    @property
    def sql(self):
        return self.query['sql']

    @property
    def rawsql(self):
        return self.query['raw_sql']

    @property
    def sql_display(self):
        return cleanup_sql(self.sql)

    @property
    def rawsql_display(self):
        return cleanup_sql(self.rawsql)

    @property
    def duration(self):
        return self.query['duration']


#
# querylist functions
#
def where(queries, key, key_value):
    key = key_func(key)
    return filter(lambda query: key(query) == key_value, queries)


def most_common(queries, key, n=10):
    key = key_func(key)
    duration = lambda key_val: sum(
        map(key_func('duration'), where(queries, key, key_val)))

    return [
        {'key': key_val, 'count': count, 'duration': duration(key_val)}
        for key_val, count in Counter(map(key, queries)).most_common(n)]


def num_duplicates(queries, key):
    key = key_func(key)

    query_counts = defaultdict(int)
    for query in queries:
        query_counts[key(query)] += 1

    return sum(count - 1 for count in query_counts.itervalues() if count > 1)


def summary(queries):
    return OrderedDict([
        ('queries', len(queries)),
        ('duration', sum(query.duration for query in queries)),
        ('template queries', len(filter(lambda qq:qq.template, queries))),
        ('duplicate exact-sql', num_duplicates(queries, 'sql')),
        ('duplicate param-sql', num_duplicates(queries, 'rawsql'))])
