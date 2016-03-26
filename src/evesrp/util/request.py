from __future__ import unicode_literals
from flask import Request


class AcceptRequest(Request):

    _json_mimetypes = ['application/json',]

    _html_mimetypes = ['text/html', 'application/xhtml+xml']

    _xml_mimetypes = ['application/xml', 'text/xml']

    _rss_mimetypes = ['application/rss+xml', 'application/rdf+xml']

    @property
    def _known_mimetypes(self):
        return self._html_mimetypes + \
               self._json_mimetypes + \
               self._xml_mimetypes + \
               self._rss_mimetypes

    @property
    def is_json(self):
        if 'fmt' in self.values:
            return self.values['fmt'] == 'json'
        return self.accept_mimetypes.best_match(self._known_mimetypes) in \
            self._json_mimetypes

    @property
    def is_xml(self):
        if 'fmt' in self.values:
            return self.values['fmt'] == 'xml'
        return self.accept_mimetypes.best_match(self._known_mimetypes) in \
            self._xml_mimetypes

    @property
    def is_rss(self):
        if self.path.endswith('rss.xml'):
            return True
        if 'fmt' in self.values:
            return self.values['fmt'] == 'rss'
        return self.accept_mimetypes.best_match(self._known_mimetypes) in \
            self._rss_mimetypes
