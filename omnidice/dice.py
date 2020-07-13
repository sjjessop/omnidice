
from fractions import Fraction

from .drv import DRV
from .expressions import Atom

class d(DRV):
    """
    One polyhedral die, or in general a uniform discrete random variable over
    the integers from 1 to `sides` inclusive.
    """
    def __init__(self, sides: int):
        prob = Fraction(1, sides)
        super().__init__(
            ((idx, prob) for idx in range(1, sides + 1)),
            tree=Atom(f'd{sides}' if sides <= 100 else f'd({sides})')
        )
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

for idx in range(1, 101):
    globals()[f'd{idx}'] = d(idx)

def roll(drv: DRV):
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
