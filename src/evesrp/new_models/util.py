import datetime as dt
import iso8601
import six


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
