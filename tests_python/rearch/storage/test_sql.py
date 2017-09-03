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
    def connection(self, engine, schema):
        conn = engine.connect()
        yield conn
        conn.close()

    @pytest.fixture(scope='function')
    def bare_store(self, connection):
        return SqlStore(connection=connection)

    @pytest.fixture(scope='function')
    def store(self, connection, bare_store):
        with connection.begin_nested() as trans:
            yield bare_store
            trans.rollback()

    @pytest.fixture(scope='function')
    def populated_store(self, bare_store, request, connection):
        dirty_database = (
            connection.dialect.name == 'mysql' and
            request.function.__name__ in ('test_filter',
                                          'test_sparse_filter')
        )
        if dirty_database:
            # MySQL doesn't update the FTS indexes until a commit has happened,
            # so for those tests that need those indexes updated, we populate
            # the test data, commit it, run the tests, than delete everything.
            populate_database(connection)
            transaction = connection.begin_nested()
        else:
            # On everything else, we populate the data inside a transaction
            transaction = connection.begin_nested()
            populate_database(connection)
        yield bare_store
        transaction.rollback()
        if dirty_database:
            # now delete all data we commited
            for table in reversed(ddl.metadata.sorted_tables):
                connection.execute(table.delete())
