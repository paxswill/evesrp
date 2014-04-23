from evesrp.auth.testauth import TestAuth
from evesrp.auth.bravecore import BraveCore

class Config(object):
    DEBUG = False
    CSRF_ENABLE = True
    SECRET_KEY = 'foobarbaz'
    AUTH_METHODS = [TestAuth()]
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

class Development(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///development.sqlite3'
    AUTH_METHODS = [
            TestAuth(),
            BraveCore(),
            ]
    CORE_AUTH_PRIVATE_KEY = 'client.private.pem'
    CORE_AUTH_PUBLIC_KEY = 'server.public.pem'
    CORE_AUTH_IDENTIFIER = 'EVE SRP'

