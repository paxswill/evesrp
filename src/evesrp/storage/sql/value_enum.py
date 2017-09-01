import enum
import sqlalchemy as sqla
# These imports are to minimize the changes needed to the standard Enum code
from sqlalchemy import util, Enum
from sqlalchemy.sql.elements import TypeCoerce as type_coerce, _defer_name
from sqlalchemy.sql.sqltypes import SchemaType


class ValueEnum(sqla.Integer, SchemaType):
    """This is a moderately modified version of the standard SQLAlchemy Enum
    that stores the *values* of a PEP 435 enum instead of the string names.
    This was mainly done to enforce a sorting order.
    """

    def __init__(self, enum, **kw):
        self.enum_class = enum
        if 'name' not in kw:
            # name needs to be in kw to have adapt() work
            kw['name'] = self.enum_class.__name__.lower()
        self.name = kw['name']

        self.enums = [v.value for v in self.enum_class]
        self._valid_lookup = {v: v.value for v in self.enum_class}
        self._object_lookup = {v.value: v for v in self.enum_class}
        self._valid_lookup.update({v.name: v.value for v in self.enum_class})

        self.native_enum = kw.pop('native_enum', True)
        self.create_constraint = kw.pop('create_constraint', True)

        self._valid_lookup[None] = self._object_lookup[None] = None

        sqla.Integer.__init__(self)
        sqla.sql.sqltypes.SchemaType.__init__(self, **kw)

    def _db_value_for_elem(self, elem):
        # Mirroring Enum._db_value_for_elem, just without error checking (that
        # sounds like a bad idea typing it out).
        return self._valid_lookup[elem]

    def literal_processor(self, dialect):
        parent_processor = super(ValueEnum, self).literal_processor(dialect)

        def process(value):
            value = self._db_value_for_elem(value)
            if parent_processor:
                value = parent_processor(value)
            return value
        return process

    bind_processor = literal_processor

    def result_processor(self, dialect, coltype):
        parent_processor = super(ValueEnum, self).result_processor(
            dialect, coltype
        )

        def process(value):
            if parent_processor:
                value = parent_processor(value)

            # We can just call the enum class for value lookup
            value = self.enum_class(value)
            return value

        return process

    comparator_factory = sqla.Integer.Comparator

    @property
    def python_type(self):
        return self.enum_class

    def adapt(self, impltype, **kw):
        schema = kw.pop('schema', self.schema)
        metadata = kw.pop('metadata', self.metadata)
        _create_events = kw.pop('_create_events', False)
        if issubclass(impltype, ValueEnum):
            return impltype(self.enum_class,
                            name=self.name,
                            schema=schema,
                            metadata=metadata,
                            native_enum=self.native_enum,
                            inherit_schema=self.inherit_schema,
                            _create_events=_create_events,
                            **kw)
        else:
            # TODO: why would we be here?
            return super(ValueEnum, self).adapt(impltype, **kw)

    # Everything below is straight copied from sqlalchemy.sql.sqltypes.Enum

    def _should_create_constraint(self, compiler, **kw):
        if not self._is_impl_for_variant(compiler.dialect, kw):
            return False
        return not self.native_enum or \
            not compiler.dialect.supports_native_enum

    @util.dependencies("sqlalchemy.sql.schema")
    def _set_table(self, schema, column, table):
        if self.native_enum:
            SchemaType._set_table(self, column, table)

        if not self.create_constraint:
            return

        variant_mapping = self._variant_mapping_for_set_table(column)

        e = schema.CheckConstraint(
            type_coerce(column, self).in_(self.enums),
            name=_defer_name(self.name),
            _create_rule=util.portable_instancemethod(
                self._should_create_constraint,
                {"variant_mapping": variant_mapping}),
            _type_bound=True
        )
        assert e.table is table

    def copy(self, **kw):
        return SchemaType.copy(self, **kw)
