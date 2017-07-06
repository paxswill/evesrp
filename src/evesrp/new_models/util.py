import enum
import iso8601
import six

from evesrp.util import classproperty


class IdEquality(object):

    def __hash__(self):
        return hash(self.id_) ^ hash(self.__class__.__name__)

    def __eq__(self, other):
        # Simplistic, not checking types here.
        return self.id_ == other.id_


class GetItemAttribute(object):

    def __getitem__(self, item):
        key_error = KeyError("{} does not exist as an attribute.".format(item))
        try:
            return getattr(self, item)
        except AttributeError:
            # just in case the name is a reserved one being worked around by
            # adding a trailing underscore (like type or id)
            try:
                return getattr(self, item + '_')
            except AttributeError:
                raise key_error
            raise key_error


def id_from_kwargs(arg_name, kwargs):
    id_name = arg_name + '_id'
    if arg_name not in kwargs and id_name not in kwargs:
        raise ValueError(u"Neither '{}' nor '{}' have been supplied.".format(
            arg_name, id_name))
    elif arg_name in kwargs:
        return kwargs[arg_name].id_
    else:
        return kwargs[id_name]


def parse_timestamp(raw_timestamp):
    if isinstance(raw_timestamp, six.string_types):
        return iso8601.parse_date(raw_timestamp)
    return raw_timestamp


class _FieldTypeSet(frozenset):

    def __new__(cls, fields):
        self = super(_FieldTypeSet, cls).__new__(cls, fields.keys())
        self._fields = fields
        return self

    def __getitem__(self, field_type):
        if field_type not in FieldType:
            raise ValueError("field_type must be a member of FieldType.")
        # Customize some things for subordinate types
        # Ex: app_id amd ccp_id both count as integer types, and text and url
        # both count as string types.
        if field_type == FieldType.integer:
            field_types = {field_type, FieldType.app_id, FieldType.ccp_id}
        elif field_type == FieldType.string:
            field_types = {field_type. FieldType.text, FieldType.url}
        else:
            field_types = {field_type, }
        return {k for k, v in six.iteritems(self._fields) if v in field_types}


class FieldsAccess(object):

    @classproperty
    def fields(self):
        return _FieldTypeSet(self.field_types)


class FieldType(enum.Enum):
    """A way to classify which fields on models are able to be filtered, and
    how to filter them.

    Model classes that support filtering (at this time, just
    :py:class:`~.Killmail` and :py:class:`~.Request`\) declare a
    `field_types` mapping of string field names to
    :py:class:`FieldType`\s.

    If the model class also supports sorting on fields, those are declared in 
    a `sorts` attribute consisting of an iterable of field names. All
    of the field names must be present in the `field_types` mapping,
    with one exception: sorting field names of the form `foo_name` are
    allowed when there is an actual field name `foo_id` of the type
    :py:attr:`ccp_id`\.
    """

    integer = 0
    """For fields that store an integer with no further restrictions."""

    datetime = 1
    """For fields that store a date and time.
    
    Filtering on these fields is done by specifying a range with a starting and
    and ending timestamp.
    """

    decimal = 2
    """For fields that hold a decimal value."""

    string = 3
    """For fields holding an unstructured string."""

    text = 4
    """For fields holding a string value that is intended to be longer and
    searchable.
    """

    ccp_id = 5
    """For integer fields referring to a CCP defined ID number.

    As an ID, filtering on this type is exact only.
    """

    app_id = 6
    """For integer fields referrring to an ID for an item in this app's
    database.

    Like :py:attr:`ccp_id`\, fields of this type are filtered by exact matches
    only.
    """

    status = 7
    """For fields referring to an :py:class:`~.ActionType`.

    Again, exact match filtering only.
    """

    url = 8
    """For string fields referring to a URL."""

    @classproperty
    def exact_types(cls):
        """These field types only support filtering for exact values."""
        return frozenset((
            cls.ccp_id,
            cls.app_id,
            cls.status,
            cls.string
        ))

    @classproperty
    def range_types(cls):
        """These field types support complex comparisons when filtering.

        Complex comparisons are things like less than or greater than.
        """
        return frozenset((
            cls.integer,
            cls.datetime,
            cls.decimal
        ))

    @classproperty
    def integer_types(cls):
        """Covers all types that are integers, no matter the semantics."""
        return frozenset((
            cls.integer,
            cls.ccp_id,
            cls.app_id
        ))

    @classproperty
    def string_types(cls):
        """Covers all types that are strings, no matter the semantics."""
        return frozenset((
            cls.string,
            cls.text,
            cls.url
        ))
