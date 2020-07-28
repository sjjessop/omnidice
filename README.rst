========
Omnidice
========

A Python library for arithmetic involving dice and other discrete random
variables. `Current release documentation <https://omnidice.readthedocs.io/>`_.

.. image:: https://readthedocs.org/projects/omnidice/badge/?version=latest
   :alt: Documentation status
   :target: https://omnidice.readthedocs.io/en/latest/

.. image:: https://github.com/sjjessop/omnidice/workflows/tests/badge.svg
   :alt: Test status
   :target: https://github.com/sjjessop/omnidice/actions?query=workflow%3Atests

.. image:: https://codecov.io/gh/sjjessop/omnidice/branch/master/graph/badge.svg
   :alt: codecov
   :target: https://codecov.io/gh/sjjessop/omnidice

.. image:: https://img.shields.io/badge/python-3.7%20%7C%203.8-blue.svg
   :alt: Python versions 3.7 3.8
   :target: https://www.python.org/downloads/release/python-380/

.. image:: https://img.shields.io/badge/badges-5-green.svg
   :alt: 5 badges
   :target: https://shields.io/

Purpose
=======

This library is mainly intended for computing probabilities for the various
dice rolls needed for different tabletop RPGs. A function is provided to roll
the dice and get a single result, but the main intention is to answer questions
like, "what are my chances of making a particular roll", "how much of an
advantage is it to have one extra point", and the like.

Getting Started
===============

Use
---

Omnidice provides a type ``DRV`` representing a discrete random variable, plus
convenience features for dice. The following operators are implemented: ``+``,
``-``, ``*``, ``/``, ``//``, ``<``, ``<=``, ``>``, ``>=``, ``==``, ``!=``, and
``@`` (which represents multiple rolls added together).

.. code-block:: pycon

    >>> from omnidice.dice import d3, d4, d6, d8, d, roll
    >>> from omnidice.drv import p
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
    >>> print(p(2 @ d6 > 3 @ d6))
    197/1296
    >>> ((d6 + 1) // 2).is_same(d3)
    True
    >>> (((d6 + 1) // 2) == d3).to_dict()
    {False: Fraction(2, 3), True: Fraction(1, 3)}


For additional examples of use, see the test code in
``omnidice/tst/dice_test.py``

Installation
------------

This package is not on PyPI (yet). If you just want to use the current release:

.. code-block:: bash

    pip install --upgrade https://github.com/sjjessop/omnidice/releases/latest/download/omnidice-v1-py3-none-any.whl

You should now be able to run any of the example code above.

Installation alternatives
-------------------------

If you want to work with the source for the current release:

.. code-block:: bash

    git clone --branch release https://github.com/sjjessop/omnidice.git
    cd omnidice
    python setup.py install
    pytest

When running the tests you might see a warning:

.. code-block:: text

    RuntimeWarning: numpy.ufunc size changed, may indicate binary incompatibility.
    Expected 192 from C header, got 216 from PyObject

`This should not be a problem <https://github.com/numpy/numpy/issues/12785>`_,
but I can't get to the bottom of why it happens at all for me, even when
everything was installed via Anaconda.

If you want the latest (unreleased) code, then use the ``master`` branch.

If you know what you're doing then of course you are free to install by
``python setup.py``, or ``pip install -e .``, or by building a wheel file
locally.

Currently the code should work fine even if not installed (so, you could amend
your ``PYTHONPATH`` or just run from the root of the repo). I might in future
add features which use data files, and those won't necessarily work when the
package isn't registered with ``setuptools``.

Optional dependencies
---------------------

If you install ``numpy``, then some operations will run faster.

If you install ``pandas``, then you can write the probability distribution to
a ``Series`` object:

.. code-block:: pycon

    >>> d4.to_pd()
    1    1/4
    2    1/4
    3    1/4
    4    1/4
    Name: probability, dtype: object

Even without Pandas, you can get the probabilities as a dictionary if you want
to do your own computations with them:

.. code-block:: pycon

    >>> d6.to_dict()
    {1: Fraction(1, 6), 2: Fraction(1, 6), 3: Fraction(1, 6), 4: Fraction(1, 6), 5: Fraction(1, 6), 6: Fraction(1, 6)}

Quirks
======

Equality
--------

Because ``==`` is overridden to return a ``DRV`` (not a boolean), ``DRV``
objects are not hashable and cannot be used in sets or dictionaries. They also
raise an exception in boolean context.

Performance and precision
=========================

The library currently computes probability distributions eagerly. When you
create the object ``10 @ d6``, all 51 possible outcomes and their probabilities
are computed and stored. The algorithms for doing so are not particularly
optimised. This means that very large dice rolls (larger than you actually
encounter in practical games) can be very slow. I may change this in future,
hopefully with minor backward-incompatibilities or none.

By default, probabilities are expressed using ``fractions.Fraction``, which is
precise but slow. You can convert the probabilities in any ``DRV`` to ``float``
by calling the ``faster()`` method, which returns a new object. Typically this
is a lot faster, but you will of course be subject to the inaccuracies of
floating-point arithmetic.

.. code-block:: pycon

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

That said, if you stick to numbers below 100 you're unlikely to mind the
speed too much even with ``fractions``:

.. code-block:: console

    $ python -mtimeit -s "from omnidice.dice import d6" -c "10 @ d6"
    50 loops, best of 5: 4.58 msec per loop

    $ python -mtimeit -s "from omnidice.dice import d6" -c "100 @ d6"
    1 loop, best of 5: 782 msec per loop

    $ python -mtimeit -s "from omnidice.dice import d6" -c "200 @ d6"
    1 loop, best of 5: 5.01 sec per loop

    $ python -mtimeit -s "from omnidice.dice import d6" -c "10 @ d6.faster()"
    500 loops, best of 5: 366 usec per loop

    $ python -mtimeit -s "from omnidice.dice import d6" -c "100 @ d6.faster()"
    10 loops, best of 5: 1.82 msec per loop

    $ python -mtimeit -s "from omnidice.dice import d6" -c "200 @ d6.faster()"
    2 loops, best of 5: 3.45 msec per loop

Versioning
==========

Version numbers follow `Semantic Versioning <https://semver.org/>`_. However,
the version number in the code might only be updated at the point of creating a
`release tag <https://github.com/sjjessop/omnidice/tags>`_. So, if you're
working in the repo then the version number does not indicate compatibility
with past releases, except that the tip of the ``release`` branch is always the
current (most recent) release.

Compatibility
=============

Omnidice does not work with Python versions 3.6 or lower, because it uses the
``dataclasses`` module.

It should work with pretty much any versions of its optional dependencies,
``numpy`` and ``pandas``.