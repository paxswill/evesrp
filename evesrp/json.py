from flask import url_for
from flask.json import JSONEncoder
from .models import Request, Action, Modifier
from .auth.models import User, Group, Division, APIKey


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
                'name': o.name,
                'id': o.id,
            }
        except AttributeError:
            pass
        else:
            if isinstance(o, User):
                ret['href'] = url_for('api.user_detail', user_id=o.id)
            elif isinstance(o, Group):
                ret['href'] = url_for('api.group_detail', group_id=o.id)
            elif isinstance(o, Division):
                ret['href'] = url_for('api.division_detail', division_id=o.id)
            if 'href' in ret:
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
                ret['href'] = url_for('requests.get_request_details',
                        request_id=o.id)
                attrs = ('killmail_url', 'kill_timestamp', 'pilot', 'alliance',
                    'corporation', 'submitter', 'division', 'status',
                    'base_payout', 'payout', 'details', 'id')
                for attr in attrs:
                    if attr == 'pilot':
                        ret[attr] = str(o.pilot)
                    elif attr == 'status':
                        ret[attr] = o.status.value
                    elif 'payout' in attr:
                        payout = getattr(o, attr)
                        ret[attr] = payout.currency(commas=False)
                        ret[attr + '_str'] = payout.currency()
                    else:
                        ret[attr] = getattr(o, attr)
                ret['submit_timestamp'] = o.timestamp
                return ret
            elif isinstance(o, Action):
                ret['note'] = o.note or ''
                ret['timestamp'] = o.timestamp
                ret['user'] = o.user
                ret['type'] = o.type_.value
                return ret
            elif isinstance(o, Modifier):
                ret['user'] = o.user
                ret['timestamp'] = o.timestamp
                ret['note'] = o.note or ''
                if o.voided:
                    ret['void'] = {
                            'user': o.voided_user,
                            'timestamp': o.voided_timestamp,
                    }
                else:
                    ret['void'] = False
                if hasattr(o.value, 'currency'):
                    ret['value'] = o.value.currency(commas=False)
                else:
                    ret['value'] = o.value
                ret['value_str'] = str(o)
                return ret
            elif isinstance(o, APIKey):
                ret['key'] = o.hex_key
                ret['timestamp'] = o.timestamp
                return ret
        return super(GrabbagEncoder, self).default(o)


# Multiple inheritance FTW
class SRPEncoder(IterableEncoder, NamedEncoder, GrabbagEncoder):
    pass
