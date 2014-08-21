from evesrp.auth.testauth import TestAuth
from evesrp.auth.bravecore import BraveCore


DEBUG = True

SQLALCHEMY_ECHO = False

SRP_USER_AGENT_EMAIL = u'paxswill@paxswill.com'

SQLALCHEMY_DATABASE_URI = 'postgres://localhost:5432/evesrp'

SRP_AUTH_METHODS = [
        TestAuth(admins=[u'paxswill',]),
]

# Killmail sources are a string with the import path to a type.
# Custom killmail handers can be put in the instance folder or next to the
# app's definition file.
SRP_KILLMAIL_SOURCES = [
    'custom_killmails.TestZKillboard',
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
