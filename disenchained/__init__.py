"""Basic loading functions.
"""

import cPickle as pickle

from disenchained.query import Query


class DebugFile(object):
    def __init__(self, filename):
        with open(filename) as fp:
            obj = pickle.load(fp)
            self.info = obj['info']
            self.queries = map(Query, obj['queries'])
