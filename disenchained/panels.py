import cPickle as pickle
import os
import os.path
import time

from django.conf import settings
from django.core.urlresolvers import resolve
from django.utils.translation import ugettext_lazy as _

from debug_toolbar.middleware import DebugToolbarMiddleware
from debug_toolbar.panels.sql import DebugPanel
from debug_toolbar.panels.sql import SQLDebugPanel


def dump_queries(queries, request=None, filename_prefix=None):
    data = {'info': {}, 'queries': queries}

    if request:
        view_info = resolve(request.path)
        if not filename_prefix:
            filename_prefix = view_info.view_name.replace(':', '__')

        data['info'].update({
            'sessionid': request.COOKIES.get('sessionid', ''),
            'url_name': view_info.url_name,
            'app_name': view_info.app_name,
            'view_name': view_info.view_name,
            'func_name': view_info.func.__name__,
            'func_args': view_info.args,
            'func_kwargs': view_info.kwargs})
    else:
        filename_prefix = filename_prefix or "unknown"

    datadir = getattr(settings, 'DISENCHAINED_DATA_DIRECTORY', None)
    if datadir:
        if not os.path.exists(datadir):
            os.makedirs(datadir)

        filename = "%s.%s.pickle" % (
            filename_prefix,
            str(time.time()).replace('.', '')
        )
        datafile = "%s/%s" % (datadir, filename)
        with open(datafile, 'w') as fp:
            pickle.dump(data, fp)
    else:
        RuntimeError("No `DISENCHAINED_DATA_DIRECTORY` specified.")

    return datafile


class DisenchainedPanel(DebugPanel):
    """Disenchained debug panel that dumps query log to a file.
    """
    name = 'Disenchained'
    title = 'Django Disenchained'
    has_content = True

    def process_response(self, request, response):
        middleware = DebugToolbarMiddleware.get_current()
        self.sql_panel = middleware.get_panel(SQLDebugPanel)

        if self.sql_panel._queries:
            self.datafile = dump_queries(self.sql_panel._queries, request)

        super(DisenchainedPanel, self).process_response(request, response)

    def nav_title(self):
        return _(self.name)

    def nav_subtitle(self):
        return ''

    def url(self):
        return ''

    def content(self):
        return "Debug data stored in file <b>%s</b>" % self.datafile
