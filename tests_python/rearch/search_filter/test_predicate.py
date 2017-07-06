import pytest
from evesrp.search_filter import PredicateType


@pytest.fixture(params=list(PredicateType),
                ids=lambda p: p.name)
def left(request):
    return request.param


@pytest.fixture(params=list(PredicateType),
                ids=lambda p: p.name)
def right(request):
    return request.param


def test_or_equivalence(left, right):
    # Test that the various different ways to OR two operands are
    # equivalent (ordering, function vs operator).
    function_left = left.add_or(right)
    function_right = right.add_or(left)
    operator_left = left | right
    operator_right = right | left
    assert function_left == function_right
    assert operator_left == operator_right
    assert function_left == operator_left


def test_and_equivalence(left, right):
    # Same as test_or_equivalence but for AND
    function_left = left.add_and(right)
    function_right = right.add_and(left)
    operator_left = left & right
    operator_right = right & left
    assert function_left == function_right
    assert operator_left == operator_right
    assert function_left == operator_left


@pytest.mark.parametrize('predicate', list(PredicateType),
                         ids=lambda p: p.name)
@pytest.mark.parametrize('left', (0, 1, 2))
@pytest.mark.parametrize('right', (0, 1, 2))
def test_operator(predicate, left, right):
    if left == PredicateType.greater:
        assert predicate.operator(left, right) == (left > right)
    elif left == PredicateType.less:
        assert predicate.operator(left, right) == (left < right)
    elif left == PredicateType.equal:
        assert predicate.operator(left, right) == (left == right)
    elif left == PredicateType.not_equal:
        assert predicate.operator(left, right) == (left != right)
    elif left == PredicateType.greater_equal:
        assert predicate.operator(left, right) == (left >= right)
    elif left == PredicateType.less_equal:
        assert predicate.operator(left, right) == (left <= right)
    elif left == PredicateType.any:
        assert predicate.operator(left, right)
    elif left == PredicateType.none:
        assert not predicate.operator(left, right)


# The `assert False` lines below are to ensure that there is no fall-though of
# any possible cases


def test_or_results(left, right):
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
            assert left | right == PredicateType.any
        elif right == PredicateType.any:
            assert left | right == PredicateType.any
        elif right == PredicateType.none:
            assert left | right == PredicateType.greater
        else:
            assert False
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
            assert left | right == PredicateType.any
        elif right == PredicateType.less_equal:
            assert left | right == PredicateType.less_equal
        elif right == PredicateType.any:
            assert left | right == PredicateType.any
        elif right == PredicateType.none:
            assert left | right == PredicateType.less
        else:
            assert False
    elif left == PredicateType.equal:
        if right == PredicateType.greater:
            assert left | right == PredicateType.greater_equal
        elif right == PredicateType.less:
            assert left | right == PredicateType.less_equal
        elif right == PredicateType.equal:
            assert left | right == PredicateType.equal
        elif right == PredicateType.not_equal:
            assert left | right == PredicateType.any
        elif right == PredicateType.greater_equal:
            assert left | right == PredicateType.greater_equal
        elif right == PredicateType.less_equal:
            assert left | right == PredicateType.less_equal
        elif right == PredicateType.any:
            assert left | right == PredicateType.any
        elif right == PredicateType.none:
            assert left | right == PredicateType.equal
        else:
            assert False
    elif left == PredicateType.not_equal:
        if right == PredicateType.greater:
            assert left | right == PredicateType.not_equal
        elif right == PredicateType.less:
            assert left | right == PredicateType.not_equal
        elif right == PredicateType.equal:
            assert left | right == PredicateType.any
        elif right == PredicateType.not_equal:
            assert left | right == PredicateType.not_equal
        elif right == PredicateType.greater_equal:
            assert left | right == PredicateType.any
        elif right == PredicateType.less_equal:
            assert left | right == PredicateType.any
        elif right == PredicateType.any:
            assert left | right == PredicateType.any
        elif right == PredicateType.none:
            assert left | right == PredicateType.not_equal
        else:
            assert False
    elif left == PredicateType.greater_equal:
        if right == PredicateType.greater:
            assert left | right == PredicateType.greater_equal
        elif right == PredicateType.less:
            assert left | right == PredicateType.any
        elif right == PredicateType.equal:
            assert left | right == PredicateType.greater_equal
        elif right == PredicateType.not_equal:
            assert left | right == PredicateType.any
        elif right == PredicateType.greater_equal:
            assert left | right == PredicateType.greater_equal
        elif right == PredicateType.less_equal:
            assert left | right == PredicateType.any
        elif right == PredicateType.any:
            assert left | right == PredicateType.any
        elif right == PredicateType.none:
            assert left | right == PredicateType.greater_equal
        else:
            assert False
    elif left == PredicateType.less_equal:
        if right == PredicateType.greater:
            assert left | right == PredicateType.any
        elif right == PredicateType.less:
            assert left | right == PredicateType.less_equal
        elif right == PredicateType.equal:
            assert left | right == PredicateType.less_equal
        elif right == PredicateType.not_equal:
            assert left | right == PredicateType.any
        elif right == PredicateType.greater_equal:
            assert left | right == PredicateType.any
        elif right == PredicateType.less_equal:
            assert left | right == PredicateType.less_equal
        elif right == PredicateType.any:
            assert left | right == PredicateType.any
        elif right == PredicateType.none:
            assert left | right == PredicateType.less_equal
        else:
            assert False
    elif left == PredicateType.any:
        assert left | right == PredicateType.any
    elif left == PredicateType.none:
        assert left | right == right
    else:
        assert False


def test_and_results(left, right):
    # Again, rewriting a truth table as an if-else block.
    if left == PredicateType.greater:
        if right == PredicateType.greater:
            assert left & right == PredicateType.greater
        elif right == PredicateType.less:
            assert left & right == PredicateType.none
        elif right == PredicateType.equal:
            assert left & right == PredicateType.none
        elif right == PredicateType.not_equal:
            assert left & right == PredicateType.greater
        elif right == PredicateType.greater_equal:
            assert left & right == PredicateType.greater
        elif right == PredicateType.less_equal:
            assert left & right == PredicateType.none
        elif right == PredicateType.any:
            assert left & right == PredicateType.greater
        elif right == PredicateType.none:
            assert left & right == PredicateType.none
        else:
            assert False
    elif left == PredicateType.less:
        if right == PredicateType.greater:
            assert left & right == PredicateType.none
        elif right == PredicateType.less:
            assert left & right == PredicateType.less
        elif right == PredicateType.equal:
            assert left & right == PredicateType.none
        elif right == PredicateType.not_equal:
            assert left & right == PredicateType.less
        elif right == PredicateType.greater_equal:
            assert left & right == PredicateType.none
        elif right == PredicateType.less_equal:
            assert left & right == PredicateType.less
        elif right == PredicateType.any:
            assert left & right == PredicateType.less
        elif right == PredicateType.none:
            assert left & right == PredicateType.none
        else:
            assert False
    elif left == PredicateType.equal:
        if right == PredicateType.greater:
            assert left & right == PredicateType.none
        elif right == PredicateType.less:
            assert left & right == PredicateType.none
        elif right == PredicateType.equal:
            assert left & right == PredicateType.equal
        elif right == PredicateType.not_equal:
            assert left & right == PredicateType.none
        elif right == PredicateType.greater_equal:
            assert left & right == PredicateType.equal
        elif right == PredicateType.less_equal:
            assert left & right == PredicateType.equal
        elif right == PredicateType.any:
            assert left & right == PredicateType.equal
        elif right == PredicateType.none:
            assert left & right == PredicateType.none
        else:
            assert False
    elif left == PredicateType.not_equal:
        if right == PredicateType.greater:
            assert left & right == PredicateType.greater
        elif right == PredicateType.less:
            assert left & right == PredicateType.less
        elif right == PredicateType.equal:
            assert left & right == PredicateType.none
        elif right == PredicateType.not_equal:
            assert left & right == PredicateType.not_equal
        elif right == PredicateType.greater_equal:
            assert left & right == PredicateType.greater
        elif right == PredicateType.less_equal:
            assert left & right == PredicateType.less
        elif right == PredicateType.any:
            assert left & right == PredicateType.not_equal
        elif right == PredicateType.none:
            assert left & right == PredicateType.none
        else:
            assert False
    elif left == PredicateType.greater_equal:
        if right == PredicateType.greater:
            assert left & right == PredicateType.greater
        elif right == PredicateType.less:
            assert left & right == PredicateType.none
        elif right == PredicateType.equal:
            assert left & right == PredicateType.equal
        elif right == PredicateType.not_equal:
            assert left & right == PredicateType.greater
        elif right == PredicateType.greater_equal:
            assert left & right == PredicateType.greater_equal
        elif right == PredicateType.less_equal:
            assert left & right == PredicateType.equal
        elif right == PredicateType.any:
            assert left & right == PredicateType.greater_equal
        elif right == PredicateType.none:
            assert left & right == PredicateType.none
        else:
            assert False
    elif left == PredicateType.less_equal:
        if right == PredicateType.greater:
            assert left & right == PredicateType.none
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
        elif right == PredicateType.any:
            assert left & right == PredicateType.less_equal
        elif right == PredicateType.none:
            assert left & right == PredicateType.none
    elif left == PredicateType.any:
        assert left & right == right
    elif left == PredicateType.none:
        assert left & right == PredicateType.none
    else:
        assert False
