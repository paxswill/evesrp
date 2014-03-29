class Config(object):
    DEBUG = False
    CSRF_ENABLE = True
    SECRET_KEY = 'foobarbaz'
    AUTH_METHODS = ['evesrp.auth.testauth.TestAuth']
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

class Development(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///development.sqlite3'
    AUTH_METHODS = [
            'evesrp.auth.testauth.TestAuth',
            'evesrp.auth.bravecore.BraveCore',
            ]
    CORE_AUTH_PRIVATE_KEY = 'client.private.pem'
    CORE_AUTH_PUBLIC_KEY = 'server.public.pem'
    CORE_AUTH_IDENTIFIER = 'EVE SRP'

