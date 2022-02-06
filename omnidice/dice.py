
from fractions import Fraction
from typing import Any

from .drv import DRV
from .expressions import Atom

#: A frozenset of integers, giving the numbers of sides of the standard dice
#: provided as module attributes.
preset_dice = frozenset({2, 3, 4, 6, 8, 10, 12, 20, 30, 100, 1000})

class d(DRV):
    """
    One polyhedral die, or in general a uniform discrete random variable over
    the integers from 1 to `sides` inclusive.
    """
    def __init__(self, sides: int):
        if sides <= 0:
            raise ValueError(sides)
        prob = Fraction(1, sides)
        super().__init__(
            ((idx, prob) for idx in range(1, sides + 1)),
            tree=Atom(f'd{sides}' if sides in preset_dice else f'd({sides})')
        )
    @property
    def _intvalued(self):
        return True
    # This is subtle. Because of some rules in Python to help subclasses
    # override operators successfully, we have to suppress the comparisons.
    # Otherwise some_drv < d(6) gets evaluated as d(6) > some_drv, which is
    # functionally equivalent but rather confusing when you see the repr.
    # https://docs.python.org/3/reference/datamodel.html#object.__lt__
    def _compare(self, other, op):
        if isinstance(other, DRV) and not isinstance(other, d):
            return NotImplemented
        return getattr(super(), op)(other)
    def __le__(self, other):
        return self._compare(other, '__le__')
    def __lt__(self, other):
        return self._compare(other, '__lt__')
    def __ge__(self, other):
        return self._compare(other, '__ge__')
    def __gt__(self, other):
        return self._compare(other, '__gt__')
    def __eq__(self, other):
        return self._compare(other, '__eq__')
    def __ne__(self, other):
        return self._compare(other, '__ne__')

def roll(drv: DRV) -> Any:
    """
    Roll the dice indicated by `drv`.

    To specify the random number generator to use, call
    :meth:`drv.sample() <omnidice.drv.DRV.sample()>`.

    :param drv: Dice to roll (that is, the random variable to sample).
    :returns: One possible value of `drv`. If `drv` represents real dice, then
      this will be an integer, but you can have `drv` objects with other types.
      For example, :code:`roll(d6 / 2)` returns `float`.
    """
    return drv.sample()

# These need to match preset_dice, but if we assign them in a loop then mypy
# gets upset, because it doesn't know what attributes our module has.
d2 = d(2)
d3 = d(3)
d4 = d(4)
d6 = d(6)
d8 = d(8)
d10 = d(10)
d12 = d(12)
d20 = d(20)
d30 = d(30)
d100 = d(100)
d1000 = d(1000)
