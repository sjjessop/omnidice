
from fractions import Fraction
import math
import os
from typing import Dict, Tuple

import pytest

from omnidice.dice import d, d10
from omnidice.drv import DRV, p
from omnidice.pools import PlainResult, keep_lowest
from omnidice.pools import pool as Pool
from omnidice.systems import one_roll_engine as ore

# For speed, don't bother testing the big dice pools.
SIZE_LIMIT = int(os.environ.get('OMNIDICE_TST_ORE_SIZE_LIMIT', 4))

# The numbers of distinct results for each dice pool size,
# counted the slow way. They were calculated to *include* the width-1 match
# in case no matches are rolled.
expected_counts = {
    1: 10,
    2: 19,
    3: 28,
    4: 82,
    5: 181,
    6: 445,
    7: 994,
    8: 2158,
    9: 4477,
}

@pytest.mark.parametrize('dice, count', expected_counts.items())
def test_matches(dice: int, count: int) -> None:
    """
    Check that we have the right number of values in each distribution.
    """
    # Brute-forcing what all the possible values are would take a while, and
    # any optimisation makes it less clear the test is correct, so just test
    # that the number of results is right.
    if SIZE_LIMIT >= dice:
        # Basic counts are for allow_highest
        assert len(ore.matches(d=dice, allow_highest=True).to_dict()) == count
        # If you don't allow_highest then (11 - dice) different "highest
        # unmatched" results are all replaced with one "failed" result.
        # (11 - dice) is because with 2 dice the highest must be 2-10, etc.
        assert len(ore.matches(d=dice).to_dict()) == count - (11 - dice) + 1

def test_allow_highest() -> None:
    """
    Check that allow_highest has the correct effect.
    """
    assert ore.matches(1).is_same(DRV({(): 1}))
    assert ore.matches(1, allow_highest=False).is_same(DRV({(): 1}))
    allowed = ore.matches(1, allow_highest=True)
    assert allowed.apply(lambda x: x[0].width).is_same(DRV({1: 1}))
    assert allowed.apply(lambda x: x[0].height).is_same(d10)
    # This isn't documented, but the repr() format for Matches is
    # "widthxheight", as used in the rules.
    assert allowed.apply(repr).is_same(d10.apply(lambda x: f'(1x{x},)'))

def test_hard() -> None:
    """
    Hard dice can be added to the pool.
    """
    # With d+hd, there's only one possible way to get a match
    assert ore.matches(d=1, hd=1).is_close(DRV({
        (ore.Match(2, 10),): 1 / 10,
        (): 9 / 10,
    }))
    # 2d + hd is still small enough to figure out easily...
    distribution: Dict[Tuple[ore.Match, ...], float] = {
        (ore.Match(3, 10),): 1 / 100,
        (ore.Match(2, 10),): 18 / 100,
        **{(ore.Match(2, n),): 1 / 100 for n in range(1, 10)},
        (): 72 / 100,
    }
    assert ore.matches(d=2, hd=1).is_close(DRV(distribution))
    # 3d + hd: now we can get two pairs of 10 and something else.
    result = p(ore.matches(d=3, hd=1).apply(len) == 2)
    assert result == pytest.approx(9 * 3 / 1000)

@pytest.mark.parametrize('diff', range(1, 11))
def test_difficulty(diff: int) -> None:
    """
    Setting a difficulty means that some matching sets don't count.
    """
    pool = ore.matches(2, difficulty=diff)
    assert p(pool.apply(len) > 0) == Fraction(11 - diff, 100)
    # You wouldn't normally allow_highest and then require a matching set, but
    # since the probability is the same, we may as well check it.
    pool = ore.matches(2, difficulty=diff, allow_highest=True)
    def success(matches: Tuple[ore.Match]) -> bool:
        return matches[0].width > 1
    assert p(pool.apply(success)) == Fraction(11 - diff, 100)
    # If you rolled at least one die over the difficulty, but still failed,
    # then the difficulty actually makes no difference to your distribution.
    def failure(matches: Tuple[ore.Match]) -> bool:
        return not success(matches) and matches[0].height >= diff
    assert pool.given(failure).is_same(
        ore.matches(2, allow_highest=True).given(failure)
    )
    # That leaves cases where all dice were less than the difficulty. The
    # probability and distribution of that is an easy one to check.
    def woeful(matches: Tuple[ore.Match]) -> bool:
        return not success(matches) and matches[0].height < diff
    assert p(pool.apply(woeful)) == Fraction(diff - 1, 10)**2
    if diff > 1:
        assert pool.given(woeful).apply(
            lambda matches: matches[0].height
        ).is_same(
            # The maximum of uniformly-distributed values below diff.
            Pool(d(diff - 1), count=2).apply(max)
        )

def test_belle_curve() -> None:
    """
    There's a helpful table in the Godlike rulebook giving the probability of
    at least one match. This is based on the number of possible permutations of
    unmatched numbers that can show up. There's only so many ways that N values
    in the range 1-10 can all be different from each other.
    """
    assert p(ore.matches(1).apply(len) > 0) == 0
    assert p(ore.matches(2).apply(len) > 0) == Fraction(1, 10)
    assert p(ore.matches(3).apply(len) > 0) == Fraction(28, 100)
    # The table is approximate after this
    def combinations(d: int) -> int:
        # This is the combinatorics bit.
        # 10 choose d for the different sets of values, times d! for the orders
        # you could roll them in.
        return math.factorial(10) // math.factorial(10 - d)
    result = p(ore.matches(4).apply(len) > 0)
    assert 0.495 <= result < 0.505  # type: ignore[operator]
    assert 1 - result == Fraction(combinations(4), 10**4)
    if SIZE_LIMIT >= 5:
        result = p(ore.matches(5).apply(len) > 0)
        assert 0.695 <= result < 0.705  # type: ignore[operator]
        assert 1 - result == Fraction(combinations(5), 10**5)
    if SIZE_LIMIT >= 6:
        result = p(ore.matches(6).apply(len) > 0)
        assert 0.845 <= result < 0.855  # type: ignore[operator]
        assert 1 - result == Fraction(combinations(6), 10**6)
    if SIZE_LIMIT >= 7:
        # Book got this one wrong: it says 93% but it's 93.952%
        result = p(ore.matches(7).apply(len) > 0)
        assert 0.93 <= result < 0.94  # type: ignore[operator]
        assert 1 - result == Fraction(combinations(7), 10**7)
    if SIZE_LIMIT >= 8:
        result = p(ore.matches(8).apply(len) > 0)
        assert 0.975 <= result < 0.985  # type: ignore[operator]
        assert 1 - result == Fraction(combinations(8), 10**8)
    if SIZE_LIMIT >= 9:
        result = p(ore.matches(9).apply(len) > 0)
        assert 0.9955 <= result < 0.9965  # type: ignore[operator]
        assert 1 - result == Fraction(combinations(9), 10**9)
    if SIZE_LIMIT >= 10:
        # Book rounded this one wrong too, it's actually 99.963712%
        result = p(ore.matches(10).apply(len) > 0)
        assert 0.9985 <= result  # type: ignore[operator]
        assert 1 - result == Fraction(combinations(10), 10**10)

def test_wiggle() -> None:
    """
    Wiggle dice have the potential to be difficult to implement. The
    documentation lays out what's available to handle them.
    """
    # First example of 'wd' param.
    drv = ore.matches(3, wd=lambda x: PlainResult(max(x), max(x)))
    assert drv.is_same(
        Pool(d10, count=3)
        .apply(lambda x: x + PlainResult(max(x), max(x)))
        .apply(ore.Match.get_matches)
    )
    assert p(drv.apply(lambda x: ore.Match(5, 10) in x)) == Fraction(1, 1000)
    # Second example of 'wd' param
    drv = ore.matches(3, wd=lambda x, y=PlainResult(10, 9): y)
    assert drv.is_same(
        Pool(d10, count=3)
        .apply(lambda x: x + PlainResult(10, 9))
        .apply(ore.Match.get_matches)
    )
    assert p(drv.apply(lambda x: ore.Match(4, 10) in x)) == Fraction(1, 1000)

def test_pool_examples() -> None:
    """
    Check the examples of using pool() do vaguely work.
    """
    # First example of penalty die
    def penalty(result: PlainResult) -> PlainResult:
        return PlainResult(*(tuple(result)[1:]))

    penalised = ore.pool(1).apply(penalty).apply(ore.Match.get_matches)
    assert penalised.is_same(DRV({(): 1}))
    penalised = ore.pool(2).apply(penalty).apply(
        ore.Match.get_matches_or_highest
    )
    assert penalised.apply(len).is_same(DRV({1: 1}))
    assert penalised.apply(lambda x: x[0]).is_same(
        keep_lowest(1, d10, count=2)
        .apply(lambda x: ore.Match(1, next(iter(x))))
    )
    # Second example of penalty die
    def penalty2(result: PlainResult) -> PlainResult:
        matches = sorted(
            ore.Match.get_all_sets(result),
            key=lambda x: (x.width, x.height),
        )
        matches[0] = ore.Match(matches[0].width - 1, matches[0].height)
        return PlainResult(*(
            die
            for match in matches
            for die in [match.height] * match.width
        ))
    penalised = ore.pool(1).apply(penalty2).apply(ore.Match.get_matches)
    assert penalised.is_same(DRV({(): 1}))
    penalised = ore.pool(3).apply(penalty2).apply(ore.Match.get_matches)
    # Discarding from the narrowest match of 3 dice doesn't affect your chance
    # of success! Width 3 becomes width 2, and width 2 means there's an
    # unmatched third die to discard.
    assert p(penalised.apply(len) > 0) == p(ore.matches(3).apply(len) > 0)

def test_pool_params() -> None:
    """Although not used in the examples, test the parameters."""
    assert ore.pool(1, hd=1).apply(ore.Match.get_matches).is_same(
        ore.matches(1, hd=1)
    )
    drv = ore.pool(2, difficulty=8).apply(ore.Match.get_matches)
    assert drv.is_same(DRV({
        (): Fraction(97, 100),
        (ore.Match(2, 8),): Fraction(1, 100),
        (ore.Match(2, 9),): Fraction(1, 100),
        (ore.Match(2, 10),): Fraction(1, 100),
    }))
    drv = ore.pool(2, hd=1, difficulty=8).apply(ore.Match.get_matches)
    assert drv.is_same(DRV({
        (): Fraction(79, 100),
        (ore.Match(2, 8),): Fraction(1, 100),
        (ore.Match(2, 9),): Fraction(1, 100),
        (ore.Match(3, 10),): Fraction(1, 100),
        # 18 ways to roll a 10 plus something that isn't a 10
        (ore.Match(2, 10),): Fraction(18, 100),
    }))
