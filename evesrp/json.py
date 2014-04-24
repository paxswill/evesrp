from flask import url_for
from flask.json import JSONEncoder
from .models import Request
from .auth.models import User, Group, Division


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
            done = False
            if isinstance(o, Request):
                ret['href'] = url_for('api.request_detail', request_id=o.id)
                return ret
        return super(GrabbagEncoder, self).default(o)


# Multiple inheritance FTW
class SRPEncoder(IterableEncoder, NamedEncoder, GrabbagEncoder):
    pass
