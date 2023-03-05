
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from omnidice.dice import d10
from omnidice.drv import DRV

def standard(target: int) -> DRV:
    """
    Roll a 10-sided dice. Result is 1 (a success) if the score equals or
    exceeds the difficulty `target`. Result is -1 (a botch) if the score is 1.
    Result is 0 (a failure) otherwise.

    :param target: The difficulty of the roll.
    """
    return special(target, rerolls=0)

def special(
    target: int,
    rerolls: int = 10,
    Value: Callable[[float], Any] = lambda x: x,
) -> DRV:
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
    :param Value: The type to use for the possible values in the return DRV.
      Must be constructible from float (not just int as you might expect), and
      must support conversion to int and addition between objects of the type.
    """
    if target > 10:
        target = 10
    elif target < 2:
        target = 2
    def success(x: int) -> Any:
        return Value(int(x >= target))
    def result(x: int) -> Any:
        return Value(-1) if x == 1 else success(x)
    if rerolls == 0:
        return d10.apply(result)
    # Sneaky trick: by counting a 10 as more than 1 success, this means it's
    # the highest possible result, so explode() treats it as the only thing to
    # reroll. Then we round down the extra fractions at the end.
    def rounded(x):
        return Value(int(x) + 1)
    rerolled = (
        d10.apply(lambda x: Value(1 + 1e-9) if x == 10 else success(x))
        .explode(rerolls - 1)
        .apply(rounded)
    )
    return d10.apply(
        lambda x: rerolled if x == 10 else result(x),
        allow_drv=True,
    )

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
    def __init__(self, net_success: float, any_success: Optional[bool] = None):
        if any_success is None:
            any_success = (net_success > 0)
        object.__setattr__(self, 'net_success', net_success)
        object.__setattr__(self, 'any_success', any_success)
    # Needed for +, @
    def __add__(self, other: 'RevisedResult') -> 'RevisedResult':
        return RevisedResult(
            self.net_success + other.net_success,
            self.any_success or other.any_success,
        )
    # Needed for *, explode()
    def __mul__(self, other: int) -> 'RevisedResult':
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
    return special(target, rerolls=rerolls, Value=RevisedResult)

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
