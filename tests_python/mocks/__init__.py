from __future__ import absolute_import

from .rest_service import RESTService


crest = RESTService(r'(.*\.)?crest-tq\.eveonline\.com$')
zKillboard = RESTService(r'(.*\.)?zkillboard\.com$')
