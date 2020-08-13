"""
.. versionadded:: 1.2
"""

from dataclasses import dataclass
import functools
from itertools import groupby, starmap
from typing import Iterable, Tuple

from omnidice.dice import d10
from omnidice.drv import DRV
from omnidice.pools import Result
from omnidice.pools import pool as Pool

@dataclass(frozen=True)
class Match(object):
    """
    Represents one set of matching dice.

    The object can represent a single, unmatched die, but when we talk about
    "matches" we mean sets of 2 or more. We won't dignify a Match object with
    width 1 using the name "match"!

    :param width: Number of dice in the set.
    :param height: Value on the dice in the set.
    """
    width: int
    height: int
    def __repr__(self):
        return f'{self.width}x{self.height}'
    @classmethod
    def from_group(cls, value: int, items: Iterable[int]):
        """
        Return a Match objects from a group yielded by
        :func:`itertools.groupby`.
        """
        return cls(width=len(tuple(items)), height=value)
    @classmethod
    def get_matches(
        cls,
        result: Iterable[int],
        diff: int = 1,
    ) -> Tuple['Match', ...]:
        """
        Return a tuple of Match objects, one for each of the groups in a dice
        pool result. If there are no matches return an empty tuple.

        This function assumes that each dice pool result lists the values in
        sorted order (it doesn't really matter whether ascending or descending,
        although that determines the order the matches are returned).
        :class:`~omnidice.pools.PlainResult` lists them in order, so this
        function works with plain dice pools, but if you try to use this
        function on a pool filled with your own custom result type then bear it
        in mind.
        """
        if diff > 1:
            result = filter(lambda x: x >= diff, result)
        return tuple(
            match for match in starmap(cls.from_group, groupby(result))
            if match.width > 1
        )
    @classmethod
    def get_matches_or_highest(
        cls,
        result: Result,
        diff: int = 1,
    ) -> Tuple['Match', ...]:
        """
        Return a tuple of Match objects, one for each of the groups in a dice
        pool result. If there are no matches return a tuple containing a Match
        with width 1 for the highest die.

        The warning about result ordering in :func:`get_matches` applies.
        """
        if diff > 1:
            goodresult = filter(lambda x: x >= diff, result)
        else:
            goodresult = iter(result)
        return (
            cls.get_matches(goodresult)
            or (cls(width=1, height=max(result)),)
        )

@functools.lru_cache()
def _cached_pool(d: int) -> DRV:
    return Pool(d10, count=d)

@functools.lru_cache()
def matches(
    d: int,
    *,
    hd: int = 0,
    difficulty: int = 1,
    allow_highest: bool = False,
) -> DRV:
    """
    A DRV whose possible values are all the combinations of matches that the
    specified roll can produce.

    Use ``p(matches(...).apply(len) > 0)`` to get the probability of at least
    one successful match, unless you have specified ``allow_highest = True``,
    in which case you need ``p(matches(...).apply(lambda x: x[0].width > 1))``.

    :param d: Number of regular dice.
    :param hd: Number of hard dice.
    :param difficulty: Difficulty (matches below this height don't count).
    :param allow_highest: If False, and there are no matches, the result is an
      empty tuple. If True, and there are no matches, the result is a tuple
      containing a single Match, whose width is 1 and height is the highest die
      rolled.
    """
    if allow_highest:
        getter = Match.get_matches_or_highest
    else:
        getter = Match.get_matches
    pl = _cached_pool(d)
    if hd > 0:
        pl += Pool(DRV({10: 1}), count=hd)
    return pl.apply(lambda result: getter(result, difficulty))
