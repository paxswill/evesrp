from collections import defaultdict
import datetime as dt
import decimal
import itertools
import functools

import six
import iso8601

import evesrp
from evesrp import new_models as models


class InvalidFilterKeyError(KeyError):

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


def check_filter_key(func):
    @functools.wraps(func)
    def key_check(*args, **kwargs):
        try:
            key = args[1]
        except IndexError:
            raise TypeError("{} requires at least a key".format(
                func.__name__))
        if key not in Filter._field_types:
            raise InvalidFilterKeyError(key)
        return func(*args, **kwargs)
    return key_check


class Filter(object):

    # _field_types is a local copy of the Request and Killmail field_types, but
    # with some special field names repacing shared field names. killmail_id is
    # not special-cased, as Request has it as a member.
    _field_types = {
        'request_id': models.FieldType.app_id,
        'request_timestamp': models.FieldType.datetime,
        'killmail_timestamp': models.FieldType.datetime,
    }
    _field_types.update(models.Killmail.field_types)
    _field_types.update(models.Request.field_types)
    del _field_types['id']
    del _field_types['timestamp']

    def __init__(self, initial_filters=None, **kwargs):
        self._filters = defaultdict(set)
        if initial_filters is not None:
            for field, values in six.iteritems(initial_filters):
                self.add(field, *values)
        for field, values in six.iteritems(kwargs):
            self.add(field, *values)

    def __len__(self):
        return len(self._filters)

    def __iter__(self):
        return six.iteritems({key: frozenset(values) for key, values in
                              six.iteritems(self._filters)})

    def __contains__(self, item):
        return item in self._filters

    @check_filter_key
    def __getitem__(self, key):
        if key not in self._field_types:
            raise InvalidFilterKeyError(key)
        return frozenset(self._filters[key])

    def __eq__(self, other):
        return self._filters == other._filters

    def __repr__(self):
        def set_repr(a_set):
            return "{{{}}}".format(", ".join(map(repr, a_set)))
        def dict_repr(a_dict):
            items = ["'{}': {}".format(key, set_repr(value)) for key, value in
                     six.iteritems(a_dict)]
            return "{{{}}}".format(", ".join(items))
        return "Filter({})".format(dict_repr(self._filters))

    @check_filter_key
    def add(self, key, *values):
        field_type = self._field_types[key]
        # putting checked values in a separate list to avoid a value part way
        # through aborting the process.
        checked_values = []
        for value in values:
            if field_type == models.FieldType.decimal:
                if not isinstance(value, decimal.Decimal):
                    try:
                        new_value = decimal.Decimal(value)
                    except decimal.InvalidOperation:
                        raise InvalidFilterValueError(key, value)
                else:
                    new_value = value
                checked_values.append(new_value)
            elif field_type == models.FieldType.datetime:
                # Must be a pair of datetimes, or a string parseable
                # with evesrp.util.datetime.parse_datetime
                if isinstance(value, tuple) and len(value) == 2:
                    if isinstance(value[0], dt.datetime) and \
                            isinstance(value[1], dt.datetime):
                        checked_values.append(value)
                elif isinstance(value, six.text_type):
                    try:
                        parsed_value = evesrp.util.parse_datetime(value)
                        checked_values.append(parsed_value)
                    except iso8601.ParseError:
                        raise InvalidFilterValueError(key, value)
                else:
                    raise InvalidFilterValueError(key, value)
            elif field_type == models.FieldType.status:
                if value not in models.ActionType:
                    try:
                        status = models.ActionType[value]
                    except KeyError:
                        raise InvalidFilterValueError(key, value)
                else:
                    status = value
                checked_values.append(status)
            elif field_type == models.FieldType.url:
                # TODO: Better URL checking
                if not isinstance(value, six.string_types):
                    raise InvalidFilterValueError(key, value)
                checked_values.append(value)
            elif field_type in (models.FieldType.string,
                                models.FieldType.text):
                if not isinstance(value, six.string_types):
                    raise InvalidFilterValueError(key, value)
                checked_values.append(value)
            elif field_type in (models.FieldType.integer,
                                models.FieldType.app_id,
                                models.FieldType.ccp_id):
                if not isinstance(value, six.integer_types):
                    raise InvalidFilterValueError(key, value)
                checked_values.append(value)
        self._filters[key].update(checked_values)

    @check_filter_key
    def remove(self, key, *values):
        if key not in self._filters:
            # For keys not added yet, bail out quickly
            return
        self._filters[key].difference_update(values)
        # Remove empty filters
        if len(self._filters[key]) == 0:
               del self._filters[key]

    def merge(self, other_filter):
        # if other_filter is None, empty, or equivalent, this is a noop
        if other_filter is None or len(other_filter) == 0 or \
               other_filter == self:
            return self
        for field, values in other_filter:
            self._filters[field].update(values)

    def matches(self, request, killmail=None):
        if killmail is not None and request.killmail_id != killmail.id_:
            raise ValueError("You must pass in the killmail for the request.")
        missing_killmail_error = ValueError("The killmail must be passed in if"
                                            " filtering on killmail "
                                            "attributes.")
        for key, values in six.iteritems(self._filters):
            # Killmail fields
            if key in models.Killmail.fields:
                if killmail is None:
                    raise missing_killmail_error
                if getattr(killmail, key) not in values:
                    return False
            # Request fields
            elif key in models.Request.fields:
                if getattr(request, key) not in values:
                    return False
            # Special fields
            elif key == 'request_id':
                if request.id_ not in values:
                    return False
            elif key.endswith('_timestamp'):
                if key.startswith('request'):
                    timestamp = request.timestamp
                elif key.startswith('killmail'):
                    if killmail is None:
                        raise missing_killmail_error
                    timestamp = killmail.timestamp
                # Timestamps are special. The values are all ranges
                # (represented by tuples of starting and ending times, both
                # inclusive).
                for start, end in values:
                    if start <= timestamp >= end:
                        break
                else:
                    return False
            else:
                raise InvalidFilterKeyError("This point should not be "
                                            "reached.")
        return True
