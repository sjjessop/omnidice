
from fractions import Fraction

import pytest

from omnidice.dice import d6
from omnidice.drv import p
from omnidice.pools import PlainResult, drop_highest, drop_lowest
from omnidice.pools import pool as Pool
from omnidice.systems import over_the_edge as ote

@pytest.mark.parametrize('dice', range(1, 7))
def test_total(dice):
    """
    Get the result of a roll.
    """
    assert ote.total(dice).is_same(dice @ d6)
    assert ote.total(dice, bonus=0).is_same(dice @ d6)
    assert ote.total(dice, bonus=1).is_same(
        drop_lowest(1, d6, count=dice+1).apply(sum)
    )
    assert ote.total(dice, bonus=-1).is_same(
        drop_highest(1, d6, count=dice+1).apply(sum),
    )

def test_empty():
    """
    Empty pools make no sense. Especially with the "Botch" and/or "Unstoppable
    Six" optional rules, since no dice is simultaneously all 1s and all 6s.
    """
    with pytest.raises(ValueError):
        ote.total(0)
    with pytest.raises(ValueError):
        ote.pool(0)

@pytest.mark.parametrize('dice', range(1, 7))
def test_pool(dice):
    """
    Get the individual dice, for playing with the optional rules.
    """
    assert ote.pool(dice).is_same(Pool(d6, count=dice))
    assert ote.pool(dice, bonus=0).is_same(Pool(d6, count=dice))
    assert ote.pool(dice, bonus=1).is_same(
        drop_lowest(1, d6, count=dice+1)
    )
    assert ote.pool(dice, bonus=-1).is_same(
        drop_highest(1, d6, count=dice+1)
    )

def test_botch():
    """
    total() reports a botch as -1. pool() reports a single -1.
    """
    # Probabilities for botch on 2 dice, with bonus/penalty
    normal_prob = Fraction(1, 36)
    bonus_prob = Fraction(1, 216)
    pen_prob = Fraction(1 + 3 * 5, 216)
    assert ote.total(2, botch=True).is_same(
        (2 @ d6).apply(lambda x: -1 if x == 2 else x)
    )
    assert p(ote.total(2, bonus=0, botch=True) == -1) == normal_prob
    assert p(ote.total(2, bonus=1, botch=True) == -1) == bonus_prob
    assert p(ote.total(2, bonus=-1, botch=True) == -1) == pen_prob

    botch = PlainResult(-1)
    assert ote.pool(2, botch=True).is_same(
        Pool(d6, d6).apply(lambda x: botch if x == PlainResult(1, 1) else x)
    )
    assert p(ote.pool(2, bonus=0, botch=True) == botch) == normal_prob
    assert p(ote.pool(2, bonus=1, botch=True) == botch) == bonus_prob
    assert p(ote.pool(2, bonus=-1, botch=True) == botch) == pen_prob

def test_explode():
    """
    The "Blowing the top" rule doesn't require any special result values, it
    just adds an exploding d6 sometimes.
    """
    # Probabilities for explosion on 2 dice, with bonus/penalty
    normal_prob = Fraction(1, 36)
    bonus_prob = Fraction(1 + 3 * 5, 216)
    pen_prob = Fraction(1, 216)

    def low(result):
        return result < 12
    def high(result):
        return result >= 12

    assert ote.total(2, explode=True).given(low).is_same(
        (2 @ d6).given(low)
    )
    assert ote.total(2, explode=True).given(high).is_same(
        d6.explode() + 12,
    )
    assert ote.total(2, explode=5).given(low).is_same(
        (2 @ d6).given(low)
    )
    assert ote.total(2, explode=5).given(high).is_same(
        d6.explode(rerolls=5) + 12,
    )
    assert p(ote.total(2, bonus=0, explode=True) > 12) == normal_prob
    assert p(ote.total(2, bonus=1, explode=True) > 12) == bonus_prob
    assert p(ote.total(2, bonus=-1, explode=True) > 12) == pen_prob

    def short(result):
        return len(result.values) == 2
    def long(result):
        return len(result.values) == 3

    assert ote.pool(2, explode=True).given(short).is_same(
        Pool(d6, d6).given(lambda x: x != PlainResult(6, 6))
    )
    assert ote.pool(2, explode=True).given(long).is_same(
        (d6.explode().apply(lambda x: PlainResult(6, 6, x))),
    )
    assert ote.pool(2, explode=5).given(short).is_same(
        Pool(d6, d6).given(lambda x: x != PlainResult(6, 6))
    )
    assert ote.pool(2, explode=5).given(long).is_same(
        (d6.explode(rerolls=5).apply(lambda x: PlainResult(6, 6, x))),
    )
    assert p(ote.pool(2, bonus=0, explode=True).apply(sum) > 12) == normal_prob
    assert p(ote.pool(2, bonus=1, explode=True).apply(sum) > 12) == bonus_prob
    assert p(ote.pool(2, bonus=-1, explode=True).apply(sum) > 12) == pen_prob

@pytest.mark.parametrize('dice', range(1, 4))
def test_unstoppable(dice):
    """
    unstoppable() can be applied to a pool to tell you both the total and the
    existence (or not) of 6s.
    """
    drv = ote.pool(dice).apply(ote.Unstoppable)
    drv2 = ote.pool(dice, unstoppable=True)
    drv3 = drv2.apply(ote.Unstoppable)
    assert drv.is_same(drv2)
    assert drv.is_same(drv3)
    assert drv.apply(lambda x: x.total).is_same(ote.total(dice))
    # Check that you can apply(sum) regardless of options.
    assert drv.apply(lambda x: x.total).is_same(drv.apply(sum))
    assert p(drv.apply(lambda x: not x.unstoppable)) == Fraction(5, 6) ** dice

def test_unstoppable_explosion():
    """
    An exploded 6 counts as unstoppable.
    """
    assert p(
        ote.pool(1, explode=True, unstoppable=True)
        .apply(lambda x: x.unstoppable)
    ) == Fraction(1, 6)
