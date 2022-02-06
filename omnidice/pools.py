"""
.. versionadded:: 1.1

The simplest way that multiple dice are used together in games is by adding
together the results. :obj:`omnidice.drv.DRV` handles this, along with other
basic arithmetic. It can also add the results after applying a function to the
dice rolls, as in systems like Shadowrun or Storyteller where you count
successes. Once DRV combines the values, it "forgets" the separate rolls.

This module provides tools for combining dice together in other ways. A
:obj:`pool` is a :obj:`~omnidice.drv.DRV` which considers all the values
rolled on multiple dice. By default it tracks what numbers show on the dice,
but not which original die rolled which value:

.. code-block:: pycon

    >>> from omnidice.pools import pool as Pool, Result
    >>> from omnidice.dice import d4
    >>> pool = Pool(d4, d4)
    >>> print(pool.to_table())
    value   probability
    PlainResult(values=(1, 1))      1/16
    PlainResult(values=(2, 1))      1/8
    PlainResult(values=(3, 1))      1/8
    PlainResult(values=(4, 1))      1/8
    PlainResult(values=(2, 2))      1/16
    PlainResult(values=(3, 2))      1/8
    PlainResult(values=(4, 2))      1/8
    PlainResult(values=(3, 3))      1/16
    PlainResult(values=(4, 3))      1/8
    PlainResult(values=(4, 4))      1/16
    >>> print(pool.apply(sum).to_table())
    value   probability
    2       1/16
    3       1/8
    4       3/16
    5       1/4
    6       3/16
    7       1/8
    8       1/16
    >>> assert pool.apply(sum).is_same(2 @ d4)

The most common need for this module is "roll and keep", where you keep either
the highest or the lowest few dice and ignore the rest. These uses are supplied
by the fuctions :func:`keep_highest`, :func:`drop_highest` and so on. The
functions return a pool containing only the results of dice kept. You can then
:code:`apply(sum)` as above, if the game system needs the total, or use
:func:`~omnidice.drv.DRV.apply` for any other processing you need to do on each
possible value.

Customised and optimised dice pools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For small dice pools, which are quick to calculate, you can do whatever
processing you need at the end. Suppose we want to take the middle value of
three different dice:

.. code-block:: pycon

    >>> from omnidice.pools import pool
    >>> from omnidice.dice import d4, d6, d8
    >>> print(pool(d4, d6, d8).apply(lambda x: sorted(x.values)[1]).to_table())
    value   probability
    1       1/12
    2       5/24
    3       13/48
    4       13/48
    5       5/48
    6       1/16

To calculate the probabilities, this looks through all possible combinations of
results (88 in this case). It's rare for games to use dice pools too large to
calculate quickly, but this module supports a further optimisation in case it's
needed. You can define a custom result type to collapse together results that
are equivalent in the game system.

For example, consider a system where you roll a big bucket of 20 dice and your
score is the sum of the highest two dice rolled. Not much fun to play with that
many dice, maybe, but we can get the probability distribution by forming a pool
of all the dice and then picking out the two biggest at the end::

    import time

    from omnidice.pools import pool
    from omnidice.dice import d6

    if __name__ == '__main__':
        start = time.perf_counter()
        drv = pool(d6, count=20).apply(lambda x: sum(sorted(x.values)[-2:]))
        print(drv.to_table())
        print(time.perf_counter() - start, 'seconds')

This takes about 9 seconds on my machine, and uses 60MB of RAM. So, we decide
we want to optimise. We can define a class that keeps only the top 2 results as
each die is considered in turn::

    import time

    from omnidice.pools import pool, PlainResult
    from omnidice.dice import d6

    class Keep2(PlainResult):
        def normalize(self, values):
            return sorted(values)[-2:]

    if __name__ == '__main__':
        start = time.perf_counter()
        drv = pool(d6, count=20, result_type=Keep2).apply(sum)
        print(drv.to_table())
        print(time.perf_counter() - start, 'seconds')

This runs in 0.02 seconds and uses 16MB of RAM, which is the same memory as
importing the modules and doing nothing.

As previously mentioned, "keep highest" is a well-known dice system, so you
don't need really need to customise the pool yourself to do that::

    from omnidice import dice, pools
    pools.keep_highest(2, dice.d6, count=20).apply(sum)

Whenever you need a dice pool with special behaviour, you can implement it
either by analysing all the results at the end, or else by customising the
result type to reduce the number of different results. In fact you can also use
a custom result type to *increase* the number of results, if a game system
distinguishes between the numbers showing on different dice.

~~~~
"""

from abc import ABC, abstractmethod
from collections import abc
from dataclasses import dataclass
import itertools
from typing import Any, Callable, Iterable, Iterator, Tuple, Type, TypeVar

from omnidice.drv import DRV

T = TypeVar('T')
# This used to be OK as just T, but it stopped working between mypy 0.782 and
# 0.790. Maybe to do with https://github.com/python/typeshed/pull/4192 or
# something like it.
class LTComparable(ABC):
    @abstractmethod
    def __lt__(self, other: 'LTComparable') -> bool:
        raise NotImplementedError
CT = TypeVar('CT', bound=LTComparable)
RT = TypeVar('RT', bound='Result')

class Result(ABC, abc.Iterable):
    """
    Abstract class to represent one possible value for a pool. Each possible
    value of the pool is a wrapper around a tuple of one possible value from
    each of the DRVs in the pool.

    If you change the constructor signature in a subclass, then you will also
    need to override :func:`__add__`, since it relies on the signature to
    construct a new object.

    Implementations must be (logically) immutable. This class provides equality
    comparisons and a hash based on type and :code:`self.values` only. Derived
    classes might need to override these.
    """
    def __init__(self, *values: Any):
        raise NotImplementedError
    @property
    @abstractmethod
    def values(self) -> Tuple:
        """The wrapped tuple of values."""
        raise NotImplementedError
    def __hash__(self) -> Any:
        return hash(self.values)
    def __eq__(self, other: Any) -> bool:
        return type(self) is type(other) and self.values == other.values
    def __ne__(self, other: Any) -> bool:
        return type(self) != type(other) or self.values != other.values
    @classmethod
    def _from(cls: Type[RT], other: 'Result') -> RT:
        """
        Helper to convert between different Result classes.
        """
        return cls(*other.values)
    def __add__(self: RT, other: Any) -> RT:
        """
        Handler for `self + other`.

        If `other` is a Result, then the result of adding them is of the same
        type as `self`, containing the values from `self` and `other`
        concatenated together. Otherwise, `other` is appended to `self`.
        """
        cls = type(self)
        if isinstance(other, Result):
            return cls(*self.values, *other.values)
        return cls(*self.values, other)
    def __iter__(self) -> Iterator:
        """
        Iterates the values. This allows you to use
        :func:`~omnidice.drv.DRV.apply` on a pool, with functions like
        :func:`sum`, :func:`min`, :func:`max`, or anything else that works on
        each ``Result`` as an iterable.
        """
        return iter(self.values)

@dataclass(frozen=True)
class PlainResult(Result):
    """
    The default implementation of :obj:`Result`.

    The order of the dice in the pool is not significant (that is: we treat the
    dice as indistinguishable even if they don't all have the same probability
    distribution), but the number of times each value occurs in the result is
    significant::

      PlainResult(1, 1, 2) == PlainResult(1, 2, 1)
      PlainResult(1, 1, 2) != PlainResult(1, 2, 2)

    This class supports derived classes, but do not add more fields. This class
    provides polymorphic equality comparisons by comparing ``values``, which
    would go wrong when trying to compare objects of different subclasses if
    they have any additional state.

    :param values: The values on the dice, in any order. They must all be
      comparable with ``<``.
    """
    _values: Tuple
    def __init__(self, *values: Any):
        object.__setattr__(self, '_values', tuple(self.normalize(values)))
    @property
    def values(self) -> Tuple:
        """The values on the dice, in normalized form."""
        return self._values
    def normalize(self, values: Tuple[CT, ...]) -> Iterable[CT]:
        """
        Erase insignificant differences between possible values. Called by the
        constructor.

        The base class sorts the values in descending order.

        When a pool is constructed, each die in turn has its possible values
        appended to each of the Results for the dice so far, and the combined
        Results get normalized at each step.

        So, by cutting down the possible combinations, this is the method that
        makes a pool more efficient than iterating over the full Cartesian
        product of all the dice. Subclasses can override it whenever a game
        system treats more results as equivalent than the base class definition
        above. For example to keep the highest and lowest results in the pool
        (and discard all others), you could define::

            def normalize(self, values):
                if len(values) == 0:
                    return ()
                if len(values) == 1:
                    return (values[0],)
                return (max(values), min(values))

        For a large dice pool this would avoid considering millions of
        combinations of middle values which make no difference.

        Or, to use only the total of your dice pool, just like normal addition
        for DRVs, you could define a PlainResult subclass with::

            def normalize(self, values):
                return (sum(values),)

        That should result in a reasonably efficient calculation, although
        it wouldn't benefit from the :obj:`numpy.convolve` optimisation in DRV.

        .. versionchanged:: 1.2.1
            Fixed signature to reflect that values must be comparable.
        """
        return tuple(sorted(values, reverse=True))
    # Allow polymorphic comparisons. This is mainly useful for .is_same()
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PlainResult):
            return NotImplemented
        return self.values == other.values
    def __ne__(self, other: Any) -> bool:
        if not isinstance(other, PlainResult):
            return NotImplemented
        return self.values != other.values

def pool(
    *drvs: DRV, count: int = 1,
    result_type: Type[Result] = PlainResult,
    normalize: Callable[[Tuple[T, ...]], Iterable[T]] = None,
) -> DRV:
    """
    A "dice pool" as used in various games. This is a DRV whose possible values
    are :obj:`Result` objects representing all the different possible outcomes
    of rolling the specified dice together.

    The members of a pool will be referred to as "dice" for simplicity, but
    they are allowed to be any DRV, not just those from :obj:`omnidice.dice`.

    You can add more dice to a pool after creating it, using the ``+`` operator
    (this is consistent with the usual definition of addition for DRV  because
    adding a single value to a :obj:`Result` is the same as inserting it into
    the Result's values in the correct position). For example, the following
    are equivalent::

      pool(d6, d6, d8)
      pool(d6) + d6 + d8

    .. warning::
        Because of the way ``+`` is defined for DRV and Result, it is also
        possible to add a constant into a pool, or list a constant when
        constructing a pool. If your code is type-checked then the latter is
        forbidden (because the `drvs` parameter is typed as ``DRV``), but if
        your code is not type-checked then you can accidentally write::

          pool(d6, 5)

        when you really meant::

          pool(d6, count=5)

        That said, some systems (for example the One Roll Engine) do include
        constant values in a dice pool. If you're not type-checking your code
        and you want to write ``pool(d10, 10)`` as a more concise equivalent
        to ``pool(d10, DRV({10: 1}))`` or ``pool(d10) + 10``, then who am I to
        stop you?

    There are certain operations of DRV which can also be computed by a pool.
    For example the following are all equivalent::

        d6 + d6
        2 @ d6
        pool(d6, d6).apply(lambda x: sum(x.values))
        pool(d6, d6).apply(sum)

    Generally speaking the pool version will be slower and use more memory,
    since it first calculates all possible combinations of rolls, then later
    discovers that many of them end in the same result. DRV is not highly
    optimised, but it's much better than that:

    .. code-block:: console

      $ python -mtimeit -s "from omnidice import dice, pools" "10 @ dice.d6"
      50 loops, best of 5: 4.69 msec per loop

      $ python -mtimeit -s "from omnidice import dice, pools" "pools.pool(dice.d6, count=10).apply(sum)"
      1 loop, best of 5: 219 msec per loop

      $ python -mtimeit -s "from omnidice import dice, pools" "50 @ dice.d6"
      2 loops, best of 5: 141 msec per loop

      $ python -mtimeit -s "from omnidice import dice, pools" "pools.pool(dice.d6, count=50).apply(sum)"
      MemoryError

    This is why it is useful to define a good :func:`PlainResult.normalize`.

    Any special behaviour of the pool (like keeping only a certain number of
    dice) is encoded in the type of the possible values. Therefore it is not
    recommended to create pools with a mixture of types. Adding together pools
    of different types results in the type on the left, unless you've
    overridden ``__add__`` on your result type to do something different.

    :param drvs: Zero or more DRVs. The pool assumes they are independent
      variables.
    :param count: If you specify exactly one argument for `drvs`, then it is
      repeated this number of times. For example ``pool(d6, count=3)`` is the
      same as ``pool(d6, d6, d6)``.
    :param result_type: The type to use to represent possible values.
    :param normalize: A function to use in place of
      :func:`PlainResult.normalize`. This parameter is an alternative to
      specifying `result_type`, and overrides it if both are specified.
    """
    if count < 0:
        raise ValueError(count)
    summands: Iterable[DRV] = drvs
    if len(drvs) == 1:
        summands = itertools.repeat(drvs[0], count)
    elif count != 1:
        raise TypeError('Must specify exactly 1 DRV to specify count')
    # Empty pool
    if normalize is not None:
        class RType(PlainResult):
            def normalize(self, values):
                return normalize(values)
        result_type = RType
    pool = DRV({result_type(): 1})
    # Would use sum(), but it's allowed to reject non-numeric values
    for drv in summands:
        pool += drv
    if normalize is not None:
        # Get rid of the ad-hoc result type
        return plain(pool)
    return pool

def _how_many(drvs: Tuple[DRV, ...], count: int = 1) -> int:
    """
    Helper to count how many dice are in the specified params.
    """
    if len(drvs) == 1:
        return count
    return len(drvs)

def plain(pl: DRV) -> DRV:
    """
    Convert all possible values to :obj:`PlainResult`, thus removing any
    special behaviour of the result_type.
    """
    return pl.apply(PlainResult._from)

def KeepHighest(keep: int) -> Type[PlainResult]:
    """
    Returns a PlainResult subclass which keeps the specified number of dice,
    choosing the highest.
    """
    if keep < 0:
        raise ValueError(keep)
    class Highest(PlainResult):
        def normalize(self, values):
            # Could use heapq.nlargest for this, which would be an optimisation
            # when keep is much smaller than the full size. But because of
            # drop_lowest, and because of the fact we're usually adding one
            # more die at a time, I don't think that's commonly the case.
            # TimSort probably beats a heap sort most of the time.
            return sorted(values, reverse=True)[0:keep]
    Highest.__name__ = Highest.__qualname__ = f'Highest_{keep}'
    return Highest

def KeepLowest(keep: int) -> Type[PlainResult]:
    """
    Returns a PlainResult subclass which keeps the specified number of dice,
    choosing the lowest.
    """
    if keep < 0:
        raise ValueError(keep)
    class Lowest(PlainResult):
        def normalize(self, values):
            if keep == 0:
                return ()
            else:
                return sorted(values, reverse=True)[-keep:]
    Lowest.__name__ = Lowest.__qualname__ = f'Lowest_{keep}'
    return Lowest

def keep_highest(keep: int, *drvs: DRV, count: int = 1) -> DRV:
    """
    Return a pool in which a number of dice equal to `keep` are are retained,
    and any additional dice are ignored. The dice with the highest results are
    kept. If there are fewer than `keep` dice in the pool then all are kept.

    For example, to get the distribution of rolling 5d6 and adding the highest
    two, do::

        keep_highest(2, d6, count=5).apply(sum)

    To avoid possible confusion, the property of "keeping the highest" does not
    apply if you later add more dice to the pool. For example,
    :code:`keep_highest(2, d6) + d6 + d6` is equivalent to
    :code:`pool(d6, count=3)`, not :code:`keep_highest(2, d6, count=3)`.

    You can get a pool with the other behaviour by doing this instead::

        pool(*drvs, count=count, result_type=KeepHighest(keep))
    """
    return plain(pool(*drvs, count=count, result_type=KeepHighest(keep)))

def keep_lowest(keep: int, *drvs: DRV, count: int = 1) -> DRV:
    """
    As :func:`keep_highest`, except the lowest results are kept.
    """
    return plain(pool(*drvs, count=count, result_type=KeepLowest(keep)))

def drop_highest(drop: int, *drvs: DRV, count: int = 1) -> DRV:
    """
    Return a pool in which a number of dice equal to `drop` are are ignored,
    and any additional dice are retained. The dice with the highest results are
    dropped. If there are fewer than `drop` dice in the pool then none are
    kept.

    The property of "dropping the highest" does not apply if you later add more
    dice to the pool, and you cannot easily get that because this function is
    implemented using :obj:`KeepLowest`.
    """
    num = _how_many(drvs, count=count)
    keep = max(num - drop, 0)
    return plain(pool(*drvs, count=count, result_type=KeepLowest(keep)))

def drop_lowest(drop: int, *drvs: DRV, count: int = 1) -> DRV:
    """
    As :func:`drop_highest`, except the lowest results are dropped.
    """
    num = _how_many(drvs, count=count)
    keep = max(num - drop, 0)
    return plain(pool(*drvs, count=count, result_type=KeepHighest(keep)))
