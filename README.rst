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

.. image:: https://codecov.io/gh/sjjessop/omnidice/branch/develop/graph/badge.svg
   :alt: codecov
   :target: https://codecov.io/gh/sjjessop/omnidice

.. image:: https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-blue.svg
   :alt: Python versions 3.6 3.7 3.8 3.9
   :target: https://www.python.org/downloads/

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

    pip install -U https://github.com/sjjessop/omnidice/releases/latest/download/omnidice-v1-py3-none-any.whl

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

If you want the latest (unreleased) code, then use the ``develop`` branch.

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

The following are not considered part of the published interface of this
package, and can change without a major version number change:

* Undocumented behaviour, including exceptions not explicitly documented. The
  new behaviour could be a different exception, or could be some other
  behaviour entirely (in which case it's probably a new feature).
* Private functions (or other entities), meaning names that start with ``_``
  other than dunder methods.
* Behaviour when input constraints are violated, including type annotations.
  You don't have to type-check your code, but in this package the annotations
  document input requirements.
* The ``str()`` and ``repr()`` forms of objects.
* The ``omnidice.expressions`` module and ``tree`` parameters.
* Anything explicitly described as provisional.

Other than the last point these are all different kinds of undocumented
behaviour.

Backward-incompatible changes to undocumented behaviour may come with only
a patch version bump. Backward-incompatible changes to provisional behaviour
will come with at least a minor version bump, so you can depend on provisional
behaviour by pinning to ``major.minor.*``.

Dropping support for a Python version will come with an increased
``python_requires`` constraint. So regardless of how you've pinned this
package's version, you won't get a version that doesn't support your Python
version.

Removing support for a Python version is nevertheless considered a
backward-incompatible change and therefore does bump the major version, unless
that Python version has passed its
`end of support <https://www.python.org/downloads/>`_. Dropping such obsolete
versions is only a minor version bump.

There is only one "release stream", and changes will not be backported to past
major or minor releases.

Compatibility
=============

Omnidice does not work with Python versions 3.5 or lower, because it uses
f-strings, variable annotations, and possibly other features new in 3.6.

It should work with pretty much any versions of its optional dependencies,
``numpy`` and ``pandas``.

Changelog
=========

Version 1.2.1
-------------

Features
~~~~~~~~

No changes to API, but:

* Python 3.9 is now supported, and added to the test matrix.
* Main development branch is now called `develop`.
* Removed a documentation hack, and instead use the new `autodoc_type_aliases`
  Sphinx config option.

Bugfixes
~~~~~~~~

* Tighten up a function signature caught by a recent version of mypy: to call
  `sorted()` on a sequence we now need to declare its elements comparable as
  well as them actually being comparable at runtime.

Version 1.2.0
-------------

Features
~~~~~~~~

* Add Python 3.6 support, and corresponding test build.
* One Roll Engine.
* Open D6.

Version 1.1.0
-------------

Features
~~~~~~~~

* Started adding code for specific game systems.
* Dice pools, which are DRVs whose possible values are the different
  combinations rolled on multiple dice.
* New features of DRV:
   * The function passed to apply() can return a DRV.
   * Method given() returns conditional probability distribution.
   * Method weighted_average() combines DRVs.
* Provide a fixed URL for the latest wheel of a major version.
* Detailed versioning policy: definition of backward-compatible.

Bugfixes
~~~~~~~~

* to_table() now works even if the values of the DRV aren't sortable.
* Removed hacky use of TypeVar in DRV type annotations.
* The values on the right-hand side of ``@`` no longer need to be numeric,
  they just need to implement ``+``.

Backward-incompatible
~~~~~~~~~~~~~~~~~~~~~

* Changed `tree` to a keyword-only argument in DRV methods. It was not intended
  for public use (yet), since its type is an undocumented class.
