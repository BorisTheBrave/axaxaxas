.. _ambiguity:

Handling Ambiguity
==================

The `parse` function returns a `ParseForest`. A `ParseForest` is an efficient shared representation of multiple
possible `ParseTree` objects. For some grammars, therefore, you must be careful dealing with `ParseForest` objects
as they may contains exponentially many possible parses.

single, all, count, and \_\_iter\_\_
------------------------------------

These are the basic methods for extracting parse trees from the forest.

`ParseForest.single()` returns the unique tree in the forest, if there is one, or throws `AmbiguousParseError`
(see :ref:`errors`).

`ParseForest.count()` returns a count of all the trees.

`ParseForest.all()` returns a list of all the trees in the forest. It can be quite large.

`ParseForest.__iter__()` iterates over all the trees in the forest. It is quite a bit slower than `all`, but it
doesn't load all the trees into memory at once.

Greedy Rules
------------

Using the ``greedy``, ``lazy``, ``prefer_early``, ``prefer_late`` and ``penalty`` settings described in :ref:`greedy` allows you
to eliminate alternative parses. In the extreme case of marking every nonterminal with ``prefer_early`` and
every ``optional``, ``star`` and ``plus`` symbol with ``greedy``, then you will never have an ambiguous parse.

Builders
--------

:ref:`builders` are an advanced API that give you fine control over interpreting the parse. You can explicitly
control behaviour in ambiguity by handling `Builder.merge`.

