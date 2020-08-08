
from fractions import Fraction

import pytest

from omnidice import pools
from omnidice.dice import d6, d8
from omnidice.drv import DRV, p

def test_plain_result():
    assert pools.PlainResult(1, 2) == pools.PlainResult(2, 1)
    assert pools.PlainResult(1, 1, 2) == pools.PlainResult(1, 2, 1)

    assert pools.PlainResult(1, 1) != pools.PlainResult(1, 2)
    assert pools.PlainResult(1, 1, 2) != pools.PlainResult(1, 2, 2)
    assert pools.PlainResult() != pools.PlainResult(0)

    assert pools.PlainResult(1, 2) != (1, 2)
    assert not pools.PlainResult(1, 2) == (1, 2)

@pytest.mark.parametrize('size', range(0, 11))
def test_result_repr(size):
    """
    Because we have to do some work to set a sensible name for the subclasses
    of PlainResult, we might as well test that.
    """
    values = [1] * size
    assert repr(pools.PlainResult(*values)).startswith('PlainResult(')
    values = [0] * 20
    assert repr(pools.KeepHighest(size)(*values)).startswith(f'Highest_{size}')
    assert repr(pools.KeepLowest(size)(*values)).startswith(f'Lowest_{size}')

def test_pool():
    """
    Take a bucket of DRVs, and consider the results irrespective of order.
    """
    pool = pools.pool(d6, count=2)
    assert p(pool == pools.PlainResult(1, 1)) == Fraction(1, 36)
    assert p(pool == pools.PlainResult(1, 2)) == Fraction(2, 36)

def test_drv_equivalence():
    """
    You can work out some DRV operations "the slow way" using a pool.
    """
    drv1 = d6 + d6
    drv2 = 2 @ d6
    pool_drv = pools.pool(d6, d6).apply(lambda x: sum(x.values))
    pool_drv2 = pools.pool(d6, d6).apply(sum)
    assert drv1.is_same(pool_drv)
    assert drv2.is_same(pool_drv)
    assert pool_drv2.is_same(pool_drv)

def test_result_sum():
    """
    Result is summable, since that's a common final step.
    """
    pool = pools.pool(d6, d6, d8)
    assert pool.apply(sum).is_same(pool.apply(lambda x: sum(x.values)))

def test_mixed_pool():
    """
    Not all dice in pool need to be the same, and you can build up a pool one
    item at a time if you want to.
    """
    pool = pools.pool(d6, d8)
    assert p(pool == pools.PlainResult(1, 1)) == Fraction(1, 48)
    assert p(pool == pools.PlainResult(1, 2)) == Fraction(2, 48)
    assert p(pool == pools.PlainResult(6, 7)) == Fraction(1, 48)
    assert pool.is_same(pools.pool(d6) + d8)

def test_empty_pool():
    """
    An empty pool has one possible value: the empty collection of values.
    """
    empty1 = pools.pool()
    empty2 = pools.pool(d6, count=0)
    assert empty1.is_same(empty2)
    assert empty1.to_dict() == {pools.PlainResult(): 1}

@pytest.mark.parametrize('bad', range(-10, 0))
def test_bad_count(bad):
    """
    Less than empty is not allowed, and neither is count with many DRVs.
    """
    with pytest.raises(ValueError):
        pools.pool(d6, count=bad)
    with pytest.raises(TypeError):
        pools.pool(d6, d8, count=1 - bad)

def test_pool_addition():
    """
    You can add a constant, DRV or pool to a pool, and the effect is of
    including one or more extra dice in the pool.
    """
    pool = pools.pool(d6)
    assert p(pool + 1 == pools.PlainResult(1, 1)) == Fraction(1, 6)
    assert p(pool + d6 == pools.PlainResult(1, 1)) == Fraction(1, 36)
    assert p(pool + pool == pools.PlainResult(1, 1)) == Fraction(1, 36)

def test_keep_highest():
    """
    Roll N, keep the best K of some DRV.
    """
    pool = pools.keep_highest(2, d6, count=3)
    # There are three ways each to get 6, 6, x for x = 1..5, plus 6, 6, 6.
    assert p(pool == pools.PlainResult(6, 6)) == Fraction(16, 216)
    assert p(pool == pools.PlainResult(1, 1)) == Fraction(1, 216)
    # count=1000 acts as a performance test: if the implementation tries to
    # compute all possibilities and then restrict to 0 dice, it will fail.
    pool0 = pools.keep_highest(0, d6, count=1000)
    assert pool0.is_same(DRV({pools.PlainResult(): 1}))
    # Examples from docs
    poolA = pools.keep_highest(2, d6) + d6 + d6
    poolB = pools.pool(d6, count=3)
    poolC = pools.keep_highest(2, d6, count=3)
    poolD = pools.pool(d6, result_type=pools.KeepHighest(2)) + d6 + d6
    assert poolA.is_same(poolB)
    assert not poolA.is_same(poolC)
    assert poolD.is_same(poolC)

def test_keep_lowest():
    """
    Roll N, keep the worst K of some DRV.
    """
    pool = pools.keep_lowest(2, d6, count=3)
    assert p(pool == pools.PlainResult(6, 6)) == Fraction(1, 216)
    # There are three ways each to get 1, 1, x for x = 2..6, plus 1, 1, 1.
    assert p(pool == pools.PlainResult(1, 1)) == Fraction(16, 216)
    pool0 = pools.keep_lowest(0, d6, count=10)
    assert pool0.is_same(DRV({pools.PlainResult(): 1}))

def test_drop_lowest():
    expected = pools.keep_highest(3, d6, count=5)
    assert pools.drop_lowest(2, d6, count=5).is_same(expected)
    assert pools.drop_lowest(2, d6, d6, d6, d6, d6).is_same(expected)

def test_drop_highest():
    expected = pools.keep_lowest(3, d6, count=5)
    assert pools.drop_highest(2, d6, count=5).is_same(expected)
    assert pools.drop_highest(2, d6, d6, d6, d6, d6).is_same(expected)

@pytest.mark.parametrize('bad', range(-10, 0))
def test_bad_keep_numbers(bad):
    """
    You can't pass a negative number of dice to keep, but you can drop more
    dice than you have (resulting in no dice).
    """
    with pytest.raises(ValueError):
        pools.keep_highest(bad, d6, d6)
    with pytest.raises(ValueError):
        pools.keep_lowest(bad, d6, d6)
    assert pools.drop_highest(10, d6, count=-bad).is_same(pools.pool())
    assert pools.drop_lowest(10, d6, count=-bad).is_same(pools.pool())

def test_normalize():
    """
    You can optimize how the pool works in two different ways: by passing a
    class or by passing a function.
    """
    class Keep2(pools.PlainResult):
        def normalize(self, values):
            return sorted(values, reverse=True)[0:2]

    expected = pools.keep_highest(2, d6, count=3)
    assert pools.pool(d6, count=3, result_type=Keep2).is_same(expected)

    assert pools.pool(
        d6, count=3,
        normalize=lambda values: sorted(values, reverse=True)[0:2],
    ).is_same(expected)

def test_custom_pools():
    """
    I'm not sure how useful this is, but for completeness you can add together
    pools with different result types, including those not derived from the
    default result type. The type of the result pool is taken from the pool on
    the left of the addition.
    """
    class Keep2(pools.PlainResult):
        def normalize(self, values):
            return sorted(values, reverse=True)[0:2]

    poolA = pools.pool(d6, count=3, result_type=Keep2)
    poolB = pools.pool(d6, count=2)
    assert all(type(x) is Keep2 for x, prob in (poolA + poolB)._items())
    assert all(len(x.values) == 2 for x, prob in (poolA + poolB)._items())
    assert (poolA + poolB).is_same(pools.pool(d6, count=5, result_type=Keep2))

    for result, _ in (poolB + poolA)._items():
        assert type(result) is pools.PlainResult
    assert all(len(x.values) == 4 for x, prob in (poolB + poolA)._items())
    assert not (poolB + poolA).is_same(poolA + poolB)

    # result_type doesn't even need to inherit from pools.PlainResult. We don't
    # have to consider the order of results insignificant if we don't want to.
    class Ordered(pools.Result):
        def __init__(self, *values):
            self._values = values
        @property
        def values(self):
            return self._values

    assert Ordered(1, 2) == Ordered(1, 2)
    assert not Ordered(1, 2) != Ordered(1, 2)
    assert Ordered(1, 2) != Ordered(2, 1)
    assert not Ordered(1, 2) == Ordered(2, 1)

    poolC = pools.pool(d6, count=3, result_type=Ordered)
    assert len(poolC.to_dict()) == 6 ** 3
    poolD = pools.pool(d6, count=3)
    assert len(poolD.to_dict()) == 56
    assert all(type(x) is Ordered for x, prob in (poolC + poolD)._items())
    assert len((poolC + poolD).to_dict()) == (6 ** 3) * 56
    for result, _ in (poolD + poolC)._items():
        assert type(result) is pools.PlainResult
