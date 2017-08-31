import sqlalchemy.ext.compiler
import sqlalchemy.sql.expression
import sqlalchemy as sqla


class NaturalMatch(sqla.sql.expression.ClauseElement):

    def __init__(self, columns, value):
        self.columns = columns
        self.value = sqla.literal(value)


@sqla.ext.compiler.compiles(NaturalMatch)
def default_natural_match(element, compiler, **kw):
    return compiler.process(element.columns[0].contains(element.value))


@sqla.ext.compiler.compiles(NaturalMatch, 'postgresql')
def pg_natural_match(element, compiler, **kw):
    return "to_tsvector('english', {}) @@ to_tsquery('english', {})".format(
        " || ".join(compiler.process(c, **kw) for c in element.columns),
        compiler.process(element.value)
    )


@sqla.ext.compiler.compiles(NaturalMatch, 'mysql')
def mysql_natural_match(element, compiler, **kw):
    return "MATCH ({}) AGAINST ({} IN NATURAL LANGUAGE MODE)".format(
        ", ".join(compiler.process(c, **kw) for c in element.columns),
        compiler.process(element.value)
    )
