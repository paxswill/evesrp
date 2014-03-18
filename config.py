class Config(object):
    DEBUG = False
    CSRF_ENABLE = True
    SECRET_KEY = 'foobarbaz'


class Developement(Config):
    DEBUG = True

