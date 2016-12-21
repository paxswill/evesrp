import json


class ISOTimestampEncoder(json.JSONEncoder):

    def default(self, o):
        try:
            return o.isoformat()
        except AttributeError:
            super(ISOTimestampEncoder, self).default(o)
