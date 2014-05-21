#!/usr/bin/env python
from evesrp import create_app
from evesrp.killmail import CRESTMail, ZKillmail
from evesrp.transformers import ShipTransformer, PilotTransformer
from evesrp.auth.testauth import TestAuth
from evesrp.auth.bravecore import BraveCore
from os import environ as env
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


def configure_app(app, config):
    app.config['USER_AGENT_EMAIL'] = 'paxswill@paxswill.com'
    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DATABASE_URL',
            'sqlite:///')
    app.config['AUTH_METHODS'] = [TestAuth(admins=['paxswill',]), ]
    app.config['KILLMAIL_SOURCES'] = [
            TestZKillboard,
    ]
    app.config['SRP_SHIP_URL_TRANSFORMERS'] = [
        ShipTransformer('TEST Reimbursement Wiki',
            'https://wiki.pleaseignore.com/wiki/Reimbursement:{name}'),
    ]
    app.config['SRP_PILOT_URL_TRANSFORMERS'] = [
        PilotTransformer('TEST Auth page',
            'https://auth.pleaseignore.com/eve/character/{id_}/'),
    ]

    # Configure Brave Core if all the needed things are there
    try:
        core_private_key = hex2key(config['CORE_AUTH_PRIVATE_KEY'])
        core_public_key = hex2key(config['CORE_AUTH_PUBLIC_KEY'])
        core_identifier = config['CORE_AUTH_IDENTIFIER']
    except KeyError:
        pass
    else:
        app.config['AUTH_METHODS'].append(BraveCore(core_private_key,
                core_public_key, core_identifier))

    if config.get('DEBUG') is not None:
        app.debug = True
        if config.get('SQLALCHEMY_ECHO') is not None:
            app.config['SQLALCHEMY_ECHO'] = True

    secret_key = config.get('SECRET_KEY')
    if secret_key is not None:
        app.config['SECRET_KEY'] = unhexlify(secret_key)



app = create_app()
configure_app(app, env)


if __name__ == '__main__':
    # So we get the database tables for these
    from evesrp.auth.testauth import TestUser, TestGroup
    from evesrp.auth.bravecore import CoreUser, CoreGroup
    print("Creating databases...")
    app.extensions['sqlalchemy'].db.create_all(app=app)
