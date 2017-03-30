from werkzeug.utils import import_string


# Utility function for creating instances from dicts
def instance_from_dict(instance_descriptor):
    type_name = instance_descriptor.pop('type')
    Type = import_string(type_name)
    return Type(**instance_descriptor)
