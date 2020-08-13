"""
These dice mechanics are from 2nd Edition. I don't have access to a copy of 1st
or 3rd Edition, so if they're different then you're on your own!

The basic mechanic is to roll a number of d6 equal to your trait and add up the
numbers. A "bonus die" means you roll one extra die but discard the lowest. A
"penalty die" means you roll one extra die and discard the highest.
"""

from dataclasses import dataclass
from typing import Any, Iterator, Union

from omnidice.dice import d6
from omnidice.drv import DRV
from omnidice.pools import PlainResult, drop_highest, drop_lowest
from omnidice.pools import pool as Pool

def total(
    dice: int,
    bonus: int = 0,
    *,
    botch: bool = False,
    explode: Union[bool, int] = False,
) -> DRV:
    """
    A DRV with the distribution of the total of the roll. This ignores the
    "Unstoppable Six" optional rule, since it doesn't tell you whether or not
    there were any 6s included in the dice results.

    This gives the same result as calling :code:`pool(...).apply(sum)` with the
    same arguments, but is more efficient in the case where `bonus` is 0.

    :param dice: The score of the trait rolled (excluding bonus/penalty dice).
    :param bonus: The number of bonus dice to roll. A negative number indicates
      penalty dice.
    :param botch: If True, use the "Botches" optional rule. A botch is
      indicated by the value -1.
    :param explode: If truthy, use the "Blowing the Top Off" optional rule. As
      with :func:`DRV.explode() <omnidice.drv.DRV.explode>`, you can specify
      the max number of rerolls to allow. Specifying True means to use the
      default max number of rerolls.
    """
    if bonus == 0:
        result = dice @ d6
        if botch:
            result = result.apply(lambda x: -1 if x == dice else x)
        if explode:
            result = _add_extra(explode, result, 6 * dice)
        return result
    return pool(dice, bonus, botch=botch, explode=explode).apply(sum)

def _get_extra(explode: Union[bool, int]) -> DRV:
    if explode is True:
        return d6.explode()
    return d6.explode(rerolls=explode)

def _add_extra(explode: Union[bool, int], result: DRV, blown: Any) -> DRV:
    extra = _get_extra(explode)
    if type(blown) != int:
        extra = extra.apply(type(blown))
    extra += blown
    return result.apply(lambda x: extra if x == blown else x, allow_drv=True)

def pool(
    dice: int,
    bonus: int = 0,
    *,
    botch: bool = False,
    explode: Union[bool, int] = False,
    unstoppable=False,
) -> DRV:
    """
    A :obj:`~omnidice.pools.pool` with the distribution of all the values on
    the dice.

    Calling ``.apply(sum)`` on the result will produce the same as the result
    of :func:`total` with the same arguments.

    :param dice: The score of the trait rolled (excluding bonus/penalty dice).
    :param bonus: The number of bonus dice to roll. A negative number indicates
      penalty dice.
    :param botch: If True, use the "Botches" optional rule. A botch is
      indicated by :code:`pools.PlainResult(-1)`, as if a single die showed -1.
    :param explode: If truthy, use the "Blowing the Top Off" optional rule. As
      with :func:`DRV.explode() <omnidice.drv.DRV.explode>`, you can specify
      the max number of rerolls to allow. Specifying True means to use the
      default max number of rerolls. The additional exploding die is listed as
      a single extra die, regardless of how many 6s it rolls, so it can have a
      value greater than 6.
    :param unstoppable: If True, use the "Unstoppable Six" rule. Instead of
      showing all the dice results, the possible values of the drv returned are
      instances of :obj:`Unstoppable`.
    """
    if dice == 0:
        raise ValueError('empty pool is not allowed')
    if bonus == 0:
        result = Pool(d6, count=dice)
    elif bonus > 0:
        result = drop_lowest(bonus, d6, count=dice + bonus)
    else:
        penalty = -bonus
        result = drop_highest(penalty, d6, count=dice + penalty)
    if botch:
        botched = PlainResult(*[1] * dice)
        result = result.apply(lambda x: PlainResult(-1) if x == botched else x)
    if explode:
        result = _add_extra(explode, result, PlainResult(*[6] * dice))
    if unstoppable:
        return result.apply(Unstoppable)
    return result

@dataclass(frozen=True)
class Unstoppable:
    """
    Compute the total of a roll and also report whether or not it includes an
    "unstoppable six".

    The 2nd edition book is not explicit, but a 6 which is dropped due to a
    penalty die does *not* trigger the Unstoppable Six rule. This matches the
    example given for botches (where a dropped non-1 doesn't prevent a botch)
    and it makes sense that a penalty die shouldn't *increase* your chance of
    unstoppability.

    This can be used as ``pool(...).apply(Unstoppable)``, but if you specify
    ``unstoppable=True`` then you don't need to apply it as well.
    """
    #: Total on the dice.
    total: int
    #: Whether or not any 6s are among the dice.
    unstoppable: bool
    def __init__(self, other: Union[PlainResult, 'Unstoppable']):
        object.__setattr__(self, 'total', sum(other))
        if isinstance(other, Unstoppable):
            object.__setattr__(self, 'unstoppable', other.unstoppable)
        else:
            object.__setattr__(self, 'unstoppable', 6 in other)
    def __iter__(self) -> Iterator:
        """
        Iteration is allowed so that you can call ``.apply(sum)`` on the DRV
        returned from :func:`pool` regardless of whether ``unstoppable=True``
        was used. It yields only the total, not the boolean flag.
        """
        yield self.total
