
from bisect import bisect_left
import collections
import contextlib
from fractions import Fraction
import functools
from math import gcd, isclose
from numbers import Real
import operator
import os
from random import Random
from types import MappingProxyType
from typing import (
    Any, Callable, Dict, Iterable, Mapping, NoReturn, Optional, Tuple, Union,
)

from .expressions import (
    Atom, AttrExpression, BinaryExpression, ExpressionTree, UnaryExpression,
)

try:
    import numpy as np
    use_numpy = True
except ModuleNotFoundError:
    use_numpy = False

CONVOLVE_OPTIMISATION = True
CONVOLVE_SIZE_LIMIT = 1000

#: The random number generator used as a default by :meth:`DRV.sample()`. If
#: you need reproducible results, then you can call
#: :py:func:`omnidice.drv.rng.seed() <random.seed()>` to set its state.
#:
#: Another way to get reproducible results is to create your own instance of
#: :class:`random.Random` (or a subclass) and pass that to each call to
#: :meth:`DRV.sample()`.
rng = Random(os.urandom(10))

#: Type alias for probabilities, to make signatures more concise. This is
#: needed because mypy doesn't know that :obj:`float` implements
#: :obj:`Real <numbers.Real>`. See https://github.com/python/mypy/issues/3186
Probability = Union[Real, float]

DataPairs = Iterable[Tuple[Any, Probability]]

#: Type alias for a parameter used to create a probability dictionary.
DictData = Union[Mapping[Any, Probability], Iterable[Tuple[Any, Probability]]]

# TODO - consider using https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rv_discrete.html
# It doesn't seem to provide any of the arithmetic, though, so using scipy just
# to generate the cdf seems like overkill.
# https://github.com/jszymon/pacal might do the arithmetic for us, though.
class DRV(object):
    """
    A discrete random variable.

    A DRV has one or more :dfn:`possible values` (or just :dfn:`values`), which
    can be any type. Each possible value has an associated :dfn:`probability`,
    which is a real number between 0 and 1.

    It is strongly recommended that the probabilities add up to exactly 1. This
    might be difficult to achieve with :obj:`float` probabilities, and so this
    class does not enforce that restriction, and makes it possible to sample a
    variable even if the total is not 1. The exact distribution of the samples
    in that case is not specified, only that it will attempt to follow the
    probabilities given. Loosely: if the total is too low then one value's
    probability is rounded up. If the total is too high, then one probability
    is rounded down, and/or one or more values is ignored. These adjustments
    apply only to sampling: the original probabilities are still reported by
    :func:`to_dict()` etc.

    Because :code:`==` is overridden to return a DRV (not a boolean), DRV
    objects are not hashable and cannot be used in a set or as a dictionary
    key, even though the objects are immutable. This means you cannot have a
    DRV as a "possible value" of another DRV.

    DRV also resists being considered in boolean context, so for example you
    cannot in general test whether or not a DRV appears in a list::

      >>> from omnidice.dice import d3, d6
      >>> d3 in [d3, d6]
      True
      >>> d6 in [d3, d6]
      Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "omnidice/drv.py", line 452, in __bool__
          raise ValueError('The truth value of a random variable is ambiguous')
      ValueError: The truth value of a random variable is ambiguous

    This is the same solution used by (for example) :obj:`numpy.array`. If the
    object allowed standard boolean conversion then :code:`d4 in [d3, d6]`
    would be True, which is unacceptably surprising!

    :param distribution: Any value from which a dictionary can be constructed,
      that is a :obj:`Mapping` or :obj:`Iterable` of (value, probability)
      pairs.
    :param tree: The expression from which this object was defined. Currently
      this is used only for the string representation, but might in future
      help support lazily-evaluated DRVs.
    """
    def __init__(
        self,
        distribution: 'DictData',
        *,
        tree: Optional[ExpressionTree] = None,
    ):
        self.__dist = MappingProxyType(dict(distribution))
        # Cumulative distribution. Defer calculating this, because we only
        # need it if the variable is actually sampled. Intermediate values in
        # building up a complex DRV won't ever be sampled, so save the work.
        self.__cdf: Optional[Tuple[Probability, ...]] = None
        self.__cdf_values: Tuple = ()
        self.__lcm: Optional[int] = None
        self.__intvalued: Optional[bool] = None
        self.__expr_tree = tree
        # Computed probabilities can hit 0 due to float underflow, but maybe
        # we should strip out anything with probability 0.
        if not all(0 <= prob <= 1 for value, prob in self._items()):  # type: ignore[operator] # Real is underspecified
            raise ValueError('Probability not in range')
    def __repr__(self) -> str:
        if self.__expr_tree is not None:
            return self.__expr_tree.bracketed()
        return f'DRV({self.__dist})'
    def is_same(self, other: 'DRV') -> bool:
        """
        Return True if `self` and `other` have the same discrete probability
        distribution. Possible values with 0 probability are excluded from the
        comparison.
        """
        values = set(value for value, prob in self._items() if prob != 0)
        othervalues = set(value for value, prob in other._items() if prob != 0)
        if values != othervalues:
            return False
        return all(self.__dist[val] == other.__dist[val] for val in values)
    def is_close(
        self, other: 'DRV', *,
        rel_tol: Optional[float] = None, abs_tol: Optional[float] = None,
    ) -> bool:
        """
        Return True if `self` and `other` have approximately the same discrete
        probability distribution, within the specified tolerances. Possible
        values with 0 probability are excluded from the comparison.

        `rel_tol` and `abs_tol` are applied only to the probabilities, not to
        the possible values. They are defined as for :func:`math.isclose`.
        """
        values = set(value for value, prob in self._items() if prob != 0)
        othervalues = set(value for value, prob in other._items() if prob != 0)
        if values != othervalues:
            return False
        kwargs = {}
        if rel_tol is not None:
            kwargs['rel_tol'] = rel_tol
        if abs_tol is not None:
            kwargs['abs_tol'] = abs_tol
        return all(
            isclose(self.__dist[val], other.__dist[val], **kwargs)
            for val in values
        )
    def to_dict(self) -> Dict[Any, Probability]:
        """
        Return a dictionary mapping all possible values to probabilities.
        """
        return self.__dist.copy()
    def to_pd(self) -> Any:
        """
        Return a :class:`pandas.Series` mapping values to probabilities. The
        series is indexed by the possible values.

        :raises: :class:`ModuleNotFoundError` if pandas is not installed. Note
          that pandas is not a hard dependency of this package. You must
          install it to use this method.
        """
        try:
            import pandas as pd
        except ModuleNotFoundError:
            msg = 'You must install pandas for this optional feature'
            raise ModuleNotFoundError(msg)
        return pd.Series(self.__dist, name='probability')
    def to_table(self, as_float: bool = False) -> str:
        """
        Return a string containing the values and probabilities formatted as a
        table. This is intended only for manually checking small distributions.

        :param as_float: Display probabilites as floating-point. You might find
          floats easier to read by eye.
        """
        if not as_float:
            items = self._items()
        else:
            items = ((v, float(p)) for v, p in self._items())
        with contextlib.suppress(TypeError):
            items = sorted(items)
        return '\n'.join([
            'value\tprobability',
            *(f'{v}\t{p}' for v, p in items),
        ])
    def faster(self) -> 'DRV':
        """
        Return a new DRV, with all probabilities converted to float.
        """
        return DRV(
            {x: float(y) for x, y in self._items()},
            tree=self._combine_post('.faster()'),
        )
    def _items(self) -> DataPairs:
        return self.__dist.items()
    def replace_tree(self, tree: Optional[ExpressionTree]) -> 'DRV':
        """
        Return a new DRV with the same distribution as this DRV, but defined
        from the specified expression.

        This is used for example when some optimisation has computed a DRV one
        way, but we want to represent it the original way.
        """
        return DRV(self.__dist, tree=tree)
    @property
    def cdf(self) -> Tuple[Probability, ...]:
        if self.__cdf is None:
            def iter_totals() -> Iterable[Tuple[Any, Probability]]:
                total: Probability = 0
                for value, probability in self._items():
                    total += probability
                    yield value, total
                # In case of rounding errors
                if total < 1:
                    yield value, 1
            # The type annotations for zip can't sort this one out.
            results: Tuple[Tuple[Any, ...], Tuple[Probability, ...]]
            results = map(tuple, zip(*iter_totals()))  # type: ignore[assignment]
            self.__cdf_values, self.__cdf = results
        return self.__cdf
    @property
    def _lcm(self) -> int:
        def lcm(a: int, b: int) -> int:
            return (a // gcd(a, b)) * b
        if self.__lcm is None:
            result = 1
            for _, prob in self._items():
                if not isinstance(prob, Fraction):
                    result = 0
                    break
                result = lcm(prob.denominator, result)
            self.__lcm = result
        return self.__lcm
    def sample(self, random: Random = rng) -> Any:
        """
        Sample this variable.

        :param random: Random number generator to use. The default is a single
          object shared by all instances of :class:`DRV`.
        :returns: One possible value of this variable.
        """
        sample: Probability
        if self._lcm == 0:
            sample = random.random()
        else:
            sample = Fraction(random.randrange(self._lcm) + 1, self._lcm)
        # The index of the first cumulative probability greater than or equal
        # to our random sample. If there's a repeated probability in the array,
        # that means there was a value with probability 0. So we don't want to
        # select that value even in the very unlikely case of our sample being
        # exactly equal to the repeated probability!
        idx = bisect_left(self.cdf, sample)
        return self.__cdf_values[idx]
    @property
    def _intvalued(self) -> bool:
        if self.__intvalued is None:
            self.__intvalued = all(isinstance(x, int) for x in self.__dist)
        return self.__intvalued
    def __add__(self, right: Any) -> 'DRV':
        """
        Handler for :code:`self + right`.

        Return a random variable which is the result of adding this variable to
        `right`. `right` can be either a constant or another DRV (in which case
        the result assumes that the two random variables are independent).

        As with :meth:`apply()`, probabilities are added up wherever addition
        is many-to-one (for constant numbers it is one-to-one provided overflow
        does not occur).
        """
        while CONVOLVE_OPTIMISATION:
            if not use_numpy:
                break
            if not isinstance(right, DRV):
                break
            product_size = len(self.__dist) * len(right.__dist)
            if product_size <= CONVOLVE_SIZE_LIMIT:
                break
            if not self._intvalued or not right._intvalued:
                break
            def get_range(dist: Iterable[int]) -> range:
                return range(min(dist), max(dist) + 1)
            self_values = get_range(self.__dist)
            right_values = get_range(right.__dist)
            # Very sparse arrays aren't faster to convolve.
            if 100 * product_size <= len(self_values) * len(right_values):
                break
            final_probs = np.convolve(
                np.array(tuple(self.__dist.get(x, 0) for x in self_values)),
                np.array(tuple(right.__dist.get(x, 0) for x in right_values)),
            )
            values = range(
                min(self_values) + min(right_values),
                max(self_values) + max(right_values) + 1,
            )
            filtered: np.ndarray = (final_probs > 0)
            values = np.array(values)[filtered].tolist()
            final_probs = final_probs[filtered]
            return DRV(
                zip(values, final_probs),
                tree=self._combine(self, right, '+'),
            )
        return self._apply2(operator.add, right, connective='+')
    def __sub__(self, right: Any) -> 'DRV':
        """
        Handler for :code:`self - right`.

        Return a random variable which is the result of subtracting `right`
        from this variable. `right` can be either a constant or another DRV (in
        which case the result assumes that the two random variables are
        independent).

        As with :meth:`apply()`, probabilities are added up wherever
        subtraction is many-to-one (for constant numbers it is one-to-one
        provided overflow does not occur).
        """
        if isinstance(right, DRV):
            # So that we get the convolve optimisation
            tree = self._combine(self, right, '-')
            return (self + -right).replace_tree(tree)
        else:
            return self._apply2(operator.sub, right, connective='-')
    def __mul__(self, right: Any) -> 'DRV':
        """
        Handler for :code:`self * right`.

        Return a random variable which is the result of multiplying this
        variable with `right`. `right` can be either a constant or another DRV
        (in which case the result assumes that the two random variables are
        independent).

        As with :meth:`apply()`, probabilities are added up in the case where
        multiplication is not one-to-one (for constant numbers other than zero
        it is one-to-one provided overflow and underflow do not occur).
        """
        return self._apply2(operator.mul, right, connective='*')
    def __rmatmul__(self, left: int) -> 'DRV':
        """
        Handler for :code:`left @ self`.

        Return a random variable which is the result of sampling this variable
        `left` times, and adding the results together.
        """
        if not isinstance(left, int):
            return NotImplemented  # type: ignore[unreachable]
        # Exponentiation by squaring. This isn't massively faster, but does
        # help a bit for hundreds of dice.
        def parts(base: DRV, exponent: int) -> Iterable[DRV]:
            if exponent < 1:
                raise ValueError(exponent)
            while True:
                if exponent % 2 == 1:
                    yield base
                exponent //= 2
                if exponent == 0:
                    break
                base += base
        result = functools.reduce(operator.add, parts(self, left))
        return result.replace_tree(self._combine(left, self, '@'))
    def __matmul__(self, right: 'DRV') -> 'DRV':
        """
        Handler for :code:`self @ right`.

        Return a random variable which is the result of sampling this variable
        once, then adding together that many samples of `right`.

        All possible values of this variable must be of type :obj:`int`.
        """
        if not isinstance(right, DRV):
            return NotImplemented  # type: ignore[unreachable]
        if not all(isinstance(value, int) for value in self.__dist):
            raise TypeError('require integers on LHS of @')
        def iter_drvs() -> Iterable[Tuple[DRV, Probability]]:
            so_far = min(self.__dist) @ right
            for num_dice in range(min(self.__dist), max(self.__dist) + 1):
                if num_dice in self.__dist:
                    yield so_far, self.__dist[num_dice]
                so_far += right
        return DRV.weighted_average(
            iter_drvs(),
            tree=self._combine(self, right, '@'),
        )
    def __truediv__(self, right: Any) -> 'DRV':
        """
        Handler for :code:`self / right`.

        Return a random variable which is the result of floor-dividing this
        variable by `right`. `right` can be either a constant or another DRV
        (in which case the result assumes that the two random variables are
        independent).

        As with :meth:`apply()`, probabilities are added up wherever division
        is many-to-one (for constant numbers other than zero it is one-to-one
        provided overflow and underflow do not occur).

        0 must not be a possible value of `right` (even with probability 0).
        """
        return self._apply2(operator.truediv, right, connective='/')
    def __floordiv__(self, right: Any) -> 'DRV':
        """
        Handler for :code:`self // right`.

        Return a random variable which is the result of dividing this
        variable by `right`. `right` can be either a constant or another DRV
        (in which case the result assumes that the two random variables are
        independent).

        As with :meth:`apply()`, probabilities are added up wherever floor
        division is many-to-one (for numbers it is mostly many-to-one, for
        example :code:`2 // 2 == 1 == 3 // 2`).

        0 must not be a possible value of `right` (even with probability 0).
        """
        return self._apply2(operator.floordiv, right, connective='//')
    def __neg__(self) -> 'DRV':
        """
        Handler for :code:`-self`.

        Return a random variable which is the result of negating the values of
        this variable.

        As with :meth:`apply()`, probabilities are added up wherever negation
        is many-to-one (for numbers it is one-to-one).
        """
        return self.apply(operator.neg, tree=self._combine1('-'))
    def __eq__(self, right: Any) -> 'DRV':  # type: ignore[override]
        """
        Handler for :code:`self == right`.

        Return a random variable which takes value :obj:`True` where `self` is
        equal to `right`, and :obj:`False` otherwise. `right` can be either a
        constant or another DRV (in which case the result assumes that the two
        random variables are independent).

        If either :obj:`True` or :obj:`False` cannot happen then the result
        has only one possible value, with probability 1. There is no possible
        value with probability 0.
        """
        if isinstance(right, DRV):
            small, big = sorted([self, right], key=lambda x: len(x.__dist))
            prob = sum(
                prob * big.__dist.get(val, 0)
                for val, prob in small._items()
            )
        else:
            prob = self.__dist.get(right)
        if not prob:
            return DRV({False: 1})
        if prob >= 1.0:
            return DRV({True: 1})
        return DRV(
            {False: 1 - prob, True: prob},
            tree=self._combine(self, right, '=='),
        )
    def __ne__(self, right: 'DRV') -> 'DRV':  # type: ignore[override]
        """
        Handler for :code:`self != right`.

        Return a random variable which takes value :obj:`True` where `self` is
        not equal to `right`, and :obj:`False` otherwise. `right` can be either
        a constant or another DRV (in which case the result assumes that the
        two random variables are independent).

        If either :obj:`True` or :obj:`False` cannot happen then the result
        has only one possible value, with probability 1. There is no possible
        value with probability 0.
        """
        return (
            (self == right)
            .apply(operator.not_)
            .replace_tree(self._combine(self, right, '!='))
        )
    def __bool__(self) -> NoReturn:
        # Prevent DRVs being truthy, and hence "3 in [DRV({2: 1})]" is true.
        raise ValueError('The truth value of a random variable is ambiguous')
    def __le__(self, right: Any) -> 'DRV':
        """
        Handler for :code:`self <= right`.

        Return a random variable which takes value :obj:`True` where `self` is
        less than or equal to `right`, and :obj:`False` otherwise. `right` can
        be either a constant or another DRV (in which case the result assumes
        that the two random variables are independent).

        If either :obj:`True` or :obj:`False` cannot happen then the result
        has only one possible value, with probability 1. There is no possible
        value with probability 0.
        """
        return self._apply2(operator.le, right, connective='<=')
    def __lt__(self, right: Any) -> 'DRV':
        """
        Handler for :code:`self < right`.

        Return a random variable which takes value :obj:`True` where `self` is
        less than `right`, and :obj:`False` otherwise. `right` can be either a
        constant or another DRV (in which case the result assumes that the two
        random variables are independent).

        If either :obj:`True` or :obj:`False` cannot happen then the result
        has only one possible value, with probability 1. There is no possible
        value with probability 0.
        """
        return self._apply2(operator.lt, right, connective='<')
    def __ge__(self, right: Any) -> 'DRV':
        """
        Handler for :code:`self >= right`.

        Return a random variable which takes value :obj:`True` where `self` is
        greater than or equal to `right`, and :obj:`False` otherwise. `right`
        can be either a constant or another DRV (in which case the result
        assumes that the two random variables are independent).

        If either :obj:`True` or :obj:`False` cannot happen then the result
        has only one possible value, with probability 1. There is no possible
        value with probability 0.
        """
        return self._apply2(operator.ge, right, connective='>=')
    def __gt__(self, right: Any) -> 'DRV':
        """
        Handler for :code:`self > right`.

        Return a random variable which takes value :obj:`True` where `self` is
        greater than `right`, and :obj:`False` otherwise. `right` can be either
        a constant or another DRV (in which case the result assumes that the
        two random variables are independent).

        If either :obj:`True` or :obj:`False` cannot happen then the result
        has only one possible value, with probability 1. There is no possible
        value with probability 0.
        """
        return self._apply2(operator.gt, right, connective='>')
    def explode(self, rerolls: int = 50) -> 'DRV':
        """
        Return a new DRV distributed according to the rules of an "exploding
        die". This means, first roll the die (sample this DRV). If the result
        is not the maximum possible, then keep it. If it is the maximum, then
        roll again and add the new result to the original.

        Because DRV represents only finitely-many possible values, whereas the
        process of rerolling can (with minuscule probability) carry on
        indefinitely, this method imposes an arbitary limit to the number of
        rerolls.

        :param rerolls: The maximum number of rerolls. Set this to 1 for a die
          that can only "explode" once, not indefinitely.
        """
        reroll_value = max(self.__dist.keys())
        reroll_prob = self.__dist[reroll_value]
        each_die = self.to_dict()
        each_die.pop(reroll_value)
        def iter_pairs() -> DataPairs:
            for idx in range(rerolls + 1):
                for value, prob in each_die.items():
                    value += reroll_value * idx
                    prob *= reroll_prob ** idx
                    yield (value, prob)
            yield (reroll_value * (idx + 1), reroll_prob ** (idx + 1))
        postfix = '.explode()' if rerolls == 50 else f'.explode({rerolls!r})'
        return self._reduced(iter_pairs(), tree=self._combine_post(postfix))
    def apply(
        self,
        func: Callable[[Any], Any],
        *,
        tree: Optional[ExpressionTree] = None,
        allow_drv: bool = False,
    ) -> 'DRV':
        """
        Apply a unary function to the values produced by this DRV. If `func` is
        an injective (one-to-one) function, then the probabilities are
        unchanged. If `func` is many-to-one, then the probabilities are added
        together.

        :param func: Function to map the values. Each value `x` is replaced by
          `func(x)`.
        :param tree: the expression from which this object was defined. If
          ``None``, the result DRV is represented by listing out all the values
          and probabilities.
        :param allow_drv: If True, then when `func` returns a DRV, the possible
          values of that DRV are each included in the returned DRV. Recall that
          a DRV cannot be a possible value of the returned DRV, because it is
          not hashable. So, without this option `func` cannot return a DRV.

        .. versionchanged:: 1.1
            Added ``allow_drv`` option.
        """
        return DRV._reduced(self._items(), func, tree=tree, drv=allow_drv)
    def _apply2(
        self,
        func: Callable[[Any, Any], Any],
        right: Any,
        connective: str,
    ) -> 'DRV':
        """Apply a binary function, with the values of this DRV on the left."""
        expr_tree = self._combine(self, right, connective)
        if isinstance(right, DRV):
            return self._cross_reduce(func, right, tree=expr_tree)
        return self.apply(lambda x: func(x, right), tree=expr_tree)
    def _cross_reduce(
        self,
        func: Callable[[Any, Any], Any],
        right: 'DRV',
        tree: Optional[ExpressionTree] = None,
    ) -> 'DRV':
        """
        Take the cross product of self and right, then reduce by applying func.
        """
        return DRV._reduced(
            self._iter_cross(right),
            lambda value: func(*value),
            tree=tree,
        )
    def _iter_cross(
        self, right: 'DRV',
    ) -> Iterable[Tuple[Tuple[Any, Any], Probability]]:
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
    def _reduced(
        iterable: DataPairs,
        func: Callable = lambda x: x,
        tree: Optional[ExpressionTree] = None,
        drv: bool = False,
    ) -> 'DRV':
        distribution: dict = collections.defaultdict(int)
        if not drv:
            # Optimisation does make a difference to e.g. test_convolve
            for value, prob in iterable:
                distribution[func(value)] += prob
        else:
            for value, prob in iterable:
                transformed = func(value)
                if isinstance(transformed, DRV):
                    for value2, prob2 in transformed._weighted_items(prob):
                        distribution[value2] += prob2
                else:
                    distribution[transformed] += prob
        return DRV(distribution, tree=tree)
    @staticmethod
    def weighted_average(
        iterable: Iterable[Tuple['DRV', Probability]],
        *,
        tree: Optional[ExpressionTree] = None,
    ) -> 'DRV':
        """
        Compute a weighted average of DRVs, each with its own probability.

        This is for when you have a set of mutually-exclusive events which can
        happen, and then the final outcome occurs with a different known
        distribution according to which of those events occurs. For example,
        this function is used to implement the ``@`` operator when the
        left-hand-side is a DRV. The first roll determines what the second roll
        will be.

        The DRVs that are averaged together do not need to be disjoint (that
        is, they can have overlapping possible values). Whenever multiple
        events lead to the same final outcome, the probabilities are combined:

        https://en.wikipedia.org/wiki/Law_of_total_probability

        :param iterable: Pairs, each containing a DRV and the probability of
          that DRV being the one selected. The probabilities should add to 1,
          but this is not enforced.
        :param tree: the expression from which this object was defined. If
          ``None``, the result DRV is represented by listing out all the values
          and probabilities.

        .. versionadded:: 1.1
        """
        def iter_pairs() -> DataPairs:
            for drv, weight in iterable:
                yield from drv._weighted_items(weight)
        return DRV._reduced(iter_pairs(), tree=tree)
    def _weighted_items(
        self,
        weight: Probability,
        pred: Callable[[Any], bool] = lambda x: True,
    ) -> DictData:
        for value, prob in self.__dist.items():
            if pred(value):
                yield value, prob * weight
    def given(self, predicate: Callable[[Any], bool]) -> 'DRV':
        """
        Return the conditional probability distribution of this DRV, restricted
        to the possible values for which `predicate` is true.

        For example, :code:`drv.given(lambda x: True)` is the same distribution
        as :code:`drv`, and the following are equivalent to each other::

            d6.given(lambda x: bool(x % 2))
            DRV({1: Fraction(1, 3), 3: Fraction(1, 3), 5: Fraction(1, 3)})

        If `x` is a DRV, and `A` and `B` are predicates, then the conditional
        probability of `A` given `B`, written in probability theory as
        ``p(A(x) | B(x))``, can be computed as :code:`p(x.given(B).apply(A)))`.

        :param predicate: Called with possible values of `self`, and must
          return :obj:`bool` (not just truthy).
        :raises ZeroDivisionError: if the probability of `predicate` being
          true is 0.

        .. versionadded:: 1.1
        """
        total = p(self.apply(predicate))
        if total == 0:
            # Would be raised anyway, but nicer error message
            raise ZeroDivisionError('predicate is True with probability 0')
        return DRV(self._weighted_items(1 / total, predicate))
    @staticmethod
    def _combine(
        left: Any, right: Any, connector: str,
    ) -> Optional[ExpressionTree]:
        """
        Helper for combining two expressions into a combined expression.
        """
        try:
            def unpack(subexpr: Any) -> ExpressionTree:
                if isinstance(subexpr, DRV):
                    if subexpr.__expr_tree is None:
                        raise TypeError
                    return subexpr.__expr_tree
                return Atom(repr(subexpr))
            return BinaryExpression(unpack(left), unpack(right), connector)
        except TypeError:
            return None
    def _combine1(self, connector: str) -> Optional[ExpressionTree]:
        if self.__expr_tree is None:
            return None
        return UnaryExpression(self.__expr_tree, connector)
    def _combine_post(self, postfix: str) -> Optional[ExpressionTree]:
        if self.__expr_tree is None:
            return None
        return AttrExpression(self.__expr_tree, postfix)

def p(var: DRV) -> Probability:
    """
    Return the probability with which `var` takes value True.

    :param var: A boolean-valued random variable, such as those resulting
      from comparison operators.
    """
    if any(type(v) is not bool for v, p in var._items()):
        raise TypeError('Variable must be boolean-valued')
    return var.to_dict().get(True, 0)
