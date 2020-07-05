
from bisect import bisect_left
import os
from random import Random


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
    def __init__(self, distribution):
        # TODO - make this an immutable dictionary
        self.__dist = dict(distribution)
        # Cumulative distribution. Defer calculating this, because we only
        # need it if the variable is actually sampled. Intermediate values in
        # building up a complex DRV won't ever be sampled, so save the work.
        self.__cdf = None
    def to_dict(self):
        return self.__dist.copy()
    @property
    def cdf(self):
        if self.__cdf is None:
            def iter_totals():
                total = 0
                for value, probability in self.__dist.items():
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
