# -*- coding: UTF-8 -*-
import collections
import datetime as dt
import decimal
import enum
import functools
import itertools
import operator

import six
import iso8601

import evesrp
from evesrp.util import classproperty
from evesrp import new_models as models
from .predicate import PredicateType


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


class InvalidFilterPredicateError(ValueError):

    def __init__(self, key, predicate):
        self.key = key
        self.predicate = predicate
        error_msg = u"Predicate '{}' is not valid for attribute '{}'.".format(
            self.predicate, self.key)
        super(InvalidFilterPredicateError, self).__init__(error_msg)


def check_filter_key(func):
    @functools.wraps(func)
    def filter_key_check(*args, **kwargs):
        try:
            key = args[1]
        except IndexError:
            raise TypeError("{} requires at least a key".format(
                func.__name__))
        # First check that this is a valid key
        if key not in Search._field_types:
            raise InvalidFilterKeyError(key)
        # Now check that the predicate operator is valid for this type of filter
        predicate = kwargs.get('predicate')
        field_type = Search._field_types[key]
        # Skip processing for FieldType.text, predicates don't apply to those
        # fields.
        if predicate is not None or field_type == models.FieldType.text:
            if field_type in models.FieldType.exact_types and \
                    predicate not in PredicateType.exact_comparisons:
                raise InvalidFilterPredicateError(key, predicate)
            elif field_type in models.FieldType.range_types and \
                    predicate not in PredicateType.range_comparisons:
                raise InvalidFilterPredicateError(key, predicate)
        return func(*args, **kwargs)
    return filter_key_check


def check_sort_key(func):
    @functools.wraps(func)
    def sort_key_check(*args, **kwargs):
        # Check the key
        try:
            key = args[1]
        except IndexError:
            raise TypeError("{} requires at least a key".format(
                func.__name__))
        if key not in models.Killmail.sorts and \
                key not in models.Request.sorts:
            raise ValueError("key is not sortable.")
        # The direction may not be given, in which case it uses the default
        # (valid) direction
        try:
            direction = args[2]
            direction_given = True
        except IndexError:
            try:
                direction = kwargs['direction']
                direction_given = True
            except KeyError:
                direction_given = False
        # Check the key and direction validity
        if direction_given and direction not in SortDirection:
            raise TypeError("invalid direction given.")
        return func(*args, **kwargs)
    return sort_key_check


class SortDirection(enum.Enum):

    ascending = 1

    descending = -1


class Search(object):
    """The ``Search`` class is intendeded as a way to specify how to retrieve
    :py:class:`~.Request` objects from the app's storage.

    The two ways provided are by **filtering** and **sorting**. Filtering is
    similar to how one might filter through results on a shopping page, while
    sorting gives you control over the order results are presented.

    Filtering is done on :py:class:`~.Request` and :py:class:`~.Killmail`
    fields, as explained in :py:class:`~.FieldType`\. Filter definitions are
    added to the :py:class:`Search` using :py:meth:`add_filter`\. Multiple
    filter definitions may be provided for a single field name, and how they
    are combined depends on the type of the field. If the field type is one of
    :py:attr:`~.FieldType.exact_types`\, only strict equality or inequality
    comparisons are allowed. Multiple filter definitions will be evaluated as
    multiple predicates combined with a logical OR. As an example, if multiple
    type IDs are added to the Search, any Request for a Killmail for *any* of
    those type IDs will match.For fields in
    :py:attr:`~.FieldType.range_types`\, the opposite strategy is applied;
    multiple filter definitions are treated as individual predicates and are
    evaluated with a logical AND. A Request must also match against every field
    that has a filter specified.

    Text types (like :py:attr:`~Request.details`\) are matched with a
    case-insensitive substring search. If multiple filters are given for a
    single text field, they combined like an exact type, that is if any filter
    matches that field, that request passes.

    Sorting is much more straightforward. Sortable fields can either be sorted
    in ascending or descending order, and multiple fields may be sorted on.
    Sorting definitions are added using :py:meth:`add_sort`\. The first sort
    definition is used to sort the Requests, and if some requests have an
    identical value for that field, the next sort field is used for those
    requests and so on and so forth. To ensure a stable sorting order for all
    searches, an ascending sort on the Killmail ID and Request ID will be added
    to all Searches.
    """

    # _field_types is a local copy of the Request and Killmail field_types
    _field_types = {}
    _field_types.update(models.Killmail.field_types)
    _field_types.update(models.Request.field_types)

    def __init__(self):
        # keys are field names, values are dicts with the keys being values to
        # filter on, and the values of the inner dicts being a set of
        # PredicateType members.
        self._filters = {}
        # Keys are field names, values are directions
        self._sorts = collections.OrderedDict()

    @staticmethod
    def _field_filter_to_tuple(field_filter):
        predicate_tuples = set()
        if field_filter is None:
            return predicate_tuples
        for value, predicates in six.iteritems(field_filter):
            predicate_tuples.update(
                [(value, predicate) for predicate in predicates]
            )
        return predicate_tuples

    def __iter__(self):
        """Iterate over the current filter definitions.

        Values are 2-tuples, with the first element being the field name, and
        the second being an iterable of 2-tuples. These latter tuples are
        comprised of the value being filtered on, and the second being the
        predicate for that value.
        """
        for field_name, field_filters in six.iteritems(self._filters):
            yield (field_name, self._field_filter_to_tuple(field_filters))

    def __contains__(self, field_name):
        return field_name in self._filters

    @check_filter_key
    def __getitem__(self, field_name):
        return self._field_filter_to_tuple(self._filters.get(field_name))

    def __eq__(self, other):
        if not isinstance(other, Search):
            return NotImplemented
        return self._filters == other._filters and \
            self._sorts == other._sorts

    def __repr__(self):
        def set_repr(a_set):
            return "{{{}}}".format(", ".join(map(repr, a_set)))
        def dict_repr(a_dict):
            items = ["'{}': {}".format(key, set_repr(value)) for key, value in
                     six.iteritems(a_dict)]
            return "{{{}}}".format(", ".join(items))
        return "Search({})".format(dict_repr(self._filters))

    # Sorting

    @check_sort_key
    def add_sort(self, key, direction=SortDirection.ascending):
        """Add an additional sorting order to the end of the sorting list.

        If the field name is already present in the sorting list, it is removed
        from that position and added to the end.

        :param str key: A field key to sort on.
        :param direction: The direction to sort.
        :type direction: :py:class:`.SortDirection`
        """
        if key in self._sorts:
            del self._sorts[key]
        self._sorts[key] = direction

    def set_default_sort(self):
        """Set the sorting order to the common ascending request timestamp and
        status sort.
        """
        self.clear_sorts()
        self.add_sort('status')
        self.add_sort('request_timestamp')

    @check_sort_key
    def remove_sort(self, key):
        """Remove a field from the sorting order.

        If the field is not being sorted on, a :py:exc:`ValueError` is raised.
        """

        try:
            del self._sorts[key]
        except KeyError as old_exc:
            new_exc = ValueError("'{}' is not being sorted on.".format(key))
            six.raise_from(new_exc, old_exc)

    def clear_sorts(self):
        """Remove all sorting definitions."""
        self._sorts.clear()

    @property
    def sorts(self):
        """An iterator of 2-tuples of sort keys (strings) and directions.
        """
        # Can be replaced by a yield from statement in Python >= 3.3
        for k, v in six.iteritems(self._sorts):
            yield (k, v)

    # Filtering

    def _sanitize_values(self, field_name, *values):
        field_type = self._field_types[field_name]
        checked_values = set()
        for value in values:
            # Check types
            if field_type == models.FieldType.datetime and \
                    not isinstance(value, dt.datetime):
                raise InvalidFilterValueError(field_name, value)
            elif field_type == models.FieldType.decimal and \
                    not isinstance(value, decimal.Decimal):
                # Accept values that can be converted to a Decimal
                try:
                    new_value = decimal.Decimal(value)
                except decimal.InvalidOperation as decimal_exc:
                    invalid_exc = InvalidFilterValueError(field_name, value)
                    six.raise_from(
                        InvalidFilterValueError(field_name, value),
                        decimal_exc
                    )
                value = new_value
            elif field_type == models.FieldType.status and \
                    value not in models.ActionType:
                try:
                    value = models.ActionType[value]
                except KeyError as key_exc:
                    six.raise_from(
                        InvalidFilterValueError(field_name, value),
                        key_exc
                    )
            elif field_type in models.FieldType.integer_types and \
                    not isinstance(value, int):
                raise InvalidFilterValueError(field_name, value)
            elif field_type in models.FieldType.string_types and \
                    not isinstance(value, six.string_types):
                raise InvalidFilterValueError(field_name, value)
            checked_values.add(value)
        return checked_values


    @check_filter_key
    def add_filter(self, field_name, *values, **kwargs):
        """Add a filter definition.

        :param str field_name: The field name to filter against.
        :param predicate: By default, filtering is done with strict equality.
            The argument provides a way to do more complex comparisons when
            filtering.
        :type predicate: PredicateType or None
        :param values: The values to filter for.
        """
        predicate = kwargs.get('predicate')
        new_values = self._sanitize_values(field_name, *values)
        # Actually add the new values to filter on to self._filters
        if field_name not in self._filters:
            self._filters[field_name] = collections.defaultdict(set)
        field_filters = self._filters[field_name]
        for value in new_values:
            if predicate is None:
                predicate = PredicateType.equal
            field_filters[value].add(predicate)

    @check_filter_key
    def remove_filter(self, field_name, *values, **kwargs):
        """Remove a filter definition from a Search.

        :param str field_name: The field name to act on.
        :param predicate: If provided, only remove these predicates form the
            filter. If `None` is given, all predicates will be removed for the
            given values.
        :type predicate: PredicateType or None
        :param values: The values to no longer filter against.
        :raises KeyError: if the `field_name` does not already have any
            filters.
        """
        sanitized_values = self._sanitize_values(field_name, *values)
        predicate = kwargs.get('predicate')
        # Not checking for the existence of field_name in self._filters. It's
        # an invalid precondition
        field_filters = self._filters[field_name]
        for value in sanitized_values:
            if predicate is None:
                del field_filters[value]
            else:
                field_filters[value].discard(predicate)
        # Clean up and remove empty dicts
        if len(field_filters) == 0:
            del self._filters[field_name]

    filters = property(__iter__)

    @property
    def simplified_filters(self):
        """Generator for a simplified view of :py:meth:`.filters`\.

        For :py:meth:`.filters` second item will be an iterable of 2-tuples,
        but if there are multiple predicates specified for a single value,
        there will a 2-tuple for each of those predicates. This generator
        guarantees that there will only be a single 2-tuple for each value, as
        it simplifies multiple predicates into a single one.
        """
        for field_name, field_filters in six.iteritems(self._filters):
            field_type = self._field_types[field_name]
            if field_type in models.FieldType.exact_types:
                reducer = operator.or_
            elif field_type in models.FieldType.range_types:
                reducer = operator.and_
            else:
                # If not in range or exact types, this field's predicates are
                # ignored.
                yield (
                    field_name,
                    {(value, None) for value in six.iterkeys(field_filters)}
                )
                continue
            simplified = {}
            for value, predicates in six.iteritems(field_filters):
                simplified[value] = functools.reduce(reducer, predicates)
            # if a field definition is simplified away, skip it entirely
            yield (
                field_name,
                {(val, pred) for val, pred in six.iteritems(simplified)}
            )

    def merge(self, other_search):
        # if other_search is None, empty, or itself, this is a noop
        if other_search is None or \
                other_search == self or \
                (len(other_search._sorts) == 0 and \
                 len(other_search._filters) == 0):
            return self
        # Otherwise, add all the filters from other_search to self
        for field_name, field_filters in six.iteritems(other_search._filters):
            for value, predicates in six.iteritems(field_filters):
                for predicate in predicates:
                    self.add_filter(field_name, value, predicate=predicate)
        # Only change self._sorts if it is empty
        if len(self._sorts) == 0:
            self._sorts = other_search._sorts
        return self

    def matches(self, request, killmail=None):
        if killmail is not None and request.killmail_id != killmail.id_:
            raise ValueError("You must pass in the killmail for the request.")
        missing_killmail_error = ValueError("The killmail must be passed in if"
                                            " filtering on killmail "
                                            "attributes.")
        for field_name, filter_tuples in self.simplified_filters:
            # Handle special fields (basically ones where the model names
            # collide).
            if field_name == 'request_id':
                reference_value = request['id']
            elif field_name == 'killmail_id':
                if killmail is None:
                    raise missing_killmail_error
                reference_value = killmail['id']
            elif field_name.endswith('_timestamp'):
                if field_name.startswith('request'):
                    reference_value = request.timestamp
                elif field_name.startswith('killmail'):
                    if killmail is None:
                        raise missing_killmail_error
                    reference_value = killmail.timestamp
            # Handle non-colliding field names
            elif field_name in models.Killmail.fields:
                if killmail is None:
                    raise missing_killmail_error
                reference_value = getattr(killmail, field_name)
            elif field_name in models.Request.fields:
                reference_value = getattr(request, field_name)
            else:
                # Yes, this will raise as a weird error. It's meant to be
                # weird.
                raise InvalidFilterKeyError(
                    "Somehow, a field name without a corresponding field"
                    "type was added as a filter.")
            field_type = self._field_types[field_name]
            if field_type == models.FieldType.text:
                # text types are done as a case-insensitive substring
                # search.
                reference_value = reference_value.lower()
                just_values = map(lambda t: t[0], filter_tuples)
                passing = map(lambda v: v.lower() in reference_value,
                              just_values)
                match = functools.reduce(operator.or_, passing)
                if not match:
                    return False
            elif field_type in models.FieldType.range_types:
                for value, predicate in filter_tuples:
                    if not predicate.operator(reference_value, value):
                        return False
            elif field_type in models.FieldType.exact_types:
                # very similar to text types, but with some special
                # handling of None and no massaging of values.

                # Functionally similar to how text types are handled, but
                # done differently to handle None specially
                for value, predicate in filter_tuples:
                    if predicate is None:
                        return True
                    if predicate.operator(reference_value, value):
                        return True
                return False
        return True
