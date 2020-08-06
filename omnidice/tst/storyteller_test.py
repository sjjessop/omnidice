
import pytest

from omnidice.drv import DRV, p
from omnidice.systems import storyteller

@pytest.mark.parametrize('target', range(2, 11))
def test_standard(target):
    """Difficulty 2 - 10"""
    expected = DRV({
        -1: 0.1,
        0: (target - 2) / 10,
        1: (11 - target) / 10,
    })
    die = storyteller.standard(target)
    assert die.is_close(expected)
    assert die.is_same(die.apply(storyteller.total))
    revised_die = storyteller.revised_standard(target)
    assert revised_die.apply(storyteller.total).is_close(expected)

@pytest.mark.parametrize('target', range(11, 20))
def test_impossible(target):
    """Difficulty is capped at 10"""
    expected = storyteller.standard(10)
    die = storyteller.standard(target)
    assert die.is_close(expected)
    assert die.is_same(die.apply(storyteller.total))
    revised_die = storyteller.revised_standard(target)
    assert revised_die.apply(storyteller.total).is_close(expected)

@pytest.mark.parametrize('target', range(-10, 2))
def test_easy(target):
    """Difficulty is capped at 2"""
    die = storyteller.standard(target)
    expected = storyteller.standard(2)
    assert die.is_close(expected)
    assert die.is_same(die.apply(storyteller.total))
    revised_die = storyteller.revised_standard(target)
    assert revised_die.apply(storyteller.total).is_close(expected)

def test_special():
    """
    With a specialty you can re-roll 10s. 1s on the reroll do *not* count as
    botches.
    """
    die = storyteller.special(6, rerolls=4)
    probs = {
        # 1 on the first roll
        -1: 0.1,
        # 2-5 on the first roll
        0: 0.4,
        # 6-9 on the first roll, or 1-5 on the second roll
        1: 0.4 + 0.1 * 0.5,
        # 6-9 on the second roll, or 1-5 on the third roll
        2: 0.4 * 0.1 + 0.5 * 0.01,
        3: 0.4 * 0.01 + 0.5 * 0.001,
        4: 0.4 * 0.001 + 0.5 * 0.0001,
    }
    probs[5] = 1 - sum(probs.values())
    assert die.is_close(DRV(probs))
    assert sum(die.to_dict().values()) == 1
    revised_die = storyteller.revised_special(6, rerolls=4).apply(storyteller.total)
    assert revised_die.is_close(DRV(probs))
    assert sum(revised_die.to_dict().values()) == 1

def test_revised_botch():
    """
    The botch rule is different in Revised. Now if you roll at least one
    success, you cannot botch, even if it's cancelled out by 1s.
    """
    # With one or two dice, Revised makes no difference from 1st/2nd.
    die = storyteller.revised_standard(6).apply(storyteller.total)
    probs = {
        -1: 0.1,
        0: 0.4,
        1: 0.5,
    }
    assert die.is_close(DRV(probs))
    roll2 = (2 @ storyteller.revised_standard(6)).apply(storyteller.total)
    # With 2 dice, the only rolls that botch are 1+1 .. 1+5 and 2+1 .. 5+1
    assert p(roll2 < 0) == pytest.approx(0.09)
    # It's three dice where the difference kicks in: the case of 2 botches and
    # one success has probability 0.1 * 0.1 * 0.5 * 3 = 0.015. In Revised
    # that's not a botch.
    old_roll = 3 @ storyteller.standard(6)
    new_roll = (3 @ storyteller.revised_standard(6)).apply(storyteller.total)
    assert p(old_roll == -1) == pytest.approx(p(new_roll == -1) + 0.015)
