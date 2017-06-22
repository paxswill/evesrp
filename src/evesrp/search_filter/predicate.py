# -*- coding: UTF-8 -*-
import enum
from evesrp.util import classproperty


class PredicateType(enum.Enum):

    equal = '='

    not_equal = '!='

    less = '<'

    greater = '>'

    less_equal = '<='

    greater_equal = '>='

    @classproperty
    def exact_comparisons(cls):
        return frozenset(
            cls.equal,
            cls.not_equal
        )

    @classproperty
    def range_comparisons(cls):
        return frozenset(
            cls.less,
            cls.greater,
            cls.less_equal,
            cls.greater_equal
        )


    def add_or(self, other):
        # short-circuit tautologies
        if self == other:
            return self
        # this method is also used as the __or__ method, so conform to that
        # spec
        elif not isinstance(other, PredicateType):
            return NotImplemented
        else:
            # keys are sets (frozensets so they're hashable) of the two
            # operations we're ORing, and the value is the logical equivalent.
            # None is a special vaue signifying all values are allowed, and the
            # predicate can be dropped.
            or_results = {
                # Start with the all cases
                # = | ≠ ≡ all
                frozenset((PredicateType.equal, PredicateType.not_equal)):
                    None,
                # ≥ | ≠ ≡ all
                frozenset((PredicateType.greater_equal,
                           PredicateType.not_equal)):
                    None,
                # ≤ | ≠ ≡ all
                frozenset((PredicateType.less_equal, PredicateType.not_equal)):
                    None,
                # ≥ | < ≡ all
                frozenset((PredicateType.greater_equal, PredicateType.less)):
                    None,
                # ≤ | > ≡ all
                frozenset((PredicateType.less_equal, PredicateType.greater)):
                    None,
                # ≥ | ≤ ≡ all
                frozenset((PredicateType.greater_equal,
                           PredicateType.less_equal)):
                    None,
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
        else:
            # Same structure as the or_results map in the add_or method, with
            # the exception that None in this case represents the null set (aka
            # no results possible).
            and_results = {
                # Start with the null cases
                # > & < ≡ null
                frozenset((PredicateType.greater, PredicateType.less)): None,
                # > & = ≡ null
                frozenset((PredicateType.greater, PredicateType.equal)): None,
                # ≤ & > ≡ null
                frozenset((PredicateType.less_equal, PredicateType.greater)):
                    None,
                # < & = ≡ null
                frozenset((PredicateType.less, PredicateType.equal)): None,
                # < & ≥ ≡ null
                frozenset((PredicateType.less, PredicateType.greater_equal)):
                    None,
                # = & ≠ ≡ null
                frozenset((PredicateType.equal, PredicateType.not_equal)):
                    None,
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
