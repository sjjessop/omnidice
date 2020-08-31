"""
.. versionadded:: 1.2

The `OpenD6 system <http://opend6project.org/?page_id=62>`_ is based on rolling
several d6, adding the results, and comparing to a target difficulty.

Additionally each roll contains one 'wild die', which on 6 explodes but on 1
indicates a botch. The GM chooses between two possible results for a botch,
using the ``botch_cancels`` option.

The player can spend Character Points prior to rolling, to gain additional dice
on the roll. These explode like wild dice, but they don't cause botches.

Finally, the player can spend a Fate Point to double the trait they're rolling
(but not any bonuses from items etc.). There's no option for this in the code:
just increase the dice and pips accordingly.
"""

from dataclasses import dataclass, replace
from typing import Union

from omnidice.dice import DRV, d6
from omnidice.expressions import Atom

@dataclass(frozen=True)
class Result(object):
    """
    The summarised result of a roll.

    :param total: The total showing on all the dice.
    :param botch: Whether or not the wild die rolled a botch.
    :param highest: The highest single die showing. Needed for the option that
      it's cancelled by a botch.
    :param singleton: Whether any dice at all were rolled other than the wild
      die. Needed so as not to double-count when cancelling.
    """
    total: int
    highest: int
    botch: bool
    singleton: bool = True
    def __int__(self) -> int:
        """
        Convert to the total, cancelling out the highest die rolled in the
        event of a botch.
        """
        if self.botch:
            if self.singleton:
                return self.total - self.highest
            return self.total - self.highest - 1
        else:
            return self.total
    def __add__(self, other: Union['Result', int]) -> 'Result':
        if isinstance(other, int):
            return replace(self, total=self.total + other)
        return Result(
            total=self.total + other.total,
            highest=min(6, max(self.highest, other.highest)),
            botch=self.botch or other.botch,
            singleton=False,
        )

@dataclass(frozen=True)
class TotalWithBotch(object):
    """
    The total of a roll, in the case where the :code:`botch_cancels = False`
    option is used, meaning that the GM interprets the effect of botches.
    """
    total: int
    botch: bool

@dataclass(frozen=True)
class TestWithBotch(object):
    """
    The result of a test against a target number, in the case where the
    :code:`botch_cancels = False` option is used, meaning that the GM
    interprets the effect of botches.

    :param success: True if the roll passed, False if failed.
    :param botch: True if the roll was a botch, False if not.
    """
    success: bool
    botch: bool

#: One regular (non-wild) die
regular_die = (
    d6
    .apply(lambda x: Result(x, x, False))
    .replace_tree(Atom('regular_die'))
)

#: One wild die
wild_die = (
    d6.explode()
    .apply(lambda x: Result(x, x, x == 1))
    .replace_tree(Atom('wild_die'))
)

#: One bonus wild die from a character point (which cannot botch)
character_die = (
    d6.explode()
    .apply(lambda x: Result(x, x, False))
    .replace_tree(Atom('character_die'))
)

def dice(d: int, *, pips: int = 0, char: int = 0) -> DRV:
    """
    Summarised results of a roll.

    :param d: Base number of dice (one of which will be wild).
    :param pips: Constant modifier to add to the result.
    :param char: Number of character points spent on additional dice.
    """
    if d < 1:
        raise ValueError(d)
    if char > 0:
        bonuses: Union[DRV, int] = char @ character_die + pips
    else:
        bonuses = pips
    if d == 1:
        return wild_die + bonuses
    return wild_die + (d - 1) @ regular_die + bonuses

def total(
    d: int,
    *, pips: int = 0, char: int = 0, botch_cancels: bool = True,
) -> DRV:
    """
    Total of a roll.

    :param d: Base number of dice (one of which will be wild).
    :param pips: Constant modifier to add to the result.
    :param char: Number of character points spent on additional dice.
    :param botch_cancels: If True then a botch cancels the highest die showing
      (6 in the case a character die has exploded), and the possible values of
      the returned DRV are of type ``int``. If False then the possible values
      are of type :obj:`TotalWithBotch`, and a botch has no effect on the
      total.
    """
    pool = dice(d, pips=pips, char=char)
    if botch_cancels:
        return pool.apply(int)
    else:
        return pool.apply(lambda x: TotalWithBotch(x.total, x.botch))

def test(
    d: int, target: int,
    *, pips: int = 0, char: int = 0, botch_cancels: bool = True,
) -> DRV:
    """
    Result of a roll against a target number.

    :param d: Base number of dice (one of which will be wild).
    :param target: Target number.
    :param pips: Constant modifier to add to the result.
    :param char: Number of character points spent on additional dice.
    :param botch_cancels: If True then a botch cancels the highest die showing
      (6 in the case a character die has exploded), and the possible values of
      the returned DRV are of type ``bool``. If False then the possible values
      are of type :obj:`TestWithBotch`, and a botch has no effect on the total
      before it's compared to the target.
    """
    score = total(d, pips=pips, char=char, botch_cancels=botch_cancels)
    if botch_cancels:
        return score >= target
    else:
        return score.apply(lambda x: TestWithBotch(x.total >= target, x.botch))
