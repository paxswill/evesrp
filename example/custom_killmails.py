from evesrp.killmail import CRESTMail, ZKillmail
from flask import Markup, current_app
from decimal import Decimal


class ZeroValueZKillboard(ZKillmail):

    @property
    def value(self):
        return 0


class ZeroValueSubmittedCRESTZKillmail(CRESTMail):
    """Accepts and validates CREST killmail links, but submits them to
    ZKillboard and substitutes the zKB link in as the canonical link
    """

    def __init__(self, url, **kwargs):
        # Let CRESTMail validate the CREST link
        super(self.__class__, self).__init__(url, **kwargs)
        # Submit the CREST URL to ZKillboard
        resp = self.requests_session.post('https://zkillboard.com/post/',
                data={'killmailurl': url})
        # Use the URL we get from ZKillboard as the new URL (if valid)
        if 'post' not in resp.url:
            self.url = resp.url

    description = Markup(u'A CREST external killmail link that will be '
                         u'automatically submitted to <a href="https://'
                         u'zkillboard.com">zKillboard.com</a>.')
