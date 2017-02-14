from collections import defaultdict
import datetime as dt
import decimal
import itertools
import copy
import six
import iso8601
import evesrp
from evesrp import new_models as models


class InvalidFilterKeyError(ValueError):

    def __init__(self, key):
        self.key = key
        error_msg = u"'{}' is not a valid filter attribute.".format(self.key)
        super(InvalidFilterKeyError, self).__init__(error_msg)


class InvalidFilterValueError(ValueError):

    def __init__(self, key, value):
        self.key = key
        self.value = value
        error_msg = u"Value '{}' is not valid for attribute '{}'.".format(
            self.value, self.key)
        super(InvalidFilterValueError, self).__init__(error_msg)


integer_text_types = tuple(itertools.chain(six.integer_types, (six.text_type,)))


class Filter(object):

    def __init__(self, filter_source=None, filter_immutable=True):
        self._immutable = filter_immutable
        if filter_source is not None:
            self._filters = copy.deepcopy(filter_source._filters)
        else:
            self._filters = defaultdict(set)

    def __len__(self):
        return len(self._filters)

    def __iter__(self):
        return six.iteritems({key: frozenset(values) for key, values in
                              six.iteritems(self._filters)})

    def __contains__(self, item):
        return item in self._filters

    def __getitem__(self, key):
        if key not in self._all_keys:
            raise KeyError(key)
        return frozenset(self._filters[key])

    def __eq__(self, other):
        # NOTE: Equality does not check for immutability!
        return self._filters == other._filters

    def __repr__(self):
        filters_repr = dict.__repr__(self._filters)
        return "Filter({})".format(filters_repr)

    def add(self, **kwargs):
        # Copy ourselves if we're immutable
        if self._immutable:
            work_filter = self.__class__(filter_source=self)
        else:
            work_filter = self
        for key, value in self._check_predicates(**kwargs):
            work_filter._filters[key].add(value)
        return work_filter

    def remove(self, **kwargs):
        # Again, create a new filter if we're immutable
        if self._immutable:
            work_filter = self.__class__(filter_source=self)
        else:
            work_filter = self
        for key, value in self._check_predicates(**kwargs):
            work_filter._filters[key].discard(value)
            if len(work_filter._filters[key]) == 0:
                del work_filter._filters[key]
        return work_filter

    def merge(self, other_filter):
        # if other_filter is None or empty, this is a noop
        if other_filter is None or len(other_filter) == 0:
            return self
        if self._immutable:
            work_filter = self.__class__(filter_source=self)
        else:
            work_filter = self
        for key, values in other_filter:
            work_filter._filters[key].update(values)
        return work_filter

    _int_keys = {'division', 'user'}

    _ccp_keys = {'type', 'pilot', 'region', 'constellation', 'system'}

    _timestamp_keys = {'submit_timestamp', 'kill_timestamp'}

    _decimal_keys = {'payout', 'base_payout'}

    _text_keys = {'details',}

    _all_keys = frozenset(itertools.chain(_int_keys, _ccp_keys,
                                            _timestamp_keys, _decimal_keys,
                                            _text_keys, ('status',)))

    @classmethod
    def _check_predicates(cls, **kwargs):
        # This is the bulk of the logic in this class. Basically, each
        # attribute falls into one of a handful of classes:
        #    * Only allow integer ID numbers (for predicates referring to items
        #      in this app's database).
        #    * Allow either text types (str for Py3, unicode for Py2) or an
        #      integer ID number (for predicates referring to CCP items).
        #    * Only allow values that can be converted to a Decimal.
        #    * Only allow values that refer to a request's status.
        #    * Anything textual goes (for filtering on details, aka a full text
        #      search).
        # From there, type checking is enforced and exceptions raised. Instead
        # of returning, this function is a generator so it can process all of
        # the keyword arguments in one pass.
        for key, value in six.iteritems(kwargs):
            if key in cls._int_keys:
                if not isinstance(value, six.integer_types):
                    raise InvalidFilterValueError(key, value)
                yield key, value
            # TODO: Add alliance and corporation
            elif key in cls._ccp_keys:
                # Must be a string name, or a CCP ID.
                if not isinstance(value, integer_text_types):
                    raise InvalidFilterValueError(key, value)
                yield key, value
            elif key in cls._timestamp_keys:
                # Must be a pair of datetimes, or a string parseable
                # with evesrp.util.datetime.parse_datetime
                if isinstance(value, tuple) and len(value) == 2:
                    if isinstance(value[0], dt.datetime) and \
                            isinstance(value[1], dt.datetime):
                        yield key, value
                elif isinstance(value, six.text_type):
                    try:
                        yield key, evesrp.util.parse_datetime(value)
                    except iso8601.ParseError:
                        raise InvalidFilterValueError(key, value)
                else:
                    raise InvalidFilterValueError(key, value)
            elif key in cls._decimal_keys:
                # Must be a Decimal, or some other type exactly convertable to
                # a Decimal.
                if not isinstance(value, decimal.Decimal):
                    try:
                        new_value = decimal.Decimal(value)
                    except decimal.InvalidOperation:
                        raise InvalidFilterValueError(key, value)
                else:
                    new_value = value
                yield key, new_value
            elif key == 'status':
                # Must be a string that is equal to one of the enum members for
                # ActionType. Alternatively, can be an ActionType member.
                if value in models.ActionType:
                    yield key, value
                    continue
                try:
                    status = models.ActionType[value]
                except KeyError:
                    raise InvalidFilterValueError(key, value)
                if status not in models.ActionType.statuses:
                    raise InvalidFilterValueError(key, value)
                yield key, status
            elif key in cls._text_keys:
                # Must be a string
                if not isinstance(value, six.text_type):
                    raise InvalidFilterValueError(key, value)
                yield key, value
            else:
                raise InvalidFilterKeyError(key)

