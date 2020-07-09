
from bisect import bisect_left
import collections
import operator
import os
from random import Random

from .expressions import Atom, BinaryExpression, UnaryExpression

# In case anyone wants to run reproducible sequences of samples *without*
# passing the "random" argument every time, it's useful to expose our rng, so
# they can call seed() on it. If we used the global shared rng, then other
# calls to random.seed() or random.random() would interfere with this state.
rng = Random(os.urandom(10))


# TODO - consider using https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rv_discrete.html
# It doesn't seem to provide any of the arithmetic, though, so using scipy just
# to generate the cdf seems like overkill.
# https://github.com/jszymon/pacal might do the arithmetic for us, though.
class DRV(object):
    """
    A discrete random variable
    """
    def __init__(self, distribution, tree=None):
        # TODO - make this an immutable dictionary
        self.__dist = dict(distribution)
        # Cumulative distribution. Defer calculating this, because we only
        # need it if the variable is actually sampled. Intermediate values in
        # building up a complex DRV won't ever be sampled, so save the work.
        self.__cdf = None
        self.__expr_tree = tree
    def __repr__(self):
        if self.__expr_tree is not None:
            return self.__expr_tree.bracketed()
        return f'DRV({self.__dist})'
    def to_dict(self):
        return self.__dist.copy()
    def to_pd(self):
        try:
            import pandas as pd
        except ModuleNotFoundError:
            msg = 'You must install pandas for this optional feature'
            raise ModuleNotFoundError(msg)
        return pd.Series(self.__dist, name='probability')
    def to_table(self, as_float=False):
        if not as_float:
            items = self._items()
        else:
            items = ((v, float(p)) for v, p in self._items())
        return '\n'.join([
            'value\tprobability',
            *(f'{v}\t{p}' for v, p in sorted(items)),
        ])
    def faster(self):
        return DRV({x: float(y) for x, y in self._items()})
    def _items(self):
        return self.__dist.items()
    def replace_tree(self, tree):
        return DRV(self.__dist, tree)
    @property
    def cdf(self):
        if self.__cdf is None:
            def iter_totals():
                total = 0
                for value, probability in self._items():
                    total += probability
                    yield value, total
                # In case of rounding errors
                if total < 1:
                    yield value, 1
            self.__cdf_values, self.__cdf = map(tuple, zip(*iter_totals()))
        return self.__cdf
    def sample(self, random=rng):
        sample = random.random()
        # The index of the first cumulative probability greater than or equal
        # to our random sample. If there's a repeated probability in the array,
        # that means there was a value with probability 0. So we don't want to
        # select that value even in the very unlikely case of our sample being
        # exactly equal to the repeated probability!
        idx = bisect_left(self.cdf, sample)
        return self.__cdf_values[idx]
    def __add__(self, right):
        return self._apply2(operator.add, right, connective='+')
    def __sub__(self, right):
        return self._apply2(operator.sub, right, connective='-')
    def __mul__(self, right):
        return self._apply2(operator.mul, right, connective='*')
    def __rmatmul__(self, left):
        # Handles integer on the left, DRV on the right.
        if not isinstance(left, int):
            return NotImplemented
        if left <= 0:
            raise ValueError(left)
        # Exponentiation by squaring. This isn't massively faster, but does
        # help a bit for hundreds of dice.
        result = DRV({0: 1})
        so_far = self
        original = left
        while True:
            if left % 2 == 1:
                result += so_far
            left //= 2
            if left == 0:
                break
            so_far += so_far
        return result.replace_tree(self.combine(original, self, '@'))
    def __matmul__(self, right):
        # Handles DRV on the left, DRV on the right.
        if not isinstance(right, DRV):
            return NotImplemented
        if not all(isinstance(value, int) for value in self.__dist):
            raise TypeError('require integers on LHS of @')
        def iter_drvs():
            so_far = min(self.__dist) @ right
            for num_dice in range(min(self.__dist), max(self.__dist) + 1):
                if num_dice in self.__dist:
                    yield so_far, self.__dist[num_dice]
                so_far += right
        return DRV._weighted_average(
            iter_drvs(),
            tree=self.combine(self, right, '@'),
        )
    def __truediv__(self, right):
        return self._apply2(operator.truediv, right, connective='/')
    def __floordiv__(self, right):
        return self._apply2(operator.floordiv, right, connective='//')
    def __neg__(self):
        return self.apply(operator.neg, tree=self.combine(self, '-'))
    def __le__(self, right):
        return self._apply2(operator.le, right, connective='<=')
    def __lt__(self, right):
        return self._apply2(operator.lt, right, connective='<')
    def __ge__(self, right):
        return self._apply2(operator.ge, right, connective='>=')
    def __gt__(self, right):
        return self._apply2(operator.gt, right, connective='>')
    def explode(self, rerolls=50):
        reroll_value = max(self.__dist.keys())
        reroll_prob = self.__dist[reroll_value]
        each_die = self.__dist.copy()
        each_die.pop(reroll_value)
        def iter_pairs():
            for idx in range(rerolls + 1):
                for value, prob in each_die.items():
                    value += reroll_value * idx
                    prob *= reroll_prob ** idx
                    yield (value, prob)
            yield (reroll_value * (idx + 1), reroll_prob ** (idx + 1))
        if self.__expr_tree is None:
            tree = None
        elif rerolls == 50:
            tree = Atom(f'{self!r}.explode()')
        else:
            tree = Atom(f'{self!r}.explode({rerolls!r})')
        return self._reduced(iter_pairs(), tree=tree)
    def apply(self, func, tree=None):
        """Apply a unary function to the values produced by this DRV."""
        return DRV._reduced(self._items(), func, tree=tree)
    def _apply2(self, func, right, connective=None):
        """Apply a binary function, with the values of this DRV on the left."""
        expr_tree = self.combine(self, right, connective)
        if isinstance(right, DRV):
            return self._cross_reduce(func, right, tree=expr_tree)
        return self.apply(lambda x: func(x, right), tree=expr_tree)
    def _cross_reduce(self, func, right, tree=None):
        """
        Take the cross product of self and right, then reduce by applying func.
        """
        return DRV._reduced(
            self._iter_cross(right),
            lambda value: func(*value),
            tree=tree,
        )
    def _iter_cross(self, right):
        """
        Take the cross product of self and right, with probabilities assuming
        that the two are independent variables.

        Note that the cross product of an object with itself represents the
        results of sampling it twice, *not* just the pairs (x, x) for each
        possible value!
        """
        for (lvalue, lprob) in self._items():
            for (rvalue, rprob) in right._items():
                yield ((lvalue, rvalue), lprob * rprob)
    @staticmethod
    def _reduced(iterable, func=lambda x: x, tree=None):
        distribution = collections.defaultdict(int)
        for value, prob in iterable:
            distribution[func(value)] += prob
        return DRV(distribution, tree=tree)
    @staticmethod
    def _weighted_average(iterable, tree=None):
        def iter_pairs():
            for drv, weight in iterable:
                yield from drv._weighted_items(weight)
        return DRV._reduced(iter_pairs(), tree=tree)
    def _weighted_items(self, weight):
        for value, prob in self.__dist.items():
            yield value, prob * weight
    @staticmethod
    def combine(*args):
        """
        Helper for combining two expressions into a combined expression.
        """
        for arg in args:
            if arg is None:
                return None
            if isinstance(arg, DRV) and arg.__expr_tree is None:
                return None
        def unpack(subexpr):
            if isinstance(subexpr, DRV):
                return subexpr.__expr_tree
            return Atom(repr(subexpr))
        if len(args) == 2:
            # Unary expression
            subexpr, connective = args
            return UnaryExpression(unpack(subexpr), connective)
        elif len(args) == 3:
            # Binary expression
            left, right, connective = args
            return BinaryExpression(unpack(left), unpack(right), connective)
        raise TypeError
