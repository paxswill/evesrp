class Config(object):
    DEBUG = False
    CSRF_ENABLE = True
    SECRET_KEY = 'foobarbaz'
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

class Development(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///development.sqlite3'

