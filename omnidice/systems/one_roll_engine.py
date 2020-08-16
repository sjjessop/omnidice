"""
.. versionadded:: 1.2

Wiggle dice
~~~~~~~~~~~

Using wiggle dice involves a choice by the player, after the dice are rolled.
Therefore it's not possible to give the probability distribution of a result
with wiggle dice. There is also some discretion in what counts as "winning" a
contested roll (width vs. height), so you can only reduce it to a probability
of True using custom code for the situation.

Furthermore, you will not necessarily add your wiggle dice to a set. If you
roll 3d+wd and get 10, 1, 1, then you could add the wiggle die to the 10, but
the return value from :func:`matches` has already ignored it. So,
:func:`matches` doesn't return enough information to make the decision.

There are two ways to deal with this:

* Using the :func:`pool` function, you can get the dice result, then write
  whatever logic you want to add wiggle dice to each
  :class:`~omnidice.pools.Result` object via :func:`~omnidice.drv.DRV.apply`,
  then apply :func:`Match.get_matches` afterwards.

* The `wd` parameter to :func:`matches` is the "write whatever logic you want"
  part of the process, and :func:`matches` does the rest. For example here's
  the code for 3d+2wd if your strategy is to set the wiggle die to match the
  highest number you rolled::

    matches(3, wd=lambda x: PlainResult(max(x), max(x)))

  You can also use it to add "Expert Dice" from the game Nemesis, which in
  effect are a restriction of wiggle dice. For example, if you're adding 2
  expert dice set to 10 and 9::

    matches(3, wd=lambda x, y=PlainResult(10, 9): y)

You can also use :func:`pool` to try out rules variants of your own invention
which can remove or change the dice rolled. For example, let's invent a
"penalty die", which means that you must discard the highest number showing.
We can code this like::

    def penalty(result):
        return PlainResult(*(tuple(result)[1:]))

    penalised = pool(...).apply(penalty).apply(Match.get_matches)

Or, for a less serious penalty, perhaps it should instead be subtracted from
the narrowest match (and, in the case you have an unmatched die, discard
that)::

    def penalty(result):
        matches = sorted(
            Match.get_all_sets(result),
            key=lambda x: (x.width, x.height),
        )
        matches[0] = Match(matches[0].width - 1, matches[0].height)
        return PlainResult(*(
            die
            for match in matches
            for die in [match.height] * match.width
        ))
"""

from dataclasses import dataclass
import functools
from itertools import groupby, starmap
from typing import Callable, Iterable, Tuple

from omnidice.dice import d10
from omnidice.drv import DRV
from omnidice.pools import PlainResult, Result
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
        Return a Match object from a group yielded by
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
        Return a tuple of Match objects, one for each of the matches in a dice
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
        Return a tuple of Match objects, one for each of the matches in a dice
        pool result. If there are no matches return a tuple containing a Match
        with width 1 for the highest die (even if it is lower than `diff`).

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
    @classmethod
    def get_all_sets(cls, result: Result) -> Tuple['Match', ...]:
        """
        Return a tuple of Match objects, one for each set of matching dice,
        including each unmatched die as a Match with width 1.

        This may be useful when processing the results of :func:`pool`.

        The warning about result ordering in :func:`get_matches` applies.
        """
        return tuple(
            match for match in starmap(cls.from_group, groupby(result))
        )

@functools.lru_cache()
def _cached_pool(d: int) -> DRV:
    return Pool(d10, count=d)

@functools.lru_cache()
def _cached_pool_hd(d: int, hd: int) -> DRV:
    pl = _cached_pool(d)
    if hd > 0:
        pl += Pool(DRV({10: 1}), count=hd)
    return pl

@functools.lru_cache()
def matches(
    d: int,
    *,
    hd: int = 0,
    wd: Callable[[Result], Result] = None,
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
    :param wd: Function to add wiggle dice. This is passed a Result object,
      and returns a Result object containing the dice to add.
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
    pl = _cached_pool_hd(d, hd)
    if wd is not None:
        # mypy worries we'll assign None back to wd before calling the lambda.
        pl = pl.apply(lambda x: x + wd(x))  # type: ignore
    return pl.apply(lambda result: getter(result, difficulty))

def pool(d: int, *, hd: int = 0, difficulty: int = 1) -> DRV:
    """
    A dice pool, without checking for matches.

    :param d: Number of regular dice.
    :param hd: Number of hard dice.
    :param difficulty: Difficulty (dice below this height are removed). Note
      this is slightly different from :func:`matches`, which allows unmatched
      dice lower than `difficulty` to remain for `allow_highest`. If you want
      that behaviour with :func:`pool`, you need to apply the difficulty when
      you call :func:`Match.get_matches_or_highest` at the end. Removing failed
      dice up front is likely to be more efficient, though.
    """
    pl = _cached_pool_hd(d, hd)
    # We could optimise this with a custom Result type in the pool, but for now
    # it seems safe to rely on the cache and then remove.
    if difficulty == 1:
        return pl
    return pl.apply(lambda x: PlainResult(*(y for y in x if y >= difficulty)))
