omnidice.systems
================

.. versionadded:: 1.1

This package contains helper tools for various different dice mechanics. Each
separate system has its own module.

Many of the names of the companies and systems below are trademarks. They are
used here solely to identify the games. None of their owners have approved my
source code in any way. The descriptions and representations of how the dice
mechanics work are paraphrased from the game materials or other sources, so
they are Not Official.

The game mechanics are only described far enough to make clear what mechanic
and version we're talking about. You probably can't learn the mechanics for an
unfamiliar game from this documentation.

Usage
-----

Some function names are fairly verbose (especially if you include the
``omnidice.systems.X`` prefix), because they aim to be clear what part of the
system they relate to. If you're going to use a function repeatedly, you are
encouraged to define an abbreviation when you import it.

For example, if you're only interested in Revised editions of the Storyteller
system, there's no need to use the long name ``revised_standard`` every time.
It can instead just be ``die``, or perhaps ``diff`` (because the argument is
the difficulty):

.. code-block:: python

    from omnidice.systems.storyteller import revised_standard as diff, total

    # Distribution for 6 dice, difficulty 8 (as RevisedResult)
    6 @ diff(8)
    # Distribution for 6 dice, difficulty 8 (as total successes)
    (6 @ diff(8)).apply(total)

Storyteller (White Wolf, Mark Rein-Hagen, Tom Dowd)
---------------------------------------------------

.. automodule:: omnidice.systems.storyteller
   :show-inheritance:
   :members:
   :member-order: bysource
   :special-members: __int__
