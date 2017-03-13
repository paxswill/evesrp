import datetime as dt
import json
from evesrp import serializers


def test_serialize_datetime():
    timestamp = dt.datetime(2016, 12, 24)
    expected_json = '"2016-12-24T00:00:00"'
    assert json.loads(expected_json) == json.loads(json.dumps(
        timestamp, cls=serializers.ISOTimestampEncoder))
