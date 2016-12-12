import datetime as dt
from decimal import Decimal
import enum

from . import util
from ..util import classproperty


class Pilot(util.IdEquality):

    def __init__(self, name, id_, **kwargs):
        self.name = name
        self.id_ = id_
        self.user_id = util.id_from_kwargs('user', kwargs)

    @classmethod
    def from_dict(cls, pilot_dict):
        return cls(pilot_dict['name'],
                   pilot_dict['id'],
                   user_id=pilot_dict['user_id'])

    def get_user(self, store):
        return store.get_user(self.user_id)


class Killmail(util.IdEquality):

    def __init__(self, id_, **kwargs):
        self.id_ = id_
        self.user_id = util.id_from_kwargs('user', kwargs)
        self.pilot_id = kwargs['pilot_id']
        self.corporation_id = kwargs['corporation_id']
        # Alliance is optional, as corps aren't required to be in an alliance.
        # dict.get returns None if the key doesn't exist.
        self.alliance_id = kwargs.get('alliance_id')
        self.system_id = kwargs['system_id']
        self.constellation_id = kwargs['constellation_id']
        self.region_id = kwargs['region_id']
        self.type_id = kwargs['type_id']
        self.timestamp = kwargs['timestamp']

    @classmethod
    def from_dict(cls, killmail_dict):
        return cls(killmail_dict['id'],
                   user_id=killmail_dict['user_id'],
                   pilot_id=killmail_dict['pilot_id'],
                   corporation_id=killmail_dict['corporation_id'],
                   # Again, using dict.get to allow for null alliances
                   alliance_id=killmail_dict.get('alliance_id'),
                   system_id=killmail_dict['system_id'],
                   constellation_id=killmail_dict['constellation_id'],
                   region_id=killmail_dict['region_id'],
                   type_id=killmail_dict['type_id'],
                   # Allow either an ISO8601 date and time string, or a Python
                   # datetime object
                   timestamp=util.parse_timestamp(killmail_dict['timestamp']))

    def get_user(self, store):
        return store.get_user(user_id=self.user_id)

    def get_pilot(self, store):
        return store.get_pilot(pilot_id=self.pilot_id)

    def get_requests(self, store):
        return store.get_requests(killmail_id=self.id_)


class ActionType(enum.Enum):

    evaluating = 1

    approved = 2

    paid = 3

    rejected = 4

    incomplete = 5

    comment = 6

    @classproperty
    def finalized(cls):
        return frozenset((cls.paid, cls.rejected))

    @classproperty
    def pending(cls):
        return frozenset((cls.evaluating, cls.approved, cls.incomplete))

    @classmethod
    def statuses(cls):
        return frozenset((cls.evaluating, cls.approved, cls.paid, cls.rejected,
                          cls.incomplete))


class Request(util.IdEquality):

    def __init__(self, id_, timestamp=None, base_payout=0,
                 status=ActionType.evaluating, payout=None, **kwargs):
        self.id_ = id_
        self.killmail_id = util.id_from_kwargs('killmail', kwargs)
        self.division_id = util.id_from_kwargs('division', kwargs)
        # Default to the current time if no timestamp is given
        if timestamp is None:
            timestamp = dt.datetime.utcnow()
        self.timestamp = timestamp
        self.status = status
        # force base_payout and payout to be Decimals
        if not isinstance(base_payout, Decimal):
            base_payout = Decimal(base_payout)
        self.base_payout = base_payout
        if payout is None:
            payout = base_payout
        elif not isinstance(payout, Decimal):
            payout = Decimal(payout)
        self.payout = payout

    @classmethod
    def from_dict(cls, request_dict):
        return cls(request_dict['id'],
                   killmail_id=request_dict['killmail_id'],
                   division_id=request_dict['division_id'],
                   payout=Decimal(request_dict['payout']),
                   base_payout=Decimal(request_dict['base_payout']),
                   timestamp=util.parse_timestamp(request_dict['timestamp']),
                   status=ActionType[request_dict['status']])

    def get_actions(self, store):
        return store.get_actions(request_id=self.id_)

    def get_modifiers(self, store, void=None, type_=None):
        get_kwargs = {'request_id': self.id_}
        if void is not None:
            get_kwargs['void'] = void
        if type_ is not None:
            get_kwargs['type_'] = type_
        return store.get_modifiers(**get_kwargs)

    def get_division(self, store):
        return store.get_division(division_id=self.division_id)

    def get_killmail(self, store):
        return store.get_killmail(killmail_id=self.killmail_id)

    def current_status(self, store):
        actions = self.get_actions(store)
        for action in reversed(actions):
            if action.type_ != ActionType.comment:
                return action.type_
        return self.status

    def current_payout(self, store):
        # current payout is defined as
        # (base_payout + sum(absolute)) * (1 + sum(relative))
        # absolute being all non-void absolute modifiers' values and relative
        # the same for relative modifiers
        absolute_modifiers = self.get_modifiers(store,void=False,
                                                type_=ModifierType.absolute)
        # When an empty iterable is given to sum(), it returns 0, which is an
        # exact value (an int) for Decimal, so no need to worry about
        # inaccuracies there.
        absolute = sum([m.value for m in absolute_modifiers])
        relative_modifiers = self.get_modifiers(store,void=False,
                                                type_=ModifierType.relative)
        relative = sum([m.value for m in relative_modifiers])
        return (self.base_payout + absolute) * (Decimal(1) + relative)


class Action(util.IdEquality):

    def __init__(self, id_, type_, timestamp=None, contents='', **kwargs):
        self.id_ = id_
        self.type_ = type_
        # Default to the current time if no timestamp is given
        if timestamp is None:
            timestamp = dt.datetime.utcnow()
        self.timestamp = timestamp
        self.contents = contents
        self.request_id = util.id_from_kwargs('request', kwargs)
        self.user_id = util.id_from_kwargs('user', kwargs)

    @classmethod
    def from_dict(cls, action_dict):
        return cls(action_dict['id'],
                   ActionType[action_dict['type']],
                   timestamp=util.parse_timestamp(action_dict['timestamp']),
                   contents=action_dict['contents'],
                   user_id=action_dict['user_id'],
                   request_id=action_dict['request_id'])


class ModifierType(enum.Enum):

    relative = 1

    absolute = 2


class Modifier(util.IdEquality):

    def __init__(self, id_, type_, value, timestamp=None, **kwargs):
        self.id_ = id_
        self.type_ = type_
        if not isinstance(value, Decimal):
            value = Decimal(value)
        self.value = value
        self.user_id = util.id_from_kwargs('user', kwargs)
        self.request_id = util.id_from_kwargs('request', kwargs)
        # Default to the current time if no timestamp is given
        if timestamp is None:
            timestamp = dt.datetime.utcnow()
        self.timestamp = timestamp
        self.void_timestamp = None
        self.void_user_id = None

    @classmethod
    def from_dict(cls, modifier_dict):
        modifier = cls(modifier_dict['id'],
                       ModifierType[modifier_dict['type']],
                       Decimal(modifier_dict['value']),
                       timestamp=util.parse_timestamp(
                           modifier_dict['timestamp']),
                       user_id=modifier_dict['user_id'],
                       request_id=modifier_dict['request_id'])
        # 'void' should be present, but just in case, let's get() it to swallow
        # KeyErrors
        if modifier_dict.get('void') is not None:
            modifier.void(user_id=modifier_dict['void']['user_id'],
                          timestamp=util.parse_timestamp(
                              modifier_dict['void']['timestamp']))
        return modifier

    @property
    def is_void(self):
        return self.void_timestamp is not None and \
               self.void_user_id is not None

    def void(self, timestamp=None, **kwargs):
        self.void_user_id = util.id_from_kwargs('user', kwargs)
        if timestamp is None:
            timestamp = dt.datetime.utcnow()
        self.void_timestamp = timestamp
