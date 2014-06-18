#!/usr/bin/env python
from evesrp import create_app
from evesrp.auth.testauth import TestAuth
from evesrp.auth.bravecore import BraveCore
import os
import os.path
from binascii import unhexlify
from ecdsa import SigningKey, VerifyingKey, NIST256p
from hashlib import sha256


class TestZKillboard(ZKillmail):
    def __init__(self, *args, **kwargs):
        super(TestZKillboard, self).__init__(*args, **kwargs)
        if self.domain not in ('zkb.pleaseignore.com', 'kb.pleaseignore.com'):
            raise ValueError("This killmail is from the wrong killboard")

    @property
    def value(self):
        return 0


def hex2key(hex_key):
    key_bytes = unhexlify(hex_key)
    if len(hex_key) == 64:
        return SigningKey.from_string(key_bytes, curve=NIST256p,
                hashfunc=sha256)
    elif len(hex_key) == 128:
        return VerifyingKey.from_string(key_bytes, curve=NIST256p,
                hashfunc=sha256)
    else:
        raise ValueError("Key in hex form is of the wrong length.")


def configure_from_env(app):
    # Configure Brave Core if all the needed things are there
    try:
        core_private_key = hex2key(environ['CORE_AUTH_PRIVATE_KEY'])
        core_public_key = hex2key(environ['CORE_AUTH_PUBLIC_KEY'])
        core_identifier = environ['CORE_AUTH_IDENTIFIER']
    except KeyError:
        pass
    else:
        app.config['AUTH_METHODS'].append(BraveCore(core_private_key,
                core_public_key, core_identifier))

    secret_key = environ.get('SECRET_KEY')
    if secret_key is not None:
        app.config['SECRET_KEY'] = unhexlify(secret_key)


config_path = os.path.join(os.path.abspath(os.getcwd()), 'config.py')
app = create_app(config_path)
configure_from_env(app)


if __name__ == '__main__':
    # So we get the database tables for these
    from evesrp.auth.testauth import TestUser, TestGroup
    from evesrp.auth.bravecore import CoreUser, CoreGroup
    print("Creating databases...")
    app.extensions['sqlalchemy'].db.create_all(app=app)
