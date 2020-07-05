
import pytest

from omnidice import dice

def test_d6():
    """Basic usage of a die"""
    d6 = dice.d6
    distribution = d6.to_dict()
    assert distribution.keys() == {1, 2, 3, 4, 5, 6}
    assert sum(distribution.values()) == pytest.approx(1)
    assert len(set(distribution.values())) == 1
    # Check that to_dict() doesn't allow mutating the original
    distribution[1] = 0
    assert d6.to_dict()[1] == pytest.approx(1 / 6)

@pytest.mark.parametrize('sides', (2, 3, 4, 6, 8, 10, 12, 20, 100))
def test_presets(sides):
    """All the usual dice are available"""
    result = getattr(dice, f'd{sides}').to_dict()
    assert result == dice.d(sides).to_dict()

@pytest.mark.parametrize('sides', tuple(range(1, 101)) + (200, 471, 1000))
def test_one_die(sides):
    """Create dice with any number of sides"""
    result = dice.d(sides).to_dict()
    assert result.keys() == set(range(1, sides + 1))
    for idx in range(1, sides + 1):
        assert result[idx] == pytest.approx(1 / sides)

def test_roll_die():
    """Use the roll() function to roll one die"""
    d6 = dice.d6
    roll = dice.roll
    assert roll(d6) in (1, 2, 3, 4, 5, 6)
    # In theory this test has a tiny probability of failing
    assert set(roll(d6) for _ in range(1000)) == {1, 2, 3, 4, 5, 6}
