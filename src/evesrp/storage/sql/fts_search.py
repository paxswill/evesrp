import sqlalchemy.ext.compiler
import sqlalchemy.sql.expression
import sqlalchemy as sqla


class NaturalMatch(sqla.sql.expression.ClauseElement):
    """Custom SQL clause for matching in natural language mode on MySQL and
    normal FTS matching on PostgreSQL.
    """

    def __init__(self, columns, value):
        self.columns = columns
        self.value = sqla.literal(value)


@sqla.ext.compiler.compiles(NaturalMatch)
def default_natural_match(element, compiler, **kw):
    # Default to handling .match as a LIKE operation (.contains in SQLAlchemy).
    return compiler.process(element.columns[0].contains(element.value))


@sqla.ext.compiler.compiles(NaturalMatch, 'postgresql')
def pg_natural_match(element, compiler, **kw):
    # Explicitly use english so we can make use of the full text index defined
    # in storage.sql.ddl
    return "to_tsvector('english', {}) @@ to_tsquery('english', {})".format(
        " || ".join(compiler.process(c, **kw) for c in element.columns),
        compiler.process(element.value)
    )


@sqla.ext.compiler.compiles(NaturalMatch, 'mysql')
def mysql_natural_match(element, compiler, **kw):
    # The entire reason we're using a custom clause element, to use natural
    # language mode instead of boolean mode on MySQL.
    return "MATCH ({}) AGAINST ({} IN NATURAL LANGUAGE MODE)".format(
        ", ".join(compiler.process(c, **kw) for c in element.columns),
        compiler.process(element.value)
    )
