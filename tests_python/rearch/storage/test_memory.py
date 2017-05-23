from __future__ import absolute_import
import datetime as dt
from decimal import Decimal
import uuid

import pytest

from evesrp import storage
from .base_test import CommonStorageTest


class TestMemoryStore(CommonStorageTest):

    @pytest.fixture
    def store(self):
        return storage.MemoryStore()

    @pytest.fixture
    def populated_store(self, memory_store):
        return memory_store
