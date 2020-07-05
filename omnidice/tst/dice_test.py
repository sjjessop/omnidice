
import math

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

@pytest.mark.parametrize('sides', tuple(range(1, 51)) + (100, 200, 471, 1000))
def test_one_die(sides):
    """Create dice with any number of sides"""
    check_uniform(dice.d(sides), set(range(1, sides + 1)))

def test_roll_die():
    """Use the roll() function to roll one die"""
    d6 = dice.d6
    roll = dice.roll
    assert roll(d6) in (1, 2, 3, 4, 5, 6)
    # In theory this test has a tiny probability of failing
    assert set(roll(d6) for _ in range(1000)) == {1, 2, 3, 4, 5, 6}

def test_simple_expressions():
    """
    You can write arithmetic expressions using dice and numeric constants. The
    result is an object which you can roll just like a single die.
    """
    assert 13 <= dice.roll(dice.d6 + 12) <= 18
    check_uniform(dice.d6 + 1, {2, 3, 4, 5, 6, 7})
    check_uniform(dice.d6 - 1, {0, 1, 2, 3, 4, 5})
    check_uniform(dice.d6 * 2 + 4, {6, 8, 10, 12, 14, 16})
    check_uniform(dice.d6 / 2, {0.5, 1, 1.5, 2, 2.5, 3})
    check_uniform((dice.d6 + 1) // 2, {1, 2, 3})
    check_uniform(-dice.d6, {-1, -2, -3, -4, -5, -6})

def test_apply():
    """
    For calculations not supported by operator overloading, you can use the
    apply() function to re-map the generated values. It can be a many-to-one
    mapping.
    """
    check_uniform(
        dice.d6.apply(math.log),
        {math.log(idx) for idx in range(1, 7)},
    )
    check_uniform(
        dice.d6.apply(lambda x: 0 if x == 6 else abs(x - 3)),
        {0, 1, 2},
    )

def test_advanced_expressions():
    """
    Arithmetic expressions can involve more than one die.
    """
    result = (dice.d6 + dice.d6).to_dict()
    assert result.keys() == set(range(2, 13))
    assert sum(result.values()) == pytest.approx(1)
    assert result[7] == pytest.approx(result[12] * 6)
    check_uniform(
        (dice.d10 - 1) * 10 + dice.d10,
        set(range(1, 101)),
    )

def test_at_operator():
    """
    The @ operator represents rolling multiple dice (or other expressions) and
    adding the results together. 2 @ d6 is the same as d6 + d6.

    Note the difference between 2@d6, and d6 * 2. For the time being, the
    syntax 2 * d6 is forbidden in order to prevent accidents.

    For large numbers of dice (>100), the current implementation using
    fractions.Fraction can get a little slow. You could speed it up by using
    fast_d6 = dice.DRV({x: float(y) for x, y in dice.d6.to_dict()}), but the
    results will be less precise.
    """
    d6 = dice.d6
    check_uniform(1@d6, {1, 2, 3, 4, 5, 6})
    with pytest.raises(ValueError):
        0 @ d6
    with pytest.raises(TypeError):
        0.5 @ d6
    assert (2@d6).to_dict() == (d6 + d6).to_dict()
    assert (3@d6).to_dict() == (d6 + d6 + d6).to_dict()
    assert min((10@d6).to_dict().keys()) == 10
    assert max((10@d6).to_dict().keys()) == 60
    assert (2@(d6 + 1)).to_dict() == (d6 + d6 + 2).to_dict()
    with pytest.raises(TypeError):
        2 * d6

def test_excessive_expressions():
    """
    I don't know any games that need this, but for completeness we allow dice
    on the left-hand-side of the @ operator. This is only allowed if the
    left-hand expression takes only positive integer values.
    """
    result = (dice.d3 @ dice.d6).to_dict()
    assert min(result) == 1
    assert max(result) == 18
    assert result[18] == pytest.approx(1 / 3 / 6 ** 3)
    assert result[17] == pytest.approx(1 / 6 ** 3)

    result = ((dice.d3 * 2) @ dice.d6).to_dict()
    assert min(result) == 2
    assert max(result) == 36
    assert result[36] == pytest.approx(1 / 3 / 6 ** 6)
    assert result[35] == pytest.approx(6 / 3 / 6 ** 6)

    with pytest.raises(TypeError):
        (dice.d3 / 2) @ dice.d6

    # @ operator does not commute.
    assert (dice.d3 @ dice.d6).to_dict() != (dice.d6 @ dice.d3).to_dict()

def check_uniform(die, expected_values):
    """
    Check that "die" has uniform distribution.
    """
    result = die.to_dict()
    assert result.keys() == expected_values
    for idx in expected_values:
        assert result[idx] == pytest.approx(1 / len(expected_values))
    assert die.sample() in expected_values
    assert dice.roll(die) in expected_values
    rolls = set()
    for idx in range(100):
        rolls.update(die.sample() for _ in range(len(expected_values)))
        if rolls == expected_values:
            break
    assert rolls == expected_values
