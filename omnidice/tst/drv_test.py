
from fractions import Fraction
from unittest.mock import Mock

import pytest

from omnidice.drv import DRV

def test_sample():
    """
    DRV with float probabilities uses random(). With Fraction uses randrange().
    """
    drv = DRV({True: 0.5, False: 0.5})
    mock = Mock()
    mock.random.return_value = 0.3
    mock.randrange.side_effect = TypeError()
    assert drv.sample(random=mock) is True

    drv = DRV({True: Fraction(1, 2), False: Fraction(1, 2)})
    mock = Mock()
    mock.randrange.return_value = 0
    mock.random.side_effect = TypeError()
    assert drv.sample(random=mock) is True

def test_matmul():
    """
    The @ operator can be used with an integer or DRV on the left, and a DRV
    (but not an integer) on the right.
    """
    drv = DRV({1: 0.5, 2: 0.5})
    assert (1 @ drv).to_dict() == drv.to_dict()
    with pytest.raises(TypeError):
        1.0 @ drv
    with pytest.raises(TypeError):
        drv @ 1
    with pytest.raises(TypeError):
        drv @ 1.0
    assert (drv @ drv).to_dict() == {1: 0.25, 2: 0.375, 3: 0.25, 4: 0.125}
    # The difference with a non-int-valued DRV is you can't put it on the left.
    float_drv = DRV({1.0: 0.5, 2.0: 0.5})
    assert (1 @ float_drv).to_dict() == float_drv.to_dict()
    with pytest.raises(TypeError):
        1.0 @ drv
    with pytest.raises(TypeError):
        float_drv @ 1
    with pytest.raises(TypeError):
        float_drv @ 1.0
    with pytest.raises(TypeError):
        float_drv @ float_drv

def test_bad_probabilities():
    """
    Probabilities passed to the constructor must be between 0 and 1.
    """
    DRV({1: 1.0})
    DRV({1: 1})
    with pytest.raises(ValueError):
        DRV({1: -0.5, 2: 0.5, 3: 0.5, 4: 0.5})
    with pytest.raises(ValueError):
        DRV({1: -0.00000000001, 2: 0.5, 3: 0.5})
    with pytest.raises(ValueError):
        DRV({1: 1.00000000001})
    # They don't have to add up to exactly 1, though
    DRV({1: 0.333, 2: 0.333, 3: 0.333})

def test_convolve():
    """
    There is an optimisation which uses numpy.convolve for large additions.
    Run some bigger jobs, to make sure it all works correctly.
    """
    def check(result):
        result = result.to_dict()
        assert set(result) == set(range(2, 2001))
        for idx in range(2, 1002):
            assert result[idx] == pytest.approx((idx - 1) / 1E6)
        for idx in range(1002, 2001):
            assert result[idx] == pytest.approx((2001 - idx) / 1E6)
    d1000 = DRV({idx: 0.001 for idx in range(1, 1001)})
    check(d1000 + d1000)
    floaty = d1000.apply(float)
    check(floaty + floaty)
    sparse = d1000.apply(lambda x: x * 1000)
    check((sparse + sparse).apply(lambda x: x // 1000))
