import pytest
from evesrp.search_filter import PredicateType


class TestPredicateType(object):

    @pytest.fixture(params=list(PredicateType),
                    ids=lambda p: p.name)
    def left(self, request):
        return request.param

    @pytest.fixture(params=list(PredicateType),
                    ids=lambda p: p.name)
    def right(self, request):
        return request.param

    def test_or_equivalence(self, left, right):
        # Test that the various different ways to OR two operands are
        # equivalent (ordering, function vs operator).
        function_left = left.add_or(right)
        function_right = right.add_or(left)
        operator_left = left | right
        operator_right = right | left
        assert function_left == function_right
        assert operator_left == operator_right
        assert function_left == operator_left

    def test_and_equivalence(self, left, right):
        # Same as test_or_equivalence but for AND
        function_left = left.add_and(right)
        function_right = right.add_and(left)
        operator_left = left & right
        operator_right = right & left
        assert function_left == function_right
        assert operator_left == operator_right
        assert function_left == operator_left

    def test_or_results(self, left, right):
        # I am explicitly rewriting the big dict from the add_or method as a
        # series of if-elif-else statements to ensure everything is right (and
        # to hopefully avoid any copy-paste errors. Basically, I'm rewriting a
        # truth-table as a big block of if-else
        if left == PredicateType.greater:
            if right == PredicateType.greater:
                assert left | right == PredicateType.greater
            elif right == PredicateType.less:
                assert left | right == PredicateType.not_equal
            elif right == PredicateType.equal:
                assert left | right == PredicateType.greater_equal
            elif right == PredicateType.not_equal:
                assert left | right == PredicateType.not_equal
            elif right == PredicateType.greater_equal:
                assert left | right == PredicateType.greater_equal
            elif right == PredicateType.less_equal:
                assert left | right == None
        elif left == PredicateType.less:
            if right == PredicateType.greater:
                assert left | right == PredicateType.not_equal
            elif right == PredicateType.less:
                assert left | right == PredicateType.less
            elif right == PredicateType.equal:
                assert left | right == PredicateType.less_equal
            elif right == PredicateType.not_equal:
                assert left | right == PredicateType.not_equal
            elif right == PredicateType.greater_equal:
                assert left | right == None
            elif right == PredicateType.less_equal:
                assert left | right == PredicateType.less_equal
        elif left == PredicateType.equal:
            if right == PredicateType.greater:
                assert left | right == PredicateType.greater_equal
            elif right == PredicateType.less:
                assert left | right == PredicateType.less_equal
            elif right == PredicateType.equal:
                assert left | right == PredicateType.equal
            elif right == PredicateType.not_equal:
                assert left | right == None
            elif right == PredicateType.greater_equal:
                assert left | right == PredicateType.greater_equal
            elif right == PredicateType.less_equal:
                assert left | right == PredicateType.less_equal
        elif left == PredicateType.not_equal:
            if right == PredicateType.greater:
                assert left | right == PredicateType.not_equal
            elif right == PredicateType.less:
                assert left | right == PredicateType.not_equal
            elif right == PredicateType.equal:
                assert left | right == None
            elif right == PredicateType.not_equal:
                assert left | right == PredicateType.not_equal
            elif right == PredicateType.greater_equal:
                assert left | right == None
            elif right == PredicateType.less_equal:
                assert left | right == None
        elif left == PredicateType.greater_equal:
            if right == PredicateType.greater:
                assert left | right == PredicateType.greater_equal
            elif right == PredicateType.less:
                assert left | right == None
            elif right == PredicateType.equal:
                assert left | right == PredicateType.greater_equal
            elif right == PredicateType.not_equal:
                assert left | right == None
            elif right == PredicateType.greater_equal:
                assert left | right == PredicateType.greater_equal
            elif right == PredicateType.less_equal:
                assert left | right == None
        elif left == PredicateType.less_equal:
            if right == PredicateType.greater:
                assert left | right == None
            elif right == PredicateType.less:
                assert left | right == PredicateType.less_equal
            elif right == PredicateType.equal:
                assert left | right == PredicateType.less_equal
            elif right == PredicateType.not_equal:
                assert left | right == None
            elif right == PredicateType.greater_equal:
                assert left | right == None
            elif right == PredicateType.less_equal:
                assert left | right == PredicateType.less_equal

    def test_and_results(self, left, right):
        # Again, rewriting a truth table as an if-else block.
        if left == PredicateType.greater:
            if right == PredicateType.greater:
                assert left & right == PredicateType.greater
            elif right == PredicateType.less:
                assert left & right == None
            elif right == PredicateType.equal:
                assert left & right == None
            elif right == PredicateType.not_equal:
                assert left & right == PredicateType.greater
            elif right == PredicateType.greater_equal:
                assert left & right == PredicateType.greater
            elif right == PredicateType.less_equal:
                assert left & right == None
        elif left == PredicateType.less:
            if right == PredicateType.greater:
                assert left & right == None
            elif right == PredicateType.less:
                assert left & right == PredicateType.less
            elif right == PredicateType.equal:
                assert left & right == None
            elif right == PredicateType.not_equal:
                assert left & right == PredicateType.less
            elif right == PredicateType.greater_equal:
                assert left & right == None
            elif right == PredicateType.less_equal:
                assert left & right == PredicateType.less
        elif left == PredicateType.equal:
            if right == PredicateType.greater:
                assert left & right == None
            elif right == PredicateType.less:
                assert left & right == None
            elif right == PredicateType.equal:
                assert left & right == PredicateType.equal
            elif right == PredicateType.not_equal:
                assert left & right == None
            elif right == PredicateType.greater_equal:
                assert left & right == PredicateType.equal
            elif right == PredicateType.less_equal:
                assert left & right == PredicateType.equal
        elif left == PredicateType.not_equal:
            if right == PredicateType.greater:
                assert left & right == PredicateType.greater
            elif right == PredicateType.less:
                assert left & right == PredicateType.less
            elif right == PredicateType.equal:
                assert left & right == None
            elif right == PredicateType.not_equal:
                assert left & right == PredicateType.not_equal
            elif right == PredicateType.greater_equal:
                assert left & right == PredicateType.greater
            elif right == PredicateType.less_equal:
                assert left & right == PredicateType.less
        elif left == PredicateType.greater_equal:
            if right == PredicateType.greater:
                assert left & right == PredicateType.greater
            elif right == PredicateType.less:
                assert left & right == None
            elif right == PredicateType.equal:
                assert left & right == PredicateType.equal
            elif right == PredicateType.not_equal:
                assert left & right == PredicateType.greater
            elif right == PredicateType.greater_equal:
                assert left & right == PredicateType.greater_equal
            elif right == PredicateType.less_equal:
                assert left & right == PredicateType.equal
        elif left == PredicateType.less_equal:
            if right == PredicateType.greater:
                assert left & right == None
            elif right == PredicateType.less:
                assert left & right == PredicateType.less
            elif right == PredicateType.equal:
                assert left & right == PredicateType.equal
            elif right == PredicateType.not_equal:
                assert left & right == PredicateType.less
            elif right == PredicateType.greater_equal:
                assert left & right == PredicateType.equal
            elif right == PredicateType.less_equal:
                assert left & right == PredicateType.less_equal

