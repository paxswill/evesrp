from .killmail import CRESTMail, ZKillmail

CSRF_ENABLE = True

# This really needs to be set to something
AUTH_METHODS = []

# Default database is an in-memory SQLite DB.
SQLALCHEMY_DATABASE_URI = 'sqlite://'

# CREST killmails don't have any external dependencies
KILLMAIL_SOURCES = [ZKillmail, CRESTMail]
