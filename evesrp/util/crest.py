from flask import flash, current_app


def check_crest_response(response):
    """Check for CREST representation deprecation/removal.

    Specifically, check that the status code isn't 406 (meaning the
    representation has been removed) and for the presence of the X-Deprecated
    header.

    :param Response response: A :py:class:`~.Response` to check.
    :rtype: bool
    """
    # TODO Add a test case for this
    if response.status_code == 406:
        flash((u"This version of EVE SRP no longer knows how to interface with"
               u"the CREST API. Please update to the latest version."),
               u'error')
        return False
    if 'X-Deprecated' in response.headers:
        flash((u"The version of the CREST representation known by EVE SRP "
               u"has been deprecated. Please update to the latest version "
               u"to ensure continued operation."), u'warn')
    return True


class NameLookup(object):

    def __init__(self, starting_data, url_slug, content_type):
        self._dict = starting_data
        self.url_slug = url_slug
        self.content_type = content_type


    def __getitem__(self, key):
        if not isinstance(key, int):
            raise TypeError("Invalid ID for name lookup: '{}'".\
                    format(key))
        if key not in self._dict:
            resp = current_app.requests_session.get(
                    self.url_slug.format(key),
                    headers={'Accept': self.content_type})
            if check_crest_response(resp) and resp.status_code == 200:
                self._dict[key] = resp.json()['name']
            else:
                message = "Cannot find the name for the ID requested [{}]: {}"\
                        .format(resp.status_code, key)
                raise KeyError(message)
        return self._dict[key]
