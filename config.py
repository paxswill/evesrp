from evesrp.killmail import CRESTMail, ZKillmail
from evesrp.auth.testauth import TestAuth
from evesrp.auth.bravecore import BraveCore


class TestZKillboard(ZKillmail):
    def __init__(self, *args, **kwargs):
        super(TestZKillboard, self).__init__(*args, **kwargs)
        if self.domain not in ('zkb.pleaseignore.com', 'kb.pleaseignore.com'):
            raise ValueError(u"This killmail is from the wrong killboard")

    @property
    def value(self):
        return 0


DEBUG = True

SQLALCHEMY_ECHO = False

SRP_USER_AGENT_EMAIL = u'paxswill@paxswill.com'

SQLALCHEMY_DATABASE_URI = 'postgres://localhost:5432/evesrp'

SRP_AUTH_METHODS = [
        TestAuth(admins=[u'paxswill',]),
]

SRP_KILLMAIL_SOURCES = [
        TestZKillboard,
]

# Transformers can be specified as 2-tuples of the name and slug...
SRP_SHIP_TYPE_URL_TRANSFORMERS = [
    (u'TEST Reimbursement Wiki',
        'https://wiki.pleaseignore.com/wiki/Reimbursement:{}'),
]

# ...or, like other object instances in the config file, as a dictionary.
SRP_PILOT_URL_TRANSFORMERS = [
    {
        'type': 'evesrp.transformers.Transformer',
        'name': u'TEST Auth page',
        'slug': 'https://auth.pleaseignore.com/eve/character/{0.id}/',
    },
]
