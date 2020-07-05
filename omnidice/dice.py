
from fractions import Fraction

from .drv import DRV

class d(DRV):
    def __init__(self, sides):
        prob = Fraction(1, sides)
        super().__init__((idx, prob) for idx in range(1, sides + 1))

for idx in range(1, 101):
    globals()[f'd{idx}'] = d(idx)

def roll(drv):
    return drv.sample()
