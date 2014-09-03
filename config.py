from binascii import unhexlify
from ecdsa import SigningKey, VerifyingKey, NIST256p
from hashlib import sha256


def hex2key(hex_key):
    """Convert hex representations of keys to the actual key objects."""
    key_bytes = unhexlify(hex_key)
    if len(hex_key) == 64:
        return SigningKey.from_string(key_bytes, curve=NIST256p,
                hashfunc=sha256)
    elif len(hex_key) == 128:
        return VerifyingKey.from_string(key_bytes, curve=NIST256p,
                hashfunc=sha256)
    else:
        raise ValueError("Key in hex form is of the wrong length.")


DEBUG = True

SQLALCHEMY_ECHO = False

SRP_USER_AGENT_EMAIL = u'paxswill@paxswill.com'

SQLALCHEMY_DATABASE_URI = 'postgres://localhost:5432/evesrp'

# Object instances are specified as dictionaries with a 'type' key. All other
# keys are passed as keyword arguments to the initializer for that type.
SRP_AUTH_METHODS = [
    {
        'type': 'evesrp.auth.testoauth.TestOAuth',
        'admins': [u'paxswill'],
        'name': 'Test Auth',
        'key': 'consumer_key_here',
        'secret': 'consumer_secret_here',
    },
    {
        'type': 'evesrp.auth.bravecore.BraveCore',
        'client_key': hex2key('client_key_here'),
        'server_key': hex2key('server_key_here'),
        'identifier': 'core_app_id_here',
    },
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
