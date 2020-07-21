
import timeit
from unittest.mock import patch

import pytest

from omnidice import dice

def run(payload):
    setup = 'from omnidice import dice'
    timer = timeit.Timer(payload, setup, globals=dice.__dict__.copy())
    number, time_taken = timer.autorange()
    results = [time_taken] + timer.repeat(repeat=2, number=number)
    best = min(results) / number
    worst = max(results) / number
    if worst > 2 * best:
        raise ValueError('Results too widely spread')
    noun = 'loop' if number == 1 else 'loops'
    print(f'{number} {noun}, best of {len(results)}: {best} per loop')
    return best

@patch('omnidice.drv.CONVOLVE_OPTIMISATION', False)
def run_without_optimisation(payload):
    print(f'{payload} without optimisation')
    return run(payload), eval(payload, dice.__dict__.copy())

@patch('omnidice.drv.CONVOLVE_OPTIMISATION', True)
def run_with_optimisation(payload):
    print(f'{payload} with optimisation')
    return run(payload), eval(payload, dice.__dict__.copy())

def run_both_ways(payload, factor):
    try:
        import numpy  # noqa: F401 'numpy' imported but unused
    except ModuleNotFoundError:
        factor = 1.3
        print('')
        print('numpy not available: optimisation will have no effect')
    else:
        print('')
    old, old_result = run_without_optimisation(payload)
    new, new_result = run_with_optimisation(payload)
    assert old_result.keys() == new_result.keys()
    for key in old_result.keys():
        assert old_result[key] == pytest.approx(new_result[key])
    assert (new < old * factor)

expressions = (
    # numpy.convolve() seems to very slightly speed up Fraction.
    ('(d(300) + d(300)).to_dict()', 0.95),
    ('(50 @ d6).to_dict()', 0.95),
    # With float instead of Fraction, we expect a good speed increase.
    ('(d(300).faster() + d(300).faster()).to_dict()', 0.15),
    ('(50 @ d6.faster()).to_dict()', 0.3),
    ('(100 @ d6.faster()).to_dict()', 0.1),
    ('(200 @ d6.faster()).to_dict()', 0.04),
    # Sparse inputs are slow to convolve, so make sure they're excluded.
    ('(100 @ (d6 * 50).faster()).to_dict()', 1.3),
    ('(50 @ (d6 * 1000).faster()).to_dict()', 1.3),
    # Subtraction as well as addition
    ('(d(300).faster() - d(300).faster()).to_dict()', 0.2),
)

# Wrapper so that the tests can be run with pytest. Since the filename doesn't
# have "test" in it, pytest will not pick them up automatically.
@pytest.mark.parametrize('expression,factor', expressions)
def test_optimisation(expression, factor):
    run_both_ways(expression, factor)

# Wrapper so that the tests can be run without pytest.
if __name__ == '__main__':
    for expr in expressions:
        run_both_ways(*expr)
