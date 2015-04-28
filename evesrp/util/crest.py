from flask import flash


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
