
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
    fast_d6 = dice.d6.faster(), but the results will be less precise.
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

def test_comparisons():
    """
    Expressions involving a comparison operation return a random variable
    over two values: True and False.

    You can use comparison operators to implement "target numbers".

    == and != are not currently implemented in this way, because it is
    ambiguous whether for example d6 == d6 should return True (because they're
    the same object) or a distibution {True: 1 / 6, False: 5 / 6}.
    """
    def true_or_false(prob_true):
        if prob_true >= 1:
            return {True: 1}
        if prob_true <= 0:
            return {False: 1}
        return {
            True: pytest.approx(prob_true),
            False: pytest.approx(1 - prob_true),
        }
    assert (dice.d4 <= 2).to_dict() == true_or_false(0.5)
    assert (dice.d4 < 3).to_dict() == true_or_false(0.5)
    assert (dice.d4 >= 4).to_dict() == true_or_false(0.25)
    assert (dice.d4 > 3).to_dict() == true_or_false(0.25)
    for idx in range(-10, 10):
        assert (dice.d4 <= idx).to_dict() == true_or_false(idx * 0.25), idx
        assert (dice.d4 < idx).to_dict() == true_or_false(idx * 0.25 - 0.25), idx
        assert (dice.d4 >= idx).to_dict() == true_or_false((5 - idx) * 0.25), idx
        assert (dice.d4 > idx).to_dict() == true_or_false((4 - idx) * 0.25), idx

    # There are alternatives to equality comparisons
    # assert dice.d2 == dice.d(2)
    assert dice.d2.to_dict() == dice.d(2).to_dict()
    # assert dice.d2 != dice.d3
    assert dice.d2.to_dict() != dice.d3.to_dict()
    # assert (dice.d4 == 1).to_dict() == true_or_false(0.25)
    assert dice.d4.to_dict()[1] == 0.25
    # assert (dice.d4 != 2).to_dict() == true_or_false(0.75)
    dist = dice.d4.to_dict().items()
    assert sum(prob for value, prob in dist if value != 2) == 0.75
    assert 1 - dice.d4.to_dict()[2] == 0.75

    # Target numbers
    assert (dice.d100 <= 87).to_dict() == true_or_false(0.87)
    # Natural twenty
    assert (dice.d20 >= 20).to_dict()[True] == pytest.approx(1 / 20)
    # Two different 50/50 chances
    check_approx(10@(dice.d10 >= 6), 10@(dice.d2 >= 2))
    # Bucket o' dice and count successes
    def prob(n, difficulty=8, dice=10):
        p_succ = (11 - difficulty) / 10
        return (
            (p_succ ** n) * (1 - p_succ) ** (dice - n)
            # TODO math.comb in Python 3.8
            * math.factorial(dice) / math.factorial(n) / math.factorial(dice - n)
        )
    # Exactly 4 successes
    assert (10 @ (dice.d10 >= 8)).to_dict()[4] == pytest.approx(prob(4))
    # 4 or more successes
    prob_4_or_more = sum(prob(n) for n in range(4, 11))
    result = (10 @ (dice.d10 >= 8) >= 4).to_dict()[True]
    assert result == pytest.approx(prob_4_or_more)

def test_explode():
    """
    Plenty of systems use dice that explode on their maximum value.
    """
    assert (dice.d6.explode() > 6).to_dict()[True] == pytest.approx(1 / 6)
    assert (dice.d6.explode() > 12).to_dict()[True] == pytest.approx(1 / 36)
    # Limit the number of times the die is re-rolled
    mini_explode = dice.d6.explode(rerolls=1)
    assert (mini_explode > 6).to_dict()[True] == pytest.approx(1 / 6)
    assert mini_explode.to_dict()[12] == pytest.approx(1 / 36)
    assert (mini_explode > 12).to_dict().get(True, 0) == 0
    # It doesn't have to be a single die
    multi_explode = (2@dice.d6).explode()
    assert multi_explode.to_dict().get(12, 0) == 0
    assert (multi_explode > 12).to_dict()[True] == pytest.approx(1 / 36)

def test_repr():
    """
    The representation of these objects reflects the original expression. It's
    not just a dump of the probabilities unless the expression was created in
    a way we can't track.
    """
    def check(expr, string_form):
        assert repr(expr) == string_form
        result = eval(string_form, dice.__dict__)
        check_approx(expr, result)

    check(dice.d6, 'd6')
    check(dice.d6 + 1, '(d6 + 1)')
    check(dice.d6 + dice.d6, '(d6 + d6)')
    check(2@dice.d6, '(2 @ d6)')
    check(dice.d(783), 'd(783)')
    check(dice.d(6), 'd6')
    check(-dice.d6, '-d6')
    check(-(dice.d6 + dice.d4), '-(d6 + d4)')
    check(
        (2 @ dice.d4) * (dice.d6 + dice.d(10)) - (8 @ dice.d4 - 5),
        '((2 @ d4) * (d6 + d10) - (8 @ d4 - 5))',
    )
    check(dice.d6 + dice.d6 + dice.d6, '(d6 + d6 + d6)')
    check(dice.d6 - dice.d6 - dice.d6, '(d6 - d6 - d6)')
    check(dice.d6 - (dice.d6 - dice.d6), '(d6 - (d6 - d6))')
    check((dice.d6 + dice.d6) - dice.d6, '(d6 + d6 - d6)')
    check((dice.d6 + dice.d6) < dice.d6, '(d6 + d6 < d6)')
    check((dice.d6 + dice.d6) * dice.d6, '((d6 + d6) * d6)')
    check(
        (dice.d6 <= dice.d6) <= (dice.d6 <= dice.d6),
        '((d6 <= d6) <= (d6 <= d6))',
    )
    check(dice.d2 @ dice.d2, '(d2 @ d2)')
    check(
        dice.d2.apply(lambda x: x + 1),
        'DRV({2: Fraction(1, 2), 3: Fraction(1, 2)})',
    )
    check(dice.d6.explode(), 'd6.explode()')
    check(dice.d6.explode(rerolls=2), 'd6.explode(2)')

def test_table():
    """
    For eyeballing small data, we can dump the probabilities as a text table.
    This table is often easier to read with the probabilities as floats.
    """
    check_table_match(dice.d4.to_table(), """
        value\tprobability
        1\t1/4
        2\t1/4
        3\t1/4
        4\t1/4
    """)
    check_table_match((2@dice.d6).to_table(as_float=True), """
        value\tprobability
        2\t0.027777777777777776
        3\t0.05555555555555555
        4\t0.08333333333333333
        5\t0.1111111111111111
        6\t0.1388888888888889
        7\t0.16666666666666666
        8\t0.1388888888888889
        9\t0.1111111111111111
        10\t0.08333333333333333
        11\t0.05555555555555555
        12\t0.027777777777777776
    """)

@pytest.mark.parametrize('expr', [dice.d6, 10 @ dice.d6, dice.d10 + 1])
def test_pandas(expr):
    """
    For eyeballing or charting data, or whatever other onward processing you
    like, we can export the distribution as a pandas Series object. This is
    an optional feature, only available is pandas is installed.
    """
    try:
        import pandas  # noqa F401 'pandas' imported but unused
    except ModuleNotFoundError:
        with pytest.raises(ModuleNotFoundError):
            expr.to_pd()
    else:
        assert dict(expr.to_pd()) == expr.to_dict()
        # You can also construct a random variable from a Series
        check_approx(dice.DRV(expr.to_pd()), expr)

@pytest.mark.parametrize('expr', [dice.d6, 10 @ dice.d6, dice.d10 + 1])
def test_faster(expr):
    """
    If the default implementation using fractions is slow, converting to
    float is likely to be faster. However it is less precise.
    """
    check_approx(expr.faster(), expr)
    # Not really testing much here, but it does cover a little bit of code
    # in the cdf function, which handles the case where rounding errors make
    # the total probability less than 1.
    expr.faster().sample()

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

def check_approx(left, right):
    left, right = left.to_dict(), right.to_dict()
    assert left.keys() == right.keys()
    for key in left.keys():
        assert left[key] == pytest.approx(right[key])

def check_table_match(left, right):
    def clean(table):
        lines = table.splitlines()
        return list(filter(None, map(str.strip, lines)))
    # Left-hand table, which came from an expression, is in "clean" form...
    assert clean(left) == left.splitlines()
    # ... and matches the expected result
    assert clean(left) == clean(right)
