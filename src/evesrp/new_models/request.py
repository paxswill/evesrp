import datetime as dt
from decimal import Decimal
import enum

import six

from . import util
from ..util import classproperty


class Character(util.IdEquality):

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
        self.character_id = kwargs['character_id']
        self.corporation_id = kwargs['corporation_id']
        # Alliance is optional, as corps aren't required to be in an alliance.
        # dict.get returns None if the key doesn't exist.
        self.alliance_id = kwargs.get('alliance_id')
        self.system_id = kwargs['system_id']
        self.constellation_id = kwargs['constellation_id']
        self.region_id = kwargs['region_id']
        self.type_id = kwargs['type_id']
        self.timestamp = kwargs['timestamp']
        self.url = kwargs['url']

    @classmethod
    def from_dict(cls, killmail_dict):
        return cls(killmail_dict['id'],
                   user_id=killmail_dict['user_id'],
                   character_id=killmail_dict['character_id'],
                   corporation_id=killmail_dict['corporation_id'],
                   # Again, using dict.get to allow for null alliances
                   alliance_id=killmail_dict.get('alliance_id'),
                   system_id=killmail_dict['system_id'],
                   constellation_id=killmail_dict['constellation_id'],
                   region_id=killmail_dict['region_id'],
                   type_id=killmail_dict['type_id'],
                   # Allow either an ISO8601 date and time string, or a Python
                   # datetime object
                   timestamp=util.parse_timestamp(killmail_dict['timestamp']),
                   url=killmail_dict['url'])

    def get_user(self, store):
        return store.get_user(user_id=self.user_id)

    def get_character(self, store):
        return store.get_character(character_id=self.character_id)

    def get_requests(self, store):
        return store.get_requests(killmail_id=self.id_)


class ActionType(enum.Enum):

    evaluating = 1

    approved = 2

    paid = 3

    rejected = 4

    incomplete = 5

    comment = 6

    # TODO: split details changes out from evaluating

    @classproperty
    def finalized(cls):
        return frozenset((cls.paid, cls.rejected))

    @classproperty
    def updateable(cls):
        """Status where the request details can be updated."""
        return frozenset((cls.incomplete, cls.evaluating))

    @classproperty
    def pending(cls):
        return frozenset((cls.evaluating, cls.approved, cls.incomplete))

    @classproperty
    def statuses(cls):
        return frozenset((cls.evaluating, cls.approved, cls.paid, cls.rejected,
                          cls.incomplete))


class RequestStatusError(ValueError):
    """Error raised when the :py:class:`request <Request>` is in the wrong
    state to make a modification."""
    pass


class Request(util.IdEquality):

    # If you're adding a column/data field for Requests, make sure to update
    # Request.__init__ and Request.from_dict in addition to
    # BrowseActivity.columns.setter so you can get it out from searches. You
    # should also update test cases as well of course.

    def __init__(self, id_, details='', timestamp=None, base_payout=0,
                 status=ActionType.evaluating, payout=None, **kwargs):
        self.id_ = id_
        self.details = details
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
        status = request_dict['status']
        if isinstance(status, six.string_types):
            status = ActionType[status]
        return cls(request_dict['id'],
                   request_dict['details'],
                   killmail_id=request_dict['killmail_id'],
                   division_id=request_dict['division_id'],
                   payout=Decimal(request_dict['payout']),
                   base_payout=Decimal(request_dict['base_payout']),
                   timestamp=util.parse_timestamp(request_dict['timestamp']),
                   status=status)

    def get_actions(self, store):
        return store.get_actions(request_id=self.id_)

    state_rules = {
        ActionType.evaluating: frozenset((
            ActionType.evaluating,
            ActionType.incomplete,
            ActionType.rejected,
            ActionType.approved,
            ActionType.comment,
        )),
        ActionType.incomplete: frozenset((
            ActionType.rejected,
            ActionType.evaluating,
            ActionType.comment,
        )),
        ActionType.rejected: frozenset((
            ActionType.evaluating,
            ActionType.comment,
        )),
        ActionType.approved: frozenset((
            ActionType.evaluating,
            ActionType.paid,
            ActionType.comment,
        )),
        ActionType.paid: frozenset((
            ActionType.approved,
            ActionType.evaluating,
            ActionType.comment,
        )),
    }

    @classmethod
    def possible_actions(cls, status):
        return cls.state_rules[status]

    def add_action(self, store, type_, contents='', **kwargs):
        if type_ not in self.possible_actions(self.status):
            raise RequestStatusError(u"It is not possible for request {} to "
                                     u"change status to {} from {}.".format(
                                         self.id_, type_, self.status))
        user_id = util.id_from_kwargs('user', kwargs)
        action = store.add_action(self.id_, type_, user_id, contents)
        if action.type_ != ActionType.comment:
            self.status = action.type_
        store.save_request(self)
        return action

    def set_details(self, store, new_details, **kwargs):
        if self.status not in ActionType.updateable:
            raise RequestStatusError(u"Details can only be changed for "
                                     u"requests in evaluating or incomplete "
                                     u"states (Request #{} is {}).".format(
                                         self.id_, self.status))
        new_action = self.add_action(store,
                                     ActionType.evaluating,
                                     contents=self.details,
                                     request_id=self.id_, **kwargs)
        self.details = new_details
        store.save_request(self)
        return new_action

    def get_modifiers(self, store, void=None, type_=None):
        get_kwargs = {'request_id': self.id_}
        if void is not None:
            get_kwargs['void'] = void
        if type_ is not None:
            get_kwargs['type_'] = type_
        return store.get_modifiers(**get_kwargs)

    def add_modifier(self, store, type_, value, note=u'', **kwargs):
        if self.status != ActionType.evaluating:
            raise RequestStatusError(u"Request {} must be in the evaluating "
                                     u"state to add change its modifiers (it "
                                     u"is currently {}).".format(
                                         self.id_, self.status))
        user_id = util.id_from_kwargs('user', kwargs)
        modifier = store.add_modifier(self.id_, user_id, type_, value, note)
        self.payout = self.current_payout(store)
        store.save_request(self)
        return modifier

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
        absolute_modifiers = self.get_modifiers(store, void=False,
                                                type_=ModifierType.absolute)
        # When an empty iterable is given to sum(), it returns 0, which is an
        # exact value (an int) for Decimal, so no need to worry about
        # inaccuracies there.
        absolute = sum([m.value for m in absolute_modifiers])
        relative_modifiers = self.get_modifiers(store, void=False,
                                                type_=ModifierType.relative)
        relative = sum([m.value for m in relative_modifiers])
        return (self.base_payout + absolute) * (Decimal(1) + relative)

    def set_base_payout(self, store, new_payout):
        if self.status != ActionType.evaluating:
            raise RequestStatusError(u"Request {} must be in the evaluating "
                                     u"state to change its base "
                                     u"payout.".format(self.id_))
        if not isinstance(new_payout, Decimal):
            new_payout = Decimal(new_payout)
        self.payout = self.current_payout(store)
        store.save_request(self)


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
        type_ = action_dict['type']
        if isinstance(type_, six.string_types):
            type_ = ActionType[type_]
        return cls(action_dict['id'],
                   type_,
                   timestamp=util.parse_timestamp(action_dict['timestamp']),
                   contents=action_dict['contents'],
                   user_id=action_dict['user_id'],
                   request_id=action_dict['request_id'])


class ModifierType(enum.Enum):

    relative = 1

    absolute = 2


class Modifier(util.IdEquality):

    def __init__(self, id_, type_, value, note=u'', timestamp=None, **kwargs):
        self.id_ = id_
        self.type_ = type_
        if not isinstance(value, Decimal):
            value = Decimal(value)
        self.value = value
        self.note = note
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
        type_ = modifier_dict['type']
        if isinstance(type_, six.string_types):
            type_ = ModifierType[type_]
        modifier = cls(modifier_dict['id'],
                       type_,
                       Decimal(modifier_dict['value']),
                       note=modifier_dict.get('note', ''),
                       timestamp=util.parse_timestamp(
                           modifier_dict['timestamp']),
                       user_id=modifier_dict['user_id'],
                       request_id=modifier_dict['request_id'])
        # 'void' should be present, but just in case, let's get() it to swallow
        # KeyErrors
        voided = modifier_dict.get('void')
        if voided is not None:
            modifier.void_user_id = voided['user_id']
            modifier.void_timestamp = util.parse_timestamp(voided['timestamp'])
        return modifier

    @property
    def is_void(self):
        return self.void_timestamp is not None and \
            self.void_user_id is not None

    def void(self, store, **kwargs):
        srp_request = store.get_request(request_id=self.request_id)
        if srp_request.status != ActionType.evaluating:
            raise RequestStatusError(u"Request {} must be in the evaluating "
                                     u"state to change its modifiers (it "
                                     u"is currently {}).".format(
                                         srp_request.id_, srp_request.status))
        self.void_user_id = util.id_from_kwargs('user', kwargs)
        self.void_timestamp = store.void_modifier(self.id_, self.void_user_id)
        # Recalculate the payout and save it
        srp_request.payout = srp_request.current_payout(store)
        store.save_request(srp_request)
