import json
import enum
from evesrp import serializers


def test_serialize_enum():
    class EnumTest(enum.Enum):
        foo = u'bar'
        baz = u'qux'
    expected_json = {e: '"{}"'.format(e.value) for e in EnumTest}
    actual_json = {e: json.dumps(e, cls=serializers.EnumEncoder) for e in
                   EnumTest}
    for e in EnumTest:
        assert json.loads(expected_json[e]) == json.loads(actual_json[e])
