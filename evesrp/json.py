from __future__ import absolute_import
from flask import url_for
from flask.json import JSONEncoder
import six
from .models import Request, Action, Modifier
from .auth.models import User, Group, Division, APIKey

if six.PY3:
    unicode = str


class IterableEncoder(JSONEncoder):
    def default(self, o):
        try:
            iterator = iter(o)
        except TypeError:
            pass
        else:
            return list(o)
        return super(IterableEncoder, self).default(o)


class NamedEncoder(JSONEncoder):
    def default(self, o):
        try:
            ret = {
                u'name': o.name,
                u'id': o.id,
            }
        except AttributeError:
            pass
        else:
            if isinstance(o, User):
                ret[u'href'] = url_for('api.user_detail', user_id=o.id)
            elif isinstance(o, Group):
                ret[u'href'] = url_for('api.group_detail', group_id=o.id)
            elif isinstance(o, Division):
                ret[u'href'] = url_for('api.division_detail', division_id=o.id)
            if u'href' in ret:
                return ret
        return super(NamedEncoder, self).default(o)


class GrabbagEncoder(JSONEncoder):
    def default(self, o):
        try:
            ret = {'id': o.id}
        except AttributeError:
            pass
        else:
            if isinstance(o, Request):
                ret[u'href'] = url_for('requests.get_request_details',
                        request_id=o.id)
                attrs = (u'killmail_url', u'kill_timestamp', u'pilot',
                         u'alliance', u'corporation', u'submitter',
                         u'division', u'status', u'base_payout', u'payout',
                         u'details', u'id', u'ship_type', u'system',)
                for attr in attrs:
                    if attr == u'pilot':
                        ret[attr] = str(o.pilot)
                    elif attr == u'status':
                        ret[attr] = o.status.value
                    elif attr == u'ship_type':
                        ret['ship'] = o.ship_type
                    elif u'payout' in attr:
                        payout = getattr(o, attr)
                        ret[attr] = payout.currency(commas=False)
                        ret[attr + '_str'] = payout.currency()
                    else:
                        ret[attr] = getattr(o, attr)
                ret[u'submit_timestamp'] = o.timestamp
                return ret
            elif isinstance(o, Action):
                ret[u'note'] = o.note or u''
                ret[u'timestamp'] = o.timestamp
                ret[u'user'] = o.user
                ret[u'type'] = o.type_.value
                return ret
            elif isinstance(o, Modifier):
                ret[u'user'] = o.user
                ret[u'timestamp'] = o.timestamp
                ret[u'note'] = o.note or u''
                if o.voided:
                    ret[u'void'] = {
                            u'user': o.voided_user,
                            u'timestamp': o.voided_timestamp,
                    }
                else:
                    ret[u'void'] = False
                if hasattr(o.value, 'currency'):
                    ret[u'value'] = o.value.currency(commas=False)
                else:
                    ret[u'value'] = o.value
                ret[u'value_str'] = unicode(o)
                return ret
            elif isinstance(o, APIKey):
                ret[u'key'] = o.hex_key
                ret[u'timestamp'] = o.timestamp
                return ret
        return super(GrabbagEncoder, self).default(o)


# Multiple inheritance FTW
class SRPEncoder(IterableEncoder, NamedEncoder, GrabbagEncoder):
    pass
