# -*- coding: UTF-8 -*-
import enum
import operator
from evesrp.util import classproperty


class PredicateType(enum.Enum):

    equal = '='

    not_equal = '!='

    less = '<'

    greater = '>'

    less_equal = '<='

    greater_equal = '>='

    any = 'any'

    none = 'none'

    @classproperty
    def exact_comparisons(cls):
        return frozenset((
            cls.equal,
            cls.not_equal
        ))

    @classproperty
    def range_comparisons(cls):
        return frozenset((
            cls.less,
            cls.greater,
            cls.less_equal,
            cls.greater_equal,
            # These were added in after the other members for allowable range
            # comparisons.
            cls.equal,
            cls.not_equal
        ))


    def add_or(self, other):
        # short-circuit tautologies
        if self == other:
            return self
        # this method is also used as the __or__ method, so conform to that
        # spec
        elif not isinstance(other, PredicateType):
            return NotImplemented
        elif PredicateType.any in (self, other):
            return PredicateType.any
        elif PredicateType.none == self:
            return other
        elif PredicateType.none == other:
            return self
        else:
            # keys are sets (frozensets so they're hashable) of the two
            # operations we're ORing, and the value is the logical equivalent.
            or_results = {
                # Start with the any cases
                # = | ≠ ≡ any
                frozenset((PredicateType.equal, PredicateType.not_equal)):
                    PredicateType.any,
                # ≥ | ≠ ≡ any
                frozenset((PredicateType.greater_equal,
                           PredicateType.not_equal)):
                    PredicateType.any,
                # ≤ | ≠ ≡ any
                frozenset((PredicateType.less_equal, PredicateType.not_equal)):
                    PredicateType.any,
                # ≥ | < ≡ any
                frozenset((PredicateType.greater_equal, PredicateType.less)):
                    PredicateType.any,
                # ≤ | > ≡ any
                frozenset((PredicateType.less_equal, PredicateType.greater)):
                    PredicateType.any,
                # ≥ | ≤ ≡ any
                frozenset((PredicateType.greater_equal,
                           PredicateType.less_equal)):
                    PredicateType.any,
                # Now not-equal
                # < | > ≡ ≠
                frozenset((PredicateType.less, PredicateType.greater)):
                    PredicateType.not_equal,
                # ≠ | > ≡ ≠
                frozenset((PredicateType.not_equal, PredicateType.greater)):
                    PredicateType.not_equal,
                # ≠ | < ≡ ≠
                frozenset((PredicateType.not_equal, PredicateType.less)):
                    PredicateType.not_equal,
                # Less-than or equal
                # = | < ≡ ≤
                frozenset((PredicateType.equal, PredicateType.less)):
                    PredicateType.less_equal,
                # = | ≤ ≡ ≤
                frozenset((PredicateType.equal, PredicateType.less_equal)):
                    PredicateType.less_equal,
                # < | ≤ ≡ ≤
                frozenset((PredicateType.less, PredicateType.less_equal)):
                    PredicateType.less_equal,
                # Greater-than or equal
                # = | > ≡ ≥
                frozenset((PredicateType.equal, PredicateType.greater)):
                    PredicateType.greater_equal,
                # = | ≥ ≡ ≥
                frozenset((PredicateType.equal, PredicateType.greater_equal)):
                    PredicateType.greater_equal,
                # > | ≥ ≡ ≥
                frozenset((PredicateType.greater,
                           PredicateType.greater_equal)):
                    PredicateType.greater_equal,
            }
            operands = frozenset((self, other))
            return or_results[operands]

    __or__ = add_or

    def add_and(self, other):
        # short-circuit tautologies
        if self == other:
            return self
        # Again, conforming to the operator spec
        elif not isinstance(other, PredicateType):
            return NotImplemented
        elif PredicateType.none in (self, other):
            return PredicateType.none
        elif PredicateType.any == self:
            return other
        elif PredicateType.any == other:
            return self
        else:
            # Same structure as the or_results map in the add_or method, with
            # the exception that None in this case represents the null set (aka
            # no results possible).
            and_results = {
                # Start with the null cases
                # > & < ≡ null
                frozenset((PredicateType.greater, PredicateType.less)):
                    PredicateType.none,
                # > & = ≡ null
                frozenset((PredicateType.greater, PredicateType.equal)):
                    PredicateType.none,
                # ≤ & > ≡ null
                frozenset((PredicateType.less_equal, PredicateType.greater)):
                    PredicateType.none,
                # < & = ≡ null
                frozenset((PredicateType.less, PredicateType.equal)):
                    PredicateType.none,
                # < & ≥ ≡ null
                frozenset((PredicateType.less, PredicateType.greater_equal)):
                    PredicateType.none,
                # = & ≠ ≡ null
                frozenset((PredicateType.equal, PredicateType.not_equal)):
                    PredicateType.none,
                # Now equal
                # ≥ & = ≡ =
                frozenset((PredicateType.greater_equal,
                           PredicateType.equal)):
                    PredicateType.equal,
                # ≤ & = ≡ =
                frozenset((PredicateType.less_equal, PredicateType.equal)):
                    PredicateType.equal,
                # ≤ & ≥ ≡ =
                frozenset((PredicateType.less_equal,
                           PredicateType.greater_equal)):
                    PredicateType.equal,
                # Less-than
                # ≠ & < ≡ <
                frozenset((PredicateType.not_equal, PredicateType.less)):
                    PredicateType.less,
                # ≤ & < ≡ <
                frozenset((PredicateType.less_equal, PredicateType.less)):
                    PredicateType.less,
                # ≤ & ≠ ≡ <
                frozenset((PredicateType.less_equal, PredicateType.not_equal)):
                    PredicateType.less,
                # Greater-than
                # ≠ & > ≡ >
                frozenset((PredicateType.not_equal, PredicateType.greater)):
                    PredicateType.greater,
                # ≥ & > ≡ >
                frozenset((PredicateType.greater_equal,
                           PredicateType.greater)):
                    PredicateType.greater,
                # ≥ & ≠ ≡ >
                frozenset((PredicateType.greater_equal,
                           PredicateType.not_equal)):
                    PredicateType.greater,
            }
            operands = frozenset((self, other))
            return and_results[operands]

    __and__ = add_and

    def operator(self, a, b):
        operations = {
            PredicateType.equal: operator.eq,
            PredicateType.not_equal: operator.ne,
            PredicateType.less: operator.lt,
            PredicateType.greater: operator.gt,
            PredicateType.less_equal: operator.le,
            PredicateType.greater_equal: operator.ge,
            PredicateType.any: lambda a, b: True,
            PredicateType.none: lambda a, b: False,
        }
        return operations[self](a, b)
