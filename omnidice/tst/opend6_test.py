
from fractions import Fraction
from itertools import product
from typing import Optional, cast

import pytest

from omnidice.dice import d6
from omnidice.drv import DRV, p
from omnidice.pools import PlainResult, pool
from omnidice.systems import opend6

def _check(
    result: DRV, values: DRV, *,
    botch: Fraction = Fraction(1, 6), single: bool = True,
    totals: Optional[DRV] = None, highest: Optional[DRV] = None,
) -> None:
    if totals is None:
        totals = values
    if highest is None:
        highest = totals
    assert result.apply(type).is_same(DRV({opend6.Result: 1}))
    assert result.apply(int).is_same(values)
    # Test the fields of Result
    assert result.apply(lambda x: x.total).is_same(totals)
    assert result.apply(lambda x: x.highest).is_same(highest)
    assert p(result.apply(lambda x: x.botch)) == botch
    assert result.apply(lambda x: x.singleton).is_same(DRV({single: 1}))

def test_wild_die() -> None:
    """The Wild Die is an exploding d6 which botches on 1"""
    _check(
        opend6.wild_die, d6.explode().apply(lambda x: 0 if x == 1 else x),
        totals=d6.explode(),
    )

def test_regular_die() -> None:
    """A regular die is just a d6"""
    _check(opend6.regular_die, d6, botch=Fraction(0))

def test_character_die() -> None:
    """A die bought with a Character Point explodes but doesn't botch"""
    _check(opend6.character_die, d6.explode(), botch=Fraction(0))

def test_dice() -> None:
    """The dice() function returns the summarised data from the rolls."""
    with pytest.raises(ValueError):
        opend6.dice(0)
    # One die is a wild die.
    assert opend6.dice(1).is_same(opend6.wild_die)
    # Two dice is wild + regular, and we need to test that addition is correct.
    expected = DRV.weighted_average((
        (DRV({0: 1}), Fraction(1, 6)),
        (d6 + d6.explode().given(lambda x: cast(int, x) != 1), Fraction(5, 6)),
    ))
    _check(
        opend6.dice(2), expected, single=False,
        totals=d6 + d6.explode(), highest=pool(d6, d6).apply(max),
    )

@pytest.mark.parametrize('reg', range(2, 5))
def test_more_dice(reg: int) -> None:
    """
    Test with higher numbers of dice. Three dice is wild + 2 @ regular, etc.
    """
    def remove_highest(values: PlainResult) -> int:
        return int(sum(values) - max(values))
    not_1 = (1).__ne__
    expected = DRV.weighted_average((
        (pool(d6, count=reg).apply(remove_highest), Fraction(1, 6)),
        (reg @ d6 + d6.explode().given(not_1), Fraction(5, 6)),
    ))
    _check(
        opend6.dice(reg + 1), expected, single=False,
        totals=reg @ d6 + d6.explode(),
        highest=pool(d6, count=reg + 1).apply(max),
    )

def test_dice_char() -> None:
    """The char parameter adds dice bought with Character Points"""
    # I don't think the rules explicity say what happens on a botch, if an
    # exploded character die is the highest score rolled. I'm going to assume
    # that the botch cancels the 6.
    def cancel(value: int) -> int:
        return max(value - 6, 0)
    expected = DRV.weighted_average((
        (d6.explode().apply(cancel), Fraction(1, 6)),
        (
            d6.explode() + d6.explode().given(lambda x: cast(int, x) != 1),
            Fraction(5, 6)
        ),
    ))
    _check(
        opend6.dice(1, char=1), expected, single=False,
        totals=2 @ d6.explode(),
        highest=pool(d6, d6).apply(max),
    )

@pytest.mark.parametrize('reg,char', product(range(0, 2), repeat=2))
def test_more_dice_char(reg: int, char: int) -> None:
    """Test the char parameter with higher numbers of dice"""
    pips = 2
    expected = opend6.wild_die + pips
    if reg > 0:
        expected += reg @ opend6.regular_die
    if char > 0:
        expected += char @ opend6.character_die
    assert opend6.dice(reg + 1, char=char, pips=pips).is_same(expected)

@pytest.mark.parametrize('dice', range(1, 5))
def test_total(dice: int) -> None:
    """The total() function just gives you the overall score"""
    assert opend6.total(dice).is_same(opend6.dice(dice).apply(int))

@pytest.mark.parametrize('dice,pips', product(range(1, 4), range(-3, 4)))
def test_total_pips(dice: int, pips: int) -> None:
    """Option to add/subtract a constant number to the roll"""
    assert opend6.total(dice, pips=pips).is_same(opend6.total(dice) + pips)

@pytest.mark.parametrize('dice,target', product(range(1, 4), [7, 13]))
def test_test(dice: int, target: int) -> None:
    """The test() function compares the total to a target"""
    assert opend6.test(dice, target).is_same(opend6.total(dice) >= target)
    assert opend6.test(dice, target, pips=1).is_same(
        opend6.total(dice) >= target - 1
    )

def test_botch_cancels() -> None:
    """Optionally you can switch off the botch-cancels rule."""
    result = opend6.total(2, botch_cancels=False)
    def botch(x: opend6.TotalWithBotch) -> bool:
        # breakpoint()
        return x.botch
    def nobotch(x: opend6.TotalWithBotch) -> bool:
        return not x.botch
    assert result.apply(lambda x: x.total).is_same(d6 + d6.explode())
    assert p(result.apply(botch)) == Fraction(1, 6)
    assert result.given(botch).apply(lambda x: x.total).is_same(d6 + 1)
    assert result.given(nobotch).apply(lambda x: x.total).is_same(
        d6 + d6.explode().given(lambda x: cast(int, x) != 1)
    )
    # We're happy with the result of total(), so we can use it to check a few
    # results of test()
    for target in range(0, 20, 5):
        success = opend6.test(2, target, botch_cancels=False)
        assert success.apply(lambda x: x.success).is_same(
            result.apply(lambda x: x.total >= target)
        )
