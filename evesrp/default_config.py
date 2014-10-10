from __future__ import absolute_import
from __future__ import unicode_literals
from .killmail import CRESTMail, ZKillmail

CSRF_ENABLE = True

# This really needs to be set to something
SRP_AUTH_METHODS = []

# Default database is an in-memory SQLite DB.
SQLALCHEMY_DATABASE_URI = 'sqlite://'

# CREST killmails don't have any external dependencies
SRP_KILLMAIL_SOURCES = [ZKillmail, CRESTMail]

SRP_SITE_NAME = 'EVE-SRP'

SRP_DETAILS_DESCRIPTION = 'Supporting details about your loss.'

SRP_SKIP_VALIDATION = False

# Add a hash of the files contents to the filename (useful for working around
# caching issues).
SRP_STATIC_FILE_HASH = False
