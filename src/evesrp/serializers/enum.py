import json


class EnumEncoder(json.JSONEncoder):

    def default(self, o):
        try:
            return o.value
        except AttributeError:
            return super(EnumEncoder, self).default(o)
