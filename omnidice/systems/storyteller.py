
from dataclasses import dataclass
from fractions import Fraction
from typing import Union

from ..dice import DRV, d, d10

def standard(target: int) -> DRV:
    """
    Roll a 10-sided dice. Result is 1 (a success) if the score equals or
    exceeds the difficulty `target`. Result is -1 (a botch) if the score is 1.
    Result is 0 (a failure) otherwise.

    :param target: The difficulty of the roll.
    """
    return special(target, rerolls=0)

def special(target: int, rerolls: int = 10) -> DRV:
    """
    If you have a specialty, then on the roll of a 10 you count a success and
    reroll that die. A 1 on the reroll does not count as a botch, and a 10 on
    the reroll can reroll again.

    :param target: The difficulty of the roll.
    :param rerolls: Since a :code:`DRV` can only represent a finite
      distribution, this function must limit the number of rerolls even though
      the system does not. The chance of 10 consecutive 10s (the default) is
      too small to make any practical difference to a game, but you can
      increase the number of rerolls if you prefer. Set to ``0`` to get a
      standard roll with no specialty.
    """
    if target > 10:
        target = 10
    elif target < 2:
        target = 2
    def success(x):
        return int(x >= target)
    if rerolls == 0:
        return d10.apply(lambda x: -1 if x == 1 else success(x))
    first_roll = d(9).apply(lambda x: -1 if x == 1 else success(x))
    # Sneaky trick: by counting a 10 as more than 1 success, this means it's
    # the highest possible result, so explode() treats it as the only thing to
    # reroll. Then we round down the extra fractions at the end.
    reroll = d10.apply(lambda x: 1 + 1e-9 if x == 10 else success(x))
    return DRV.weighted_average((
        (first_roll, Fraction(9, 10)),
        (reroll.explode(rerolls - 1).apply(int) + 1, Fraction(1, 10)),
    ))

@dataclass(frozen=True, order=True)
class RevisedResult(object):
    """
    In Revised editions, rolling more 1s than successes isn't necessarily a
    botch. If you roll any successes then you cannot botch, even if all
    successes are cancelled out and botches remain. This type tracks that when
    added up, so that you can use ``@`` with a :class:`DRV <omnidice.drv.DRV>`
    that has values of this type.
    """
    #: Number of successes minus number of 1s.
    net_success: float
    #: Whether or not there were any success before cancellation by 1s.
    any_success: bool
    # Needed for +, @
    def __add__(self, other: 'RevisedResult') -> 'RevisedResult':
        return RevisedResult(
            self.net_success + other.net_success,
            self.any_success or other.any_success,
        )
    # Needed for *, explode()
    def __mul__(self, other: int):
        return RevisedResult(self.net_success * other, self.any_success)
    def __int__(self) -> int:
        """
        Handler for :code:`int(self)`.

        Return net successes, unless `any_success` is true. In that case return
        at least 0 even if the net successes is negative.
        """
        net = int(self.net_success)
        return max(net, 0) if self.any_success else net

def revised_standard(target: int) -> DRV:
    """
    Return a single die for Revised.

    The possible values are of type :obj:`RevisedResult`. So you can create a
    pool by adding these dice together with ``+`` or ``@`` in the usual way,
    and then call ``.apply(total)`` at the end to tally up the results and
    check for botches.

    :param target: The difficulty of the roll.
    """
    return revised_special(target, rerolls=0)

def revised_special(target: int, rerolls: int = 10) -> DRV:
    """
    A single die for Revised, with a specialty allowing reroll on 10.

    :param target: The difficulty of the roll.
    :param rerolls: Since a :code:`DRV` can only represent a finite
      distribution, this function must limit the number of rerolls even though
      the system does not. The chance of 10 consecutive 10s (the default) is
      too small to make any practical difference to a game, but you can
      increase the number of rerolls if you prefer. Set to ``0`` to get a
      standard roll with no specialty.
    """
    if target > 10:
        target = 10
    elif target < 2:
        target = 2
    def result(x: int, ignore_botch=False) -> RevisedResult:
        if x == 1 and not ignore_botch:
            return RevisedResult(-1, False)
        if x < target:
            return RevisedResult(0, False)
        return RevisedResult(1, True)
    if rerolls == 0:
        return d10.apply(result)
    first_roll = d(9).apply(result)
    # Sneaky trick: by counting a 10 as more than 1 success, this means it's
    # the highest possible result, so explode() treats it as the only thing to
    # reroll. Then we round down the extra fractions at the end.
    reroll = d10.apply(
        lambda x: RevisedResult(1 + 1e-9, True) if x == 10 else result(x, True)
    )
    def rounded(x: RevisedResult) -> RevisedResult:
        return RevisedResult(int(x.net_success) + 1, True)
    return DRV.weighted_average((
        (first_roll, Fraction(9, 10)),
        (reroll.explode(rerolls - 1).apply(rounded), Fraction(1, 10)),
    ))

def total(score: Union[int, RevisedResult]) -> int:
    """
    Return the total number of successes (negative for a botch).

    If `score` is an integer (from a 1st/2nd ed. die from :func:`standard` or
    :func:`special`) then it is returned unmodified.

    If `score` is a :class:`RevisedResult` (from :func:`revised_standard` or
    :func:`revised_special`) then the value returned is the net successes,
    except in the special case where there were successes but they were all
    cancelled out by botches. In that case return 0 even if the net successes
    is negative.
    """
    return int(score)
