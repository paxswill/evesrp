import sqlalchemy as sqla


@sqla.event.listens_for(sqla.engine.Engine, 'connect')
def connect_listener(dbapi_connection, connection_record):
    # NOTE This is hacky, too many underscores to be a good idea
    dialect_name = connection_record._ConnectionRecord__pool._dialect.name
    if dialect_name == 'sqlite':
        # disable pysqlite's emitting of the BEGIN statement entirely.
        # also stops it from emitting COMMIT before any DDL.
        dbapi_connection.isolation_level = None
        # Also enable transactions
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


@sqla.event.listens_for(sqla.engine.Engine, 'begin')
def pysqlite_begin_listener(conn):
    # Not a massive hack this time
    dialect_name = conn.dialect.name
    if dialect_name == 'sqlite':
        # emit our own BEGIN
        conn.execute("BEGIN")
