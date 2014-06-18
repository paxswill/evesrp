from evesrp.killmail import CRESTMail, ZKillmail
from evesrp.transformers import ShipTransformer, PilotTransformer
from evesrp.auth.testauth import TestAuth
from evesrp.auth.bravecore import BraveCore


class TestZKillboard(ZKillmail):
    def __init__(self, *args, **kwargs):
        super(TestZKillboard, self).__init__(*args, **kwargs)
        if self.domain not in ('zkb.pleaseignore.com', 'kb.pleaseignore.com'):
            raise ValueError("This killmail is from the wrong killboard")

    @property
    def value(self):
        return 0


DEBUG = True

SQLALCHEMY_ECHO = False

USER_AGENT_EMAIL = 'paxswill@paxswill.com'

SQLALCHEMY_DATABASE_URI = 'postgres://localhost:5432/evesrp'

AUTH_METHODS = [
        TestAuth(admins=['paxswill',]),
]

KILLMAIL_SOURCES = [
        TestZKillboard,
]

SRP_SHIP_URL_TRANSFORMERS = [
    ShipTransformer('TEST Reimbursement Wiki',
        'https://wiki.pleaseignore.com/wiki/Reimbursement:{name}'),
]

SRP_PILOT_URL_TRANSFORMERS = [
    PilotTransformer('TEST Auth page',
        'https://auth.pleaseignore.com/eve/character/{id_}/'),
]
