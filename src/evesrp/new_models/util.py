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

    integer = 0
    """For fields that store an integer with no further restrictions."""

    datetime = 1
    """For fields that store a date and time."""

    decimal = 2
    """For fields that hold a decimal value."""

    string = 3
    """For fields holding an unstructured string."""

    text = 4
    """For fields holding a string value that is intended to be longer and
    searchable.
    """

    ccp_id = 5
    """For integer fields referring to a CCP defined ID number."""

    app_id = 6
    """For integer fields referrring to an ID for an item in this app's
    database.
    """

    status = 7
    """For fields referring to an :py:class:`~.ActionType`."""

    url = 8
    """For string fields referring to a URL."""
