import pytest
import sqlalchemy as sqla

from evesrp.storage.sql import SqlStore, ddl
from .base_test import CommonStorageTest
from .populate_sql import populate_database


class TestSqlStore(CommonStorageTest):

    @pytest.fixture(
        scope='session',
        params=(
            'sqlite:///:memory:',
            'postgres://paxswill@localhost/evesrp_rearch',
            'mysql+pymysql://root@localhost/evesrp_rearch',
        ),
        ids=(
            'sqlite',
            'postgres',
            'mysql',
        )
    )
    def engine(self, request):
        engine = sqla.create_engine(request.param)
        return engine

    @pytest.fixture(scope='session')
    def schema(self, engine):
        # Destroy first to clear up any leftover data
        SqlStore.destroy(engine)
        SqlStore.create(engine)
        yield
        SqlStore.destroy(engine)

    @pytest.fixture(scope='function')
    def store(self, engine, schema):
        conn = engine.connect()
        with conn.begin_nested() as trans:
            store = SqlStore(connection=conn)
            yield store
            trans.rollback()
        conn.close()

    @pytest.fixture(scope='function')
    def populated_store(self, engine, store):
        # Peek into the store so we can stay within the nested transaction
        # started in the `store` fixture
        conn = store.connection
        with conn.begin_nested() as trans:
            populate_database(conn)
            yield store
            trans.rollback()
