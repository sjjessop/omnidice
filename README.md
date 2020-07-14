# Omnidice

A Python library for arithmetic involving dice and other discrete random
variables. [Full documentation](https://omnidice.readthedocs.io/en/latest/).

[![Documentation Status](https://readthedocs.org/projects/omnidice/badge/?version=latest)](https://omnidice.readthedocs.io/en/latest/?badge=latest)

## Purpose

This library is mainly intended for computing probabilities for the various
dice rolls needed for different tabletop RPGs. A function is provided to roll
the dice and get a single result, but the main intention is to answer questions
like, "what are my chances of making a particular roll", "how much of an
advantage is it to have one extra point", and the like.

## Getting Started

### Installation

```bash
git clone git@github.com:sjjessop/omnidice.git
cd omnidice
python setup.py install
pytest
```

If you prefer you can of course install with `pip install -e omnidice`, or even
build the wheel and then install that. Or just add the `omnidice` directory to
your PYTHONPATH.

### Use

Omnidice provides a type `DRV` representing a discrete random variable, plus
convenience features for dice. The following operators are implemented: `+`,
`-`, `*`, `/`, `//`, `<`, `<=`, `>`, `>=` and `@` (which represents multiple
rolls added together).

```pycon
>>> from omnidice.dice import d4, d6, d8, d, roll
>>> roll(d6)
2
>>> roll(d6 + d4)
7
>>> roll(d(1000))
348
>>> my_dice = d6 + d8
>>> roll(my_dice)
6
>>> roll(my_dice)
10
>>> my_dice
(d6 + d8)
>>> print(d6.to_table())
value   probability
1       1/6
2       1/6
3       1/6
4       1/6
5       1/6
6       1/6
>>> print((d6 + d4).to_table())
value   probability
2       1/24
3       1/12
4       1/8
5       1/6
6       1/6
7       1/6
8       1/8
9       1/12
10      1/24
>>> print((2 @ d6 + 4).to_table())
value   probability
6       1/36
7       1/18
8       1/12
9       1/9
10      5/36
11      1/6
12      5/36
13      1/9
14      1/12
15      1/18
16      1/36
>>> print((2 @ d6 >= 9).to_table())
value   probability
False   13/18
True    5/18
>>> print((2 @ d6 > 3 @ d6).to_table())
value   probability
False   1099/1296
True    197/1296
>>> print((2 @ d6 > 3 @ d6).to_table(as_float=True))
value   probability
False   0.8479938271604939
True    0.15200617283950618
```

For additional examples of use, see the test code in
:file:`omnidice/tst/dice_test.py`

### Optional dependency

If you install `pandas`, then you can write the probability distribution to
a `Series` object:

```pycon
>>> d4.to_pd()
1    1/4
2    1/4
3    1/4
4    1/4
Name: probability, dtype: object
```

Even without Pandas, you can get the probabilities as a dictionary if you want
to do your own computations with them:

```pycon
>>> d6.to_dict()
{1: Fraction(1, 6), 2: Fraction(1, 6), 3: Fraction(1, 6), 4: Fraction(1, 6), 5: Fraction(1, 6), 6: Fraction(1, 6)}
```

## Performance and precision

The library currently computes probability distributions eagerly. When you
create the object `10 @ d6`, all 51 possible outcomes and their probabilities
are computed and stored. The algorithms for doing so are not particularly
optimised. This means that very large dice rolls (larger than you actually
encounter in practical games) can be very slow. I may change this in future,
hopefully with minor backward-incompatibilities or none.

By default, probabilities are expressed using `fractions.Fraction`, which is
precise but slow. You can convert the probabilities in any `DRV` to `float`
by calling the `faster()` method, which returns a new object. Typically this
is a lot faster, but you will of course be subject to the inaccuracies of
floating-point arithmetic.

```pycon
>>> print(d4.to_table())
value   probability
1       1/4
2       1/4
3       1/4
4       1/4
>>> print(d4.faster().to_table())
value   probability
1       0.25
2       0.25
3       0.25
4       0.25
```

That said, if you stick to numbers below 100 you're unlikely to mind the
speed too much even with `fractions`:

```console
$ python -mtimeit -s"from omnidice.dice import d6" -c "10 @ d6"
50 loops, best of 5: 4.58 msec per loop

$ python -mtimeit -s"from omnidice.dice import d6" -c "100 @ d6"
1 loop, best of 5: 833 msec per loop

$ python -mtimeit -s"from omnidice.dice import d6" -c "200 @ d6"
1 loop, best of 5: 5.37 sec per loop

$ python -mtimeit -s"from omnidice.dice import d6" -c "10 @ d6.faster()"
500 loops, best of 5: 344 usec per loop

$ python -mtimeit -s"from omnidice.dice import d6" -c "100 @ d6.faster()"
10 loops, best of 5: 28.8 msec per loop

$ python -mtimeit -s"from omnidice.dice import d6" -c "200 @ d6.faster()"
2 loops, best of 5: 118 msec per loop
```

I have a TODO item to speed up the `@` operator using `numpy.convolve` where it
is applicable, since the current code is completely generic and unoptimised.

Precision when rolling dice is currently poor: a `float` is used to select the
result. This will be fixed in future.
