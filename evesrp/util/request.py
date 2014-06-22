from flask import Request


class AcceptRequest(Request):

    _json_mimetypes = ['application/json',]

    _html_mimetypes = ['text/html', 'application/xhtml+xml']

    @property
    def _known_mimetypes(self):
        return self._json_mimetypes + self._html_mimetypes

    @property
    def wants_json(self):
        return self.accept_mimetypes.best_match(self._known_mimetypes) in \
            self._json_mimetypes

    @property
    def wants_html(self):
        return self.accept_mimetypes.best_match(self._known_mimetypes) in \
            self._html_mimetypes
