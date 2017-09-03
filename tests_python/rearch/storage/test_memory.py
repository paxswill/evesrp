import pytest

from evesrp import storage
from .base_test import CommonStorageTest


class TestMemoryStore(CommonStorageTest):

    @pytest.fixture
    def store(self):
        return storage.MemoryStore()

    # Instead of overriding 
    @pytest.fixture
    def populated_store(self, memory_store):
        return memory_store
